import os
import json
import pandas as pd
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from .models import SurveyResponse, SurveyResult, Supplement, UserHealthReport, Nutrient, UserNutrientIntake, NutrientAnalysis, Like, UserLog, Favorite, KDRIs
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from datetime import datetime, timedelta
from Product.models import Products  # 파일 상단에 추가
import pytesseract
from PIL import Image
import re
from django.contrib import messages
import csv
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import ast

@login_required
def mypage_view(request):
    # 사용자의 최근 설문 결과 가져오기
    latest_survey = SurveyResult.objects.filter(user=request.user).order_by('-created_at').first()
    
    if latest_survey:
        # 건강 점수 계산
        health_score = calculate_health_score(latest_survey)
        
        # 추천 영양제 가져오기
        recommended_supplements = get_recommended_supplements(latest_survey)
        
        # 건강 리포트 생성 또는 업데이트
        health_report, created = UserHealthReport.objects.get_or_create(
            user=request.user,
            survey_result=latest_survey,
            defaults={
                'health_score': health_score,
                'recommendations': generate_recommendations(latest_survey, health_score)
            }
        )
        
        if not created:
            health_report.health_score = health_score
            health_report.recommendations = generate_recommendations(latest_survey, health_score)
            health_report.save()
        
        # 설문 이력 가져오기
        survey_history = UserHealthReport.objects.filter(user=request.user).order_by('-created_at')
        
        context = {
            'latest_survey': latest_survey,
            'health_score': health_score,
            'recommended_supplements': recommended_supplements,
            'recommendations': health_report.recommendations.split('\n'),
            'survey_history': survey_history
        }
    else:
        context = {
            'latest_survey': None,
            'health_score': 0,
            'recommended_supplements': [],
            'recommendations': [],
            'survey_history': []
        }
    
    context['user'] = request.user
    return render(request, 'Mypage/mypage.html', context)

@login_required
def survey(request):
    try:
        with open('static/json/Mypage/survey_questions.json', 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
            
            # Add IDs to questions
            for i, question in enumerate(survey_data['questions']):
                question['id'] = str(i + 1)
            
            return render(request, 'Mypage/survey.html', {
                'survey_questions': survey_data
            })
    except Exception as e:
        print(f"Error loading survey questions: {str(e)}")
        return render(request, 'Mypage/survey.html', {
            'survey_questions': {'questions': []},
            'error': str(e)
        })

@login_required
def favorite_view(request):
    try:
        # 사용자가 좋아요한 영양제 가져오기
        likes = Like.objects.filter(user=request.user).select_related('product')
        liked_supplements = [like.product for like in likes]

        # 추천 영양제 가져오기
        latest_survey = SurveyResult.objects.filter(user=request.user).order_by('-created_at').first()
        if latest_survey:
            recommended_supplements = get_recommended_supplements(latest_survey)
        else:
            recommended_supplements = []
        
        context = {
            'liked_supplements': liked_supplements,
            'recommended_supplements': recommended_supplements
        }
        return render(request, 'Mypage/like.html', context)
    except Exception as e:
        messages.error(request, f'즐겨찾기 목록을 불러오는 중 오류가 발생했습니다: {str(e)}')
        return redirect('mypage')

@login_required
def toggle_like(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            supplement_id = data.get('supplement_id')
            is_liked = data.get('is_liked')
            
            product = Products.objects.get(id=supplement_id)
            
            if is_liked:
                Favorite.objects.get_or_create(user=request.user, product=product)
            else:
                Favorite.objects.filter(user=request.user, product=product).delete()
            
            return JsonResponse({
                'status': 'success',
                'message': '좋아요 상태가 업데이트되었습니다.'
            })
        except Products.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '영양제를 찾을 수 없습니다.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)

@login_required
def analysis_view(request):
    try:
        # 사용자의 최신 영양소 분석 결과 가져오기
        latest_analysis = NutrientAnalysis.objects.filter(user=request.user).order_by('-date').first()
        
        # 사용자가 좋아요한 영양제 가져오기
        likes = Like.objects.filter(user=request.user).select_related('product')
        liked_supplements = [like.product for like in likes]
        
        # 좋아요한 제품 데이터를 JSON으로 직렬화
        liked_supplements_json = json.dumps([
            {
                'id': product.id,
                'title': product.title,
                'description': product.brand or product.manufacturer or product.supplement_type or '설명 없음'
            }
            for product in liked_supplements
        ])
        
        print(f"[DEBUG] liked_supplements: {liked_supplements}")  # 추가: 콘솔에 리스트 출력

        # 추천 영양제 가져오기
        latest_survey = SurveyResult.objects.filter(user=request.user).order_by('-created_at').first()
        if latest_survey:
            recommended_supplements = get_recommended_supplements(latest_survey)
        else:
            recommended_supplements = []
        
        # 영양소 기준치 데이터 로드
        json_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                nutrient_standards = json.load(f)
        except Exception as e:
            nutrient_standards = {}
            print(f"영양소 기준치 파일 로드 실패: {str(e)}")
        
        context = {
            'latest_analysis': latest_analysis,
            'nutrient_standards': nutrient_standards,
            'liked_supplements': liked_supplements_json,  # JSON 문자열로 전달
            'recommended_supplements': recommended_supplements,
            'debug_info': {
                'file_path': json_path,
            }
        }
        print(f"[DEBUG] context['liked_supplements']: {context['liked_supplements']}")  # 추가: context 전달 확인
        return render(request, 'Mypage/analysis.html', context)
    except Exception as e:
        print(f"[ERROR] analysis_view 오류: {str(e)}")
        # 오류 정보를 포함한 context로 렌더링
        context = {
            'error_message': f'영양소 분석 결과를 불러오는 중 오류가 발생했습니다: {str(e)}',
            'liked_supplements': '[]',  # 빈 배열
            'recommended_supplements': [],
            'nutrient_standards': {}
        }
        return render(request, 'Mypage/analysis.html', context)

def calculate_health_score(survey_result):
    score = 100
    answers = survey_result.answers

    # 수면 시간 감점
    sleep_hours = answers.get('sleep_hours')
    if sleep_hours and float(sleep_hours) < 7:
        score -= 10

    # 운동 빈도 감점
    exercise_frequency = answers.get('exercise_frequency')
    if exercise_frequency in ['전혀 안함', '1-2회']:
        score -= 15

    # 물 섭취량 감점
    water_intake = answers.get('water_intake')
    if water_intake and float(water_intake) < 8:
        score -= 10

    # 건강 상태 감점
    health_status = answers.get('health_status')
    if health_status == '나쁨':
        score -= 20
    elif health_status == '보통':
        score -= 10

    # 생활습관 감점
    if answers.get('smoking'):
        score -= 15
    if answers.get('drinking'):
        score -= 10
    if answers.get('fatigue'):
        score -= 10
    if not answers.get('sleep_well'):
        score -= 10
    if answers.get('still_tired'):
        score -= 10

    return max(0, score)

def get_recommended_supplements(survey_result):
    supplements = []
    
    # 비타민 D 추천 조건
    if survey_result.answers.get('indoor_daytime'):
        supplements.append({
            'name': '비타민 D',
            'reason': '실내 생활이 많고 햇빛 노출이 부족합니다.',
            'benefits': '면역력 강화와 뼈 건강에 도움을 줍니다.'
        })
    
    # 오메가-3 추천 조건
    if survey_result.answers.get('sitting_work') and survey_result.answers.get('exercise_frequency') in ['전혀 안함', '1-2회']:
        supplements.append({
            'name': '오메가-3',
            'reason': '장시간 앉아서 일하고 운동이 부족합니다.',
            'benefits': '심장 건강과 염증 감소에 도움을 줍니다.'
        })
    
    # 비타민 B 복합체 추천 조건
    if survey_result.answers.get('fatigue') or survey_result.answers.get('still_tired'):
        supplements.append({
            'name': '비타민 B 복합체',
            'reason': '피로감이 심하고 수면의 질이 좋지 않습니다.',
            'benefits': '에너지 대사와 신경계 건강에 도움을 줍니다.'
        })
    
    return supplements

def generate_recommendations(survey_result, health_score):
    recommendations = []
    answers = survey_result.answers
    
    # 수면 관련 추천
    sleep_hours = answers.get('sleep_hours')
    if sleep_hours and float(sleep_hours) < 7:
        recommendations.append("수면 시간을 7시간 이상으로 늘리는 것을 권장합니다.")
    
    # 운동 관련 추천
    exercise_frequency = answers.get('exercise_frequency')
    if exercise_frequency in ['전혀 안함', '1-2회']:
        recommendations.append("주 3회 이상의 규칙적인 운동을 시작하는 것을 권장합니다.")
    
    # 물 섭취 관련 추천
    water_intake = answers.get('water_intake')
    if water_intake and float(water_intake) < 8:
        recommendations.append("하루 8잔 이상의 물을 마시는 것을 권장합니다.")
    
    # 생활습관 관련 추천
    if answers.get('smoking'):
        recommendations.append("흡연을 줄이거나 중단하는 것을 권장합니다.")
    if answers.get('drinking'):
        recommendations.append("음주를 줄이는 것을 권장합니다.")
    
    return '\n'.join(recommendations)

def analyze_survey_responses(survey_response):
    """
    설문 응답을 분석하여 결과를 반환합니다.
    """
    result = {
        'health_score': 0,
        'recommendations': [],
        'nutrient_needs': []
    }
    
    # 기본 점수 계산
    score = 0
    max_score = 0
    
    # 운동 관련 점수
    if survey_response.exercise == '예':
        score += 2
    max_score += 2
    
    # 수면 관련 점수
    if survey_response.sleep_well == '예':
        score += 2
    if survey_response.sleep_hours and int(survey_response.sleep_hours) >= 7:
        score += 1
    max_score += 3
    
    # 피로도 관련 점수
    if survey_response.fatigue == '아니오':
        score += 2
    if survey_response.still_tired == '아니오':
        score += 1
    max_score += 3
    
    # 건강 상태 점수
    health_status_scores = {
        '매우 좋음': 3,
        '좋음': 2,
        '보통': 1,
        '나쁨': 0,
        '매우 나쁨': 0
    }
    score += health_status_scores.get(survey_response.health_status, 0)
    max_score += 3
    
    # 최종 점수 계산 (100점 만점)
    result['health_score'] = int((score / max_score) * 100)
    
    # 추천사항 생성
    if survey_response.exercise == '아니오':
        result['recommendations'].append('규칙적인 운동을 시작하는 것을 추천드립니다.')
    
    if survey_response.sleep_hours and int(survey_response.sleep_hours) < 7:
        result['recommendations'].append('수면 시간을 7시간 이상 확보하는 것이 좋습니다.')
    
    if survey_response.fatigue == '예':
        result['recommendations'].append('피로 회복을 위한 영양제 섭취를 고려해보세요.')
    
    # 영양소 필요성 분석
    if survey_response.indoor_daytime == '예':
        result['nutrient_needs'].append('비타민 D')
    
    if survey_response.smoking == '예':
        result['nutrient_needs'].append('비타민 C')
    
    if survey_response.drinking == '예':
        result['nutrient_needs'].append('비타민 B 복합체')
    
    return result

@login_required
@require_POST
def submit_survey(request):
    try:
        # Get all form data
        responses = {}
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                responses[key] = value
        
        # 설문 응답 저장
        survey_response = SurveyResponse.objects.create(
            user=request.user,
            responses=responses,
            age_range=responses.get('age'),
            gender=responses.get('gender'),
            height=responses.get('height'),
            weight=responses.get('weight'),
            sitting_work=responses.get('sitting_work'),
            indoor_daytime=responses.get('indoor_daytime'),
            exercise=responses.get('exercise'),
            smoking=responses.get('smoking'),
            drinking=responses.get('drinking'),
            fatigue=responses.get('fatigue'),
            sleep_well=responses.get('sleep_well'),
            still_tired=responses.get('still_tired'),
            sleep_hours=responses.get('sleep_hours'),
            exercise_frequency=responses.get('exercise_frequency'),
            water_intake=responses.get('water_intake'),
            health_status=responses.get('health_status')
        )

        # 설문 결과 분석 및 저장
        result = analyze_survey_responses(survey_response)
        SurveyResult.objects.create(
            user=request.user,
            answers=responses,
            result=result,
            health_status=responses.get('health_status'),
            recommended_supplements=result.get('nutrient_needs', [])
        )

        return JsonResponse({
            'status': 'success',
            'message': '설문이 성공적으로 제출되었습니다.'
        })
    except Exception as e:
        print(f"Error submitting survey: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def survey_result(request):
    try:
        # 가장 최근 설문 결과 가져오기
        survey_result = SurveyResult.objects.filter(user=request.user).latest('created_at')
        
        # 건강 점수 계산
        health_score = calculate_health_score(survey_result)
        
        # 추천 영양제 가져오기
        recommended_supplements = get_recommended_supplements(survey_result)
        
        # 건강 리포트 생성 또는 업데이트
        health_report, created = UserHealthReport.objects.get_or_create(
            user=request.user,
            survey_result=survey_result,
            defaults={
                'health_score': health_score,
                'recommendations': generate_recommendations(survey_result, health_score)
            }
        )
        
        if not created:
            health_report.health_score = health_score
            health_report.recommendations = generate_recommendations(survey_result, health_score)
            health_report.save()
        
        context = {
            'survey_result': survey_result,
            'health_score': health_score,
            'recommended_supplements': recommended_supplements,
            'recommendations': health_report.recommendations.split('\n')
        }
        return render(request, 'Mypage/survey_result.html', context)
    except SurveyResult.DoesNotExist:
        return render(request, 'Mypage/survey_result.html', {
            'message': '설문 응답이 없습니다. 먼저 설문을 완료해주세요.'
        })
    except Exception as e:
        print(f"Error in survey_result view: {str(e)}")
        return render(request, 'Mypage/survey_result.html', {
            'message': '설문 결과를 불러오는 중 오류가 발생했습니다.'
        })

@login_required
def nutrient_analysis_view(request):
    # 오늘 날짜의 영양소 섭취 기록 가져오기
    today = timezone.now().date()
    nutrient_intakes = UserNutrientIntake.objects.filter(
        user=request.user,
        date=today
    ).select_related('nutrient')

    # 섭취량 백분율 계산
    for intake in nutrient_intakes:
        intake.percentage = min(100, (intake.amount / intake.nutrient.daily_recommended) * 100)

    # 최신 영양분석 결과 가져오기
    latest_analysis = NutrientAnalysis.objects.filter(
        user=request.user
    ).order_by('-analysis_date').first()

    context = {
        'nutrient_intakes': nutrient_intakes,
        'latest_analysis': latest_analysis,
    }
    return render(request, 'nutrient_analysis.html', context)

@login_required
@require_POST
def add_nutrient_intake(request):
    try:
        data = json.loads(request.body)
        nutrient_id = data.get('nutrient_id')
        amount = data.get('amount')
        date = data.get('date', timezone.now().date())

        nutrient = Nutrient.objects.get(id=nutrient_id)
        intake = UserNutrientIntake.objects.create(
            user=request.user,
            nutrient=nutrient,
            amount=amount,
            date=date
        )

        return JsonResponse({
            'status': 'success',
            'message': '영양소 섭취 기록이 추가되었습니다.',
            'intake': {
                'id': intake.id,
                'nutrient_name': nutrient.name,
                'amount': amount,
                'unit': nutrient.unit,
                'percentage': min(100, (amount / nutrient.daily_recommended) * 100)
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
@require_POST
def add_manual_nutrient_intake(request):
    try:
        data = json.loads(request.body)
        nutrient_name = data.get('nutrient_name')
        unit = data.get('unit')
        amount = data.get('amount', 0.0)

        # 영양소 기준치 데이터 로드
        json_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                nutrient_standards = json.load(f)
        except Exception as e:
            print(f"영양소 기준치 파일 로드 실패: {str(e)}")
            nutrient_standards = {}

        # 영양소가 존재하는지 확인하고, 없으면 생성 (ID 충돌 완전 방지)
        nutrient = None
        
        # 먼저 기존 영양소 찾기
        try:
            nutrient = Nutrient.objects.get(name=nutrient_name)
        # 기존 영양소인 경우 권장량 업데이트
            nutrient.unit = unit
            nutrient.daily_recommended = nutrient_standards.get(nutrient_name, {}).get('recommended_amount', 100)
            nutrient.description = nutrient_standards.get(nutrient_name, {}).get('description', '')
            nutrient.save()
            print(f"기존 영양소 업데이트: {nutrient_name}, 권장량: {nutrient.daily_recommended}")
        except Nutrient.DoesNotExist:
            # 새 영양소 생성 (ID 충돌 방지를 위해 시퀀스 재설정 후 생성)
            try:
                # 시퀀스 재설정 (테이블명 대소문자 구분)
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT setval(pg_get_serial_sequence('\"Mypage_nutrient\"', 'id'), COALESCE((SELECT MAX(id) FROM \"Mypage_nutrient\"), 1));")
                
                # 새 영양소 생성
                nutrient = Nutrient.objects.create(
                    name=nutrient_name,
                    unit=unit,
                    daily_recommended=nutrient_standards.get(nutrient_name, {}).get('recommended_amount', 100),
                    description=nutrient_standards.get(nutrient_name, {}).get('description', ''),
                    category='기타'  # 기본 카테고리
                )
                print(f"새 영양소 생성: {nutrient_name}, 권장량: {nutrient.daily_recommended}")
            except Exception as create_error:
                print(f"영양소 생성 중 오류: {str(create_error)}")
                # 생성 실패 시 기존 영양소를 다시 찾아보기
                try:
                    nutrient = Nutrient.objects.get(name=nutrient_name)
                except Nutrient.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'영양소 "{nutrient_name}" 생성에 실패했습니다. 오류: {str(create_error)}'
                    }, status=400)

        if not nutrient:
            return JsonResponse({
                'status': 'error',
                'message': f'영양소 "{nutrient_name}"를 찾을 수 없거나 생성할 수 없습니다.'
            }, status=400)

        # 영양소 섭취 기록 생성 (amount, unit만)
        intake = UserNutrientIntake.objects.create(
            user=request.user,
            nutrient=nutrient,
            amount=amount,
            unit=unit
        )

        # 영양분석 실행
        try:
            analyze_nutrients(request)
        except Exception as e:
            print(f"영양분석 실행 중 오류 발생: {str(e)}")
            # 분석 실패해도 기록은 저장됨

        return JsonResponse({
            'status': 'success',
            'message': '영양소 섭취 기록이 추가되었습니다.',
            'intake': {
                'id': intake.id,
                'nutrient_name': nutrient.name,
                'amount': intake.amount,
                'unit': intake.unit
            }
        })
    except Exception as e:
        print("영양소 추가 오류:", str(e))
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
@require_POST
def analyze_nutrients(request):
    try:
        print("영양분석 시작")
        
        # 이전 분석 결과 삭제
        NutrientAnalysis.objects.filter(user=request.user).delete()
        
        # 최근 7일간의 영양소 섭취 기록 가져오기
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        intakes = UserNutrientIntake.objects.filter(
            user=request.user,
            created_at__date__range=[start_date, end_date]
        ).select_related('nutrient')
        
        print(f"가져온 섭취 기록 수: {intakes.count()}")
        
        if not intakes.exists():
            print("분석할 섭취 기록이 없습니다.")
            return JsonResponse({
                'status': 'success',
                'message': '아직 영양소 섭취 기록이 없습니다.',
                'analysis': {
                    'overall_score': 0,
                    'details': [],
                    'recommendations': ['영양소 섭취 기록을 추가해주세요.']
                }
            })

        # 영양소별 평균 섭취량 계산
        nutrient_averages = {}
        for intake in intakes:
            nutrient_name = intake.nutrient.name
            if nutrient_name not in nutrient_averages:
                # 권장량 확인 및 로드
                recommended = intake.nutrient.daily_recommended
                if not recommended or recommended <= 0:
                    # 기준치 파일에서 권장량 로드
                    json_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            nutrient_standards = json.load(f)
                        recommended = nutrient_standards.get(nutrient_name, {}).get('recommended_amount', 100)
                        # 영양소 권장량 업데이트
                        intake.nutrient.daily_recommended = recommended
                        intake.nutrient.save()
                        print(f"영양소 권장량 업데이트: {nutrient_name} = {recommended}")
                    except Exception as e:
                        print(f"기준치 파일 로드 실패: {str(e)}")
                        recommended = 100
                
                nutrient_averages[nutrient_name] = {
                    'total': 0,
                    'count': 0,
                    'recommended': recommended
                }
                print(f"영양소 초기화: {nutrient_name}, 권장량: {recommended}")
            
            nutrient_averages[nutrient_name]['total'] += intake.amount
            nutrient_averages[nutrient_name]['count'] += 1

        print("영양소별 평균:", nutrient_averages)

        # 평균 섭취량 계산 및 점수 산출
        overall_score = 0
        details = []
        recommendations = []

        for nutrient_name, data in nutrient_averages.items():
            avg_intake = data['total'] / data['count']
            recommended = data['recommended']
            
            print(f"분석 중: {nutrient_name}, 평균 섭취량: {avg_intake}, 권장량: {recommended}")
            
            if recommended > 0:
                percentage = (avg_intake / recommended) * 100
                score = min(100, percentage)
                overall_score += score

                details.append(f"{nutrient_name}: {avg_intake:.1f} (권장량 {recommended} 대비 {percentage:.1f}%)")

                if percentage < 80:
                    recommendations.append(f"{nutrient_name} 섭취량이 부족합니다. 권장량의 {percentage:.1f}%만 섭취하고 있습니다.")
                elif percentage > 120:
                    recommendations.append(f"{nutrient_name} 섭취량이 과다합니다. 권장량의 {percentage:.1f}%를 섭취하고 있습니다.")
                else:
                    recommendations.append(f"{nutrient_name} 섭취량이 적절합니다. 권장량의 {percentage:.1f}%를 섭취하고 있습니다.")
            else:
                print(f"권장량이 0인 영양소: {nutrient_name}")
                details.append(f"{nutrient_name}: {avg_intake:.1f} (권장량 없음)")
        
        # 전체 점수 계산 (100점 만점)
        overall_score = overall_score / len(nutrient_averages) if nutrient_averages else 0

        print(f"전체 점수: {overall_score}")
        print("상세 정보:", details)
        print("추천사항:", recommendations)

        # 분석 결과 저장
        analysis = NutrientAnalysis.objects.create(
            user=request.user,
            date=end_date,
            total_nutrients=json.dumps(nutrient_averages, ensure_ascii=False),
            analysis_result=f"전체 영양소 섭취 점수: {overall_score:.1f}점",
            overall_score=overall_score,
            details=json.dumps(details, ensure_ascii=False),
            recommendations='\n'.join(recommendations)
        )

        return JsonResponse({
            'status': 'success',
            'message': '영양분석이 완료되었습니다.',
            'analysis': {
                'overall_score': overall_score,
                'details': details,
                'recommendations': recommendations
            }
        })
    except Exception as e:
        print(f"영양분석 중 오류 발생: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_nutrient_data(request):
    try:
        # 최신 영양분석 결과 가져오기
        latest_analysis = NutrientAnalysis.objects.filter(
            user=request.user
        ).order_by('-date').first()

        if not latest_analysis:
            print("사용자의 영양분석 결과가 없습니다.")
            return JsonResponse({
                'status': 'success',
                'data': {
                    'total_nutrients': {},
                    'analysis_result': '',
                    'overall_score': 0,
                    'details': '',
                    'recommendations': ''
                }
            })

        print(f"총 영양소 수: {latest_analysis.total_nutrients}")
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'total_nutrients': latest_analysis.total_nutrients,
                'analysis_result': latest_analysis.analysis_result,
                'overall_score': latest_analysis.overall_score,
                'details': latest_analysis.details,
                'recommendations': latest_analysis.recommendations
            }
        })
    except Exception as e:
        print(f"영양소 데이터 가져오기 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_favorite_products(request):
    try:
        print(f"사용자: {request.user}")
        
        # 사용자가 좋아요한 영양제 가져오기
        likes = Like.objects.filter(user=request.user).select_related('product')
        print(f"좋아요 수: {likes.count()}")
        
        liked_products = []
        
        for like in likes:
            product = like.product
            print(f"제품: {product.title}")
            liked_products.append({
                'id': product.id,
                'title': product.title,
                'brand': product.brand,
                'image_url': product.image_link,
                'price': product.total_price,
                'rating': product.average_rating,
                'reviews_count': product.total_reviews,
                'created_at': like.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        print(f"반환할 제품 수: {len(liked_products)}")
        
        return JsonResponse({
            'status': 'success',
            'data': liked_products
        })
    except Exception as e:
        print(f"get_favorite_products 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_nutrient_history(request):
    try:
        intakes = UserNutrientIntake.objects.filter(
            user=request.user
        ).select_related('nutrient').order_by('-created_at')

        history = []
        for intake in intakes:
            history.append({
                'id': intake.id,
                'nutrient_name': intake.nutrient.name,
                'amount': intake.amount,
                'unit': intake.unit,
                'created_at': intake.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return JsonResponse({
            'status': 'success',
            'history': history
        })
    except Exception as e:
        print(f"영양소 기록 가져오기 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def update_nutrient_intake(request):
    try:
        data = json.loads(request.body)
        intake_id = data.get('intake_id')
        nutrient_name = data.get('nutrient')
        amount = data.get('amount', 0.0)
        unit = data.get('unit', '')

        # 모든 필수 필드가 있는지 확인
        if not all([intake_id, nutrient_name]):
            return JsonResponse({
                'status': 'error',
                'message': '모든 필수 필드를 입력해주세요.'
            }, status=400)

        # nutrient 객체 가져오기
        try:
            nutrient = Nutrient.objects.get(name=nutrient_name)
        except Nutrient.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '해당 영양소를 찾을 수 없습니다.'
            }, status=404)

        # intake 가져와서 업데이트
        try:
            intake = UserNutrientIntake.objects.get(id=intake_id, user=request.user)
            intake.nutrient = nutrient
            intake.amount = amount
            intake.unit = unit
            intake.save()

            return JsonResponse({
                'status': 'success',
                'message': '영양소 섭취 기록이 업데이트되었습니다.'
            })
        except UserNutrientIntake.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '해당 섭취 기록을 찾을 수 없습니다.'
            }, status=404)

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '잘못된 요청 형식입니다.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def delete_nutrient_intake(request):
    try:
        data = json.loads(request.body)
        # intake_id와 id 두 가지 키 모두 처리
        intake_id = data.get('intake_id') or data.get('id')
        
        if not intake_id:
            return JsonResponse({
                'status': 'error',
                'message': '삭제할 기록의 ID가 제공되지 않았습니다.'
            }, status=400)

        intake = UserNutrientIntake.objects.get(id=intake_id, user=request.user)
        intake.delete()

        return JsonResponse({
            'status': 'success',
            'message': '영양소 섭취 기록이 삭제되었습니다.'
        })
    except UserNutrientIntake.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '해당 기록을 찾을 수 없습니다.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
@require_POST
def delete_all_nutrient_records(request):
    """모든 영양소 섭취 기록 삭제"""
    try:
        # 현재 사용자의 모든 영양소 섭취 기록 삭제
        deleted_count = UserNutrientIntake.objects.filter(user=request.user).delete()[0]
        
        return JsonResponse({
            'status': 'success',
            'message': f'{deleted_count}개의 영양소 섭취 기록이 삭제되었습니다.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_nutrients_list(request):
    try:
        nutrients = Nutrient.objects.all().order_by('name')
        nutrients_list = [{'id': n.id, 'name': n.name} for n in nutrients]
        return JsonResponse({
            'status': 'success',
            'nutrients': nutrients_list
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def load_liked_products_nutrients(request):
    """
    좋아요한 제품들의 영양성분 정보를 Products 테이블에서 가져와서 UserNutrientIntake에 저장
    """
    try:
        # 사용자가 좋아요한 제품들 가져오기
        liked_products = Like.objects.filter(user=request.user).select_related('product')
        
        print(f"좋아요한 제품 수: {liked_products.count()}")
        
        if not liked_products.exists():
            return JsonResponse({
                'status': 'info',
                'message': '좋아요한 제품이 없습니다.'
            })
        
        added_count = 0
        not_found_count = 0
        
        for like in liked_products:
            product = like.product
            product_title = product.title
            print(f"\n처리 중인 제품: {product_title}")
            
            # 제품의 ingredients 정보 가져오기
            ingredients = product.ingredients
            print(f"ingredients 길이: {len(str(ingredients))}")
            print(f"ingredients 내용: {str(ingredients)[:200]}...")
            
            if ingredients and isinstance(ingredients, str) and ingredients.strip():
                # ingredients에서 영양성분 정보 파싱
                nutrients = parse_nutrients_from_text(ingredients)
                print(f"파싱된 영양성분: {nutrients}")
                
                # 각 영양성분을 UserNutrientIntake에 저장
                for nutrient_name, amount_info in nutrients.items():
                    # amount_info format: "100 mg"
                    try:
                        amount_str, unit = amount_info.split(' ', 1)
                        amount = float(amount_str)
                        
                        # Nutrient 모델에서 해당 영양소 찾기 또는 생성
                        nutrient, created = Nutrient.objects.get_or_create(
                            name=nutrient_name,
                            defaults={
                                'description': f'{nutrient_name} 영양소',
                                'daily_recommended': 100,  # 기본값
                                'unit': 'mg',
                                'category': '기타'
                            }
                        )
                        
                        # UserNutrientIntake에 저장
                        UserNutrientIntake.objects.create(
                            user=request.user,
                            nutrient=nutrient,
                            amount=amount,
                            unit=unit
                        )
                        
                        added_count += 1
                        print(f"영양성분 추가: {nutrient_name} - {amount}{unit}")
                    except (ValueError, AttributeError) as e:
                        print(f"영양소 파싱 오류 ({nutrient_name}): {str(e)}")
            else:
                not_found_count += 1
                print(f"제품에 ingredients 정보가 없음: {product_title}")
        
        print(f"총 추가된 영양성분: {added_count}개")
        print(f"찾을 수 없는 제품: {not_found_count}개")
        
        return JsonResponse({
            'status': 'success',
            'message': f'좋아요한 제품 {len(liked_products)}개 중 {added_count}개의 영양성분 정보가 추가되었습니다.',
            'added_count': added_count,
            'not_found_count': not_found_count
        })
        
    except Exception as e:
        print(f"좋아요한 제품 영양성분 로드 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'영양성분 정보 로드 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

def parse_nutrients_from_text(text):
    """텍스트에서 영양소 정보 추출 (OCR용)"""
    nutrients = {}
    
    # 1. 리스트/딕셔너리 구조 파싱 시도
    try:
        data = ast.literal_eval(text)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'ingredient_name' in item and 'amount' in item and 'unit' in item:
                    nutrients[item['ingredient_name']] = f"{item['amount']} {item['unit']}"
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (int, float)):
                    nutrients[k] = f"{v} mg"
        if nutrients:
            return nutrients
    except Exception as e:
        pass  # 파싱 실패 시 아래 문자열 파싱으로 진행

    # 2. OCR 텍스트용 개선된 패턴 매칭 (영어 중심)
    nutrient_patterns = [
        # 영어 영양소 기본 패턴들
        r'([A-Za-z]+)\s+([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        r'([A-Za-z]+)\s*[:\-]?\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        # 콤마가 포함된 숫자 패턴 (10,000 mcg)
        r'([A-Za-z]+)\s+([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        # 단위가 앞에 오는 패턴
        r'([A-Za-z]+)\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        # 한글 패턴들 (기존)
        r'비타민\s*([A-Z])\s*[:\-]?\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        r'([A-Za-z가-힣]+)\s*[:\-]?\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
    ]
    
    for pattern in nutrient_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 3:
                nutrient_name = match.group(1).strip()
                amount_str = match.group(2).replace(',', '')
                unit = match.group(3)
                
                # 영양소 이름이 너무 짧거나 숫자인 경우 제외
                if len(nutrient_name) < 2 or nutrient_name.isdigit():
                    continue
                
                try:
                    amount = float(amount_str)
                    # 이미 존재하는 영양소인 경우 더 큰 값으로 업데이트
                    if nutrient_name in nutrients:
                        existing_amount = float(nutrients[nutrient_name].split()[0])
                        if amount > existing_amount:
                            nutrients[nutrient_name] = f"{amount} {unit}"
                    else:
                        nutrients[nutrient_name] = f"{amount} {unit}"
                except ValueError:
                    continue
    
    # 3. 특별한 영어 영양소 패턴들 (OCR에서 자주 나오는 형태)
    special_patterns = [
        # Biotin 패턴들
        (r'Biotin\s+([\d,\.]+)\s*mcg', 'Biotin'),
        (r'Biotin\s+([\d,\.]+)\s*mg', 'Biotin'),
        # Vitamin 패턴들
        (r'Vitamin\s+C\s+([\d,\.]+)\s*mg', 'Vitamin C'),
        (r'Vitamin\s+D\s+([\d,\.]+)\s*iu', 'Vitamin D'),
        (r'Vitamin\s+B12\s+([\d,\.]+)\s*mcg', 'Vitamin B12'),
        (r'Vitamin\s+B6\s+([\d,\.]+)\s*mg', 'Vitamin B6'),
        (r'Vitamin\s+E\s+([\d,\.]+)\s*iu', 'Vitamin E'),
        # 미네랄 패턴들
        (r'Calcium\s+([\d,\.]+)\s*mg', 'Calcium'),
        (r'Iron\s+([\d,\.]+)\s*mg', 'Iron'),
        (r'Zinc\s+([\d,\.]+)\s*mg', 'Zinc'),
        (r'Magnesium\s+([\d,\.]+)\s*mg', 'Magnesium'),
        (r'Selenium\s+([\d,\.]+)\s*mcg', 'Selenium'),
        # 기타 영양소들
        (r'Folic\s+Acid\s+([\d,\.]+)\s*mcg', 'Folic Acid'),
        (r'Omega\s*3\s+([\d,\.]+)\s*mg', 'Omega 3'),
        (r'CoQ10\s+([\d,\.]+)\s*mg', 'CoQ10'),
        # 한글 패턴들 (기존)
        (r'비타민\s*C\s+([\d,\.]+)\s*mg', '비타민 C'),
        (r'비타민\s*D\s+([\d,\.]+)\s*iu', '비타민 D'),
        (r'비타민\s*B12\s+([\d,\.]+)\s*mcg', '비타민 B12'),
    ]
    
    for pattern, nutrient_name in special_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                unit = 'mg' if 'mg' in pattern else ('mcg' if 'mcg' in pattern else 'iu')
                nutrients[nutrient_name] = f"{amount} {unit}"
            except ValueError:
                continue
                
    # 4. 추가적인 OCR 텍스트 정리 및 패턴 매칭
    # 줄바꿈이나 특수문자 제거 후 다시 시도
    cleaned_text = re.sub(r'[^\w\s\d,\.:()-]', ' ', text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    # 정리된 텍스트에서 다시 패턴 매칭
    for pattern in nutrient_patterns:
        matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 3:
                nutrient_name = match.group(1).strip()
                amount_str = match.group(2).replace(',', '')
                unit = match.group(3)
                
                if len(nutrient_name) < 2 or nutrient_name.isdigit():
                    continue
                    
                try:
                    amount = float(amount_str)
                    if nutrient_name not in nutrients:  # 중복 방지
                        nutrients[nutrient_name] = f"{amount} {unit}"
                except ValueError:
                    continue
    
    # 5. 디버깅을 위한 로그 추가
    print(f"OCR 텍스트: {text[:200]}...")  # 처음 200자만 출력
    print(f"추출된 영양소: {nutrients}")
    
    return nutrients

@login_required
def load_selected_products_nutrients(request):
    """
    선택한 제품들의 영양성분 정보를 Products 테이블에서 가져와서 UserNutrientIntake에 저장
    """
    try:
        # POST 데이터에서 선택된 제품 ID들 가져오기
        data = json.loads(request.body)
        selected_product_ids = data.get('product_ids', [])
        
        if not selected_product_ids:
            return JsonResponse({
                'status': 'error',
                'message': '선택된 제품이 없습니다.'
            })
        
        # 선택된 제품들 가져오기
        selected_products = Products.objects.filter(id__in=selected_product_ids)
        
        print(f"선택된 제품 수: {selected_products.count()}")
        
        added_count = 0
        not_found_count = 0
        
        for product in selected_products:
            product_title = product.title
            print(f"\n처리 중인 제품: {product_title}")
            
            # 제품의 ingredients 정보 가져오기
            ingredients = product.ingredients
            print(f"ingredients 길이: {len(str(ingredients))}")
            print(f"ingredients 내용: {str(ingredients)[:200]}...")
            
            if ingredients and isinstance(ingredients, str) and ingredients.strip():
                # ingredients에서 영양성분 정보 파싱
                nutrients = parse_nutrients_from_text(ingredients)
                print(f"파싱된 영양성분: {nutrients}")
                
                # 각 영양성분을 UserNutrientIntake에 저장
                for nutrient_name, amount_info in nutrients.items():
                    # amount_info format: "100 mg"
                    try:
                        amount_str, unit = amount_info.split(' ', 1)
                        amount = float(amount_str)
                        
                        # Nutrient 모델에서 해당 영양소 찾기 또는 생성
                        nutrient, created = Nutrient.objects.get_or_create(
                            name=nutrient_name,
                            defaults={
                                'description': f'{nutrient_name} 영양소',
                                'daily_recommended': 100,  # 기본값
                                'unit': 'mg',
                                'category': '기타'
                            }
                        )
                        
                        # UserNutrientIntake에 저장
                        UserNutrientIntake.objects.create(
                            user=request.user,
                            nutrient=nutrient,
                            amount=amount,
                            unit=unit
                        )
                        
                        added_count += 1
                        print(f"영양성분 추가: {nutrient_name} - {amount}{unit}")
                    except (ValueError, AttributeError) as e:
                        print(f"영양소 파싱 오류 ({nutrient_name}): {str(e)}")
                        continue
            else:
                not_found_count += 1
                print(f"제품에 ingredients 정보가 없음: {product_title}")
        
        print(f"총 추가된 영양성분: {added_count}개")
        print(f"찾을 수 없는 제품: {not_found_count}개")
        
        return JsonResponse({
            'status': 'success', 
            'message': f'선택한 제품 {len(selected_products)}개 중 {added_count}개의 영양성분 정보가 추가되었습니다.',
            'added_count': added_count,
            'not_found_count': not_found_count
        })
        
    except Exception as e:
        print(f"선택한 제품 영양성분 로드 오류: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': f'영양성분 정보 로드 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

@login_required
def like_list(request):
    try:
        # 사용자가 좋아요한 영양제 가져오기
        like_list = Like.objects.filter(user=request.user).select_related('product')
        
        # 추천 영양제 가져오기
        latest_survey = SurveyResult.objects.filter(user=request.user).order_by('-created_at').first()
        if latest_survey:
            recommended_supplements = get_recommended_supplements(latest_survey)
        else:
            recommended_supplements = []
        
        context = {
            'user': request.user,
            'like_list': like_list,
            'recommended_supplements': recommended_supplements
        }
        return render(request, 'Mypage/like.html', context)
    except Exception as e:
        messages.error(request, f'좋아요 목록을 불러오는 중 오류가 발생했습니다: {str(e)}')
        return redirect('mypage')

@login_required
@require_POST
def like_add(request):
    try:
        product_id = request.POST.get('product_id')
        product = Products.objects.get(pk=product_id)
        Like.objects.get_or_create(user=request.user, product_id=product_id)
        UserLog.objects.create(user=request.user, product=product, action='like')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def like_delete(request):
    try:
        product_id = request.POST.get('product_id')
        product = Products.objects.get(pk=product_id)
        like = Like.objects.get(user=request.user, product_id=product_id)
        like.delete()
        UserLog.objects.create(user=request.user, product=product, action='unlike')
        return JsonResponse({'success': True})
    except Like.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def get_product_nutrients(request, product_id):
    try:
        product = Products.objects.get(id=product_id)
        # 여기서 제품의 영양소 정보를 가져오는 로직을 구현해야 합니다
        # 예시 데이터:
        nutrients = [
            {
                'name': '비타민 C',
                'amount': 100,
                'unit': 'mg'
            },
            {
                'name': '비타민 D',
                'amount': 10,
                'unit': 'µg'
            }
        ]

        return JsonResponse({
            'status': 'success',
            'nutrients': nutrients
        })
    except Products.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '제품을 찾을 수 없습니다.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def product_click(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    # user = User.objects.get(pk=1)
    user = request.user
    try:
        product = Products.objects.get(pk=product_id)
        # UserLog 저장 (click)
        UserLog.objects.create(user=user, product=product, action='click')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def chatbot_view(request):
    """Widok czatbota"""
    return render(request, 'Chatbot/ChatNuti.html')

@login_required
def ocr_extract(request):
    """OCR ekstrakcja składników z obrazu"""
    if request.method == 'POST':
        try:
            # Sprawdź czy plik został przesłany
            if 'image' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': '이미지 파일이 업로드되지 않았습니다.'
                }, status=400)
            
            image_file = request.FILES['image']
            
            # Sprawdź typ pliku
            if not image_file.content_type.startswith('image/'):
                return JsonResponse({
                    'status': 'error',
                    'message': '올바른 이미지 파일을 업로드해주세요.'
                }, status=400)
            
            # Otwórz obraz
            image = Image.open(image_file)
            
            # OCR - ekstrakcja tekstu
            try:
                text = pytesseract.image_to_string(image, lang='kor+eng')
                print(f"OCR 결과: {text}")
            except Exception as ocr_error:
                print(f"OCR 오류: {str(ocr_error)}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'OCR 처리 중 오류가 발생했습니다: {str(ocr_error)}'
                }, status=500)
            
            # Tekst가 비어있는지 확인
            if not text.strip():
                return JsonResponse({
                    'status': 'error',
                    'message': '이미지에서 텍스트를 인식할 수 없습니다. 더 선명한 이미지를 업로드해주세요.'
                }, status=400)

            # 영양소 정보 추출 (간단한 패턴 매칭)
            nutrients = extract_nutrients_from_text(text)
            
            if nutrients:
                return JsonResponse({
                    'status': 'success',
                    'ingredients': nutrients,
                    'raw_text': text,
                    'debug_info': {
                        'extracted_count': len(nutrients),
                        'raw_text': text[:500] + '...' if len(text) > 500 else text
                    }
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '영양소 정보를 찾을 수 없습니다.',
                    'raw_text': text,
                    'debug_info': {
                        'raw_text': text[:500] + '...' if len(text) > 500 else text,
                        'has_numbers': any(char.isdigit() for char in text),
                        'has_units': any(unit in text.lower() for unit in ['mg', 'g', 'mcg', 'μg', 'iu', 'ml'])
                    }
                })
                
        except Exception as e:
            print(f"OCR 처리 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'이미지 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)

def extract_nutrients_from_text(text):
    """텍스트에서 영양소 정보 추출 (OCR용)"""
    nutrients = {}
    
    # 1. 리스트/딕셔너리 구조 파싱 시도
    try:
        data = ast.literal_eval(text)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'ingredient_name' in item and 'amount' in item and 'unit' in item:
                    nutrients[item['ingredient_name']] = f"{item['amount']} {item['unit']}"
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (int, float)):
                    nutrients[k] = f"{v} mg"
        if nutrients:
            return nutrients
    except Exception as e:
        pass  # 파싱 실패 시 아래 문자열 파싱으로 진행

    # 2. OCR 텍스트용 개선된 패턴 매칭 (영어 중심)
    nutrient_patterns = [
        # 영어 영양소 기본 패턴들
        r'([A-Za-z]+)\s+([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        r'([A-Za-z]+)\s*[:\-]?\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        # 콤마가 포함된 숫자 패턴 (10,000 mcg)
        r'([A-Za-z]+)\s+([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        # 단위가 앞에 오는 패턴
        r'([A-Za-z]+)\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        # 한글 패턴들 (기존)
        r'비타민\s*([A-Z])\s*[:\-]?\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
        r'([A-Za-z가-힣]+)\s*[:\-]?\s*([\d,\.]+)\s*(mg|g|mcg|μg|iu|ml)',
    ]
    
    for pattern in nutrient_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 3:
                nutrient_name = match.group(1).strip()
                amount_str = match.group(2).replace(',', '')
                unit = match.group(3)
                
                # 영양소 이름이 너무 짧거나 숫자인 경우 제외
                if len(nutrient_name) < 2 or nutrient_name.isdigit():
                    continue
                
                try:
                    amount = float(amount_str)
                    # 이미 존재하는 영양소인 경우 더 큰 값으로 업데이트
                    if nutrient_name in nutrients:
                        existing_amount = float(nutrients[nutrient_name].split()[0])
                        if amount > existing_amount:
                            nutrients[nutrient_name] = f"{amount} {unit}"
                    else:
                        nutrients[nutrient_name] = f"{amount} {unit}"
                except ValueError:
                    continue
    
    # 3. 특별한 영어 영양소 패턴들 (OCR에서 자주 나오는 형태)
    special_patterns = [
        # Biotin 패턴들
        (r'Biotin\s+([\d,\.]+)\s*mcg', 'Biotin'),
        (r'Biotin\s+([\d,\.]+)\s*mg', 'Biotin'),
        # Vitamin 패턴들
        (r'Vitamin\s+C\s+([\d,\.]+)\s*mg', 'Vitamin C'),
        (r'Vitamin\s+D\s+([\d,\.]+)\s*iu', 'Vitamin D'),
        (r'Vitamin\s+B12\s+([\d,\.]+)\s*mcg', 'Vitamin B12'),
        (r'Vitamin\s+B6\s+([\d,\.]+)\s*mg', 'Vitamin B6'),
        (r'Vitamin\s+E\s+([\d,\.]+)\s*iu', 'Vitamin E'),
        # 미네랄 패턴들
        (r'Calcium\s+([\d,\.]+)\s*mg', 'Calcium'),
        (r'Iron\s+([\d,\.]+)\s*mg', 'Iron'),
        (r'Zinc\s+([\d,\.]+)\s*mg', 'Zinc'),
        (r'Magnesium\s+([\d,\.]+)\s*mg', 'Magnesium'),
        (r'Selenium\s+([\d,\.]+)\s*mcg', 'Selenium'),
        # 기타 영양소들
        (r'Folic\s+Acid\s+([\d,\.]+)\s*mcg', 'Folic Acid'),
        (r'Omega\s*3\s+([\d,\.]+)\s*mg', 'Omega 3'),
        (r'CoQ10\s+([\d,\.]+)\s*mg', 'CoQ10'),
        # 한글 패턴들 (기존)
        (r'비타민\s*C\s+([\d,\.]+)\s*mg', '비타민 C'),
        (r'비타민\s*D\s+([\d,\.]+)\s*iu', '비타민 D'),
        (r'비타민\s*B12\s+([\d,\.]+)\s*mcg', '비타민 B12'),
    ]
    
    for pattern, nutrient_name in special_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                unit = 'mg' if 'mg' in pattern else ('mcg' if 'mcg' in pattern else 'iu')
                nutrients[nutrient_name] = f"{amount} {unit}"
            except ValueError:
                continue
    
    # 4. 추가적인 OCR 텍스트 정리 및 패턴 매칭
    # 줄바꿈이나 특수문자 제거 후 다시 시도
    cleaned_text = re.sub(r'[^\w\s\d,\.:()-]', ' ', text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    # 정리된 텍스트에서 다시 패턴 매칭
    for pattern in nutrient_patterns:
        matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 3:
                nutrient_name = match.group(1).strip()
                amount_str = match.group(2).replace(',', '')
                unit = match.group(3)
                
                if len(nutrient_name) < 2 or nutrient_name.isdigit():
                    continue
                    
                try:
                    amount = float(amount_str)
                    if nutrient_name not in nutrients:  # 중복 방지
                        nutrients[nutrient_name] = f"{amount} {unit}"
                except ValueError:
                    continue
    
    # 5. 디버깅을 위한 로그 추가
    print(f"OCR 텍스트: {text[:200]}...")  # 처음 200자만 출력
    print(f"추출된 영양소: {nutrients}")
    
    return nutrients

@csrf_exempt
@api_view(["POST", "DELETE", "GET"])
@permission_classes([IsAuthenticated])
def like_api(request):
    """
    좋아요 API 엔드포인트
    POST: 좋아요 추가
    DELETE: 좋아요 제거
    GET: 좋아요 상태 확인
    """
    # 로그인한 사용자 ID 사용
    user_id = request.user.id
    
    if request.method == "GET":
        # 쿼리 파라미터에서 product_id 가져오기
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({"error": "상품 ID가 필요합니다."}, status=400)
        
        product = get_object_or_404(Products, id=product_id)
        is_liked = Like.objects.filter(user_id=user_id, product=product).exists()
        
        return JsonResponse({
            "is_liked": is_liked
        })
        
    elif request.method in ["POST", "DELETE"]:
        try:
            
            product_id = request.data.get('product_id')
            if not product_id:
                return JsonResponse({"error": "상품 ID가 필요합니다."}, status=400)
            
            product = get_object_or_404(Products, id=product_id)
            
            if request.method == "POST":
                # 좋아요 추가 (이미 있으면 무시)
                like, created = Like.objects.get_or_create(
                    user=request.user,
                    product=product
                )
                return JsonResponse({
                    "message": "좋아요가 추가되었습니다." if created else "이미 좋아요가 되어있습니다.",
                    "is_liked": True
                })
                
            elif request.method == "DELETE":
                # 좋아요 제거
                like = Like.objects.filter(user=request.user, product=product)
                if like.exists():
                    like.delete()
                    return JsonResponse({
                        "message": "좋아요가 제거되었습니다.",
                        "is_liked": False
                    })
                else:
                    return JsonResponse({
                        "message": "좋아요가 되어있지 않습니다.",
                        "is_liked": False
                    })
                    
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "지원하지 않는 메서드입니다."}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def product_purchase(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    # user = User.objects.get(pk=1)
    user = request.user
    try:
        product = Products.objects.get(pk=product_id)
        # UserLog 저장 (click)
        UserLog.objects.create(user=user, product=product, action='purchase')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def save_ocr_ingredients(request):
    """Zapisywanie składników z OCR"""
    try:
        data = json.loads(request.body)
        ingredients = data.get('ingredients', {})
        
        # 각 영양소를 UserNutrientIntake에 저장
        added_count = 0
        for nutrient_name, amount_info in ingredients.items():
            # amount_info format: "100 mg"
            try:
                amount_str, unit = amount_info.split(' ', 1)
                amount = float(amount_str)
                
                # Nutrient 모델에서 해당 영양소 찾기 또는 생성
                nutrient, created = Nutrient.objects.get_or_create(
                    name=nutrient_name,
                    defaults={'description': f'OCR로 인식된 {nutrient_name}'}
                )
                
                # UserNutrientIntake에 저장
                UserNutrientIntake.objects.create(
                    user=request.user,
                    nutrient=nutrient,
                    amount=amount,
                    unit=unit
                )
                added_count += 1
                
            except (ValueError, AttributeError) as e:
                print(f"영양소 파싱 오류 ({nutrient_name}): {str(e)}")
                continue
        
        return JsonResponse({
            'status': 'success',
            'message': f'{added_count}개의 영양소가 성공적으로 저장되었습니다.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
