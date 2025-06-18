import os
import json
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
            'liked_supplements': liked_supplements,
            'recommended_supplements': recommended_supplements,
            'debug_info': {
                'file_path': json_path,
            }
        }
        print(f"[DEBUG] context['liked_supplements']: {context['liked_supplements']}")  # 추가: context 전달 확인
        return render(request, 'Mypage/analysis.html', context)
    except Exception as e:
        messages.error(request, f'영양소 분석 결과를 불러오는 중 오류가 발생했습니다: {str(e)}')
        return redirect('mypage:mypage')

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
        # amount i date nie są już używane w modelu UserNutrientIntake

        # 영양소 기준치 데이터 로드
        json_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                nutrient_standards = json.load(f)
        except Exception as e:
            print(f"영양소 기준치 파일 로드 실패: {str(e)}")
            nutrient_standards = {}

        # 영양소가 존재하는지 확인하고, 없으면 생성
        nutrient, created = Nutrient.objects.get_or_create(
            name=nutrient_name,
            defaults={
                'unit': unit,
                'daily_recommended': nutrient_standards.get(nutrient_name, {}).get('recommended_amount', 100),
                'description': nutrient_standards.get(nutrient_name, {}).get('description', ''),
                'category': '기타'  # 기본 카테고리
            }
        )
        
        # 기존 영양소인 경우 권장량 업데이트
        if not created:
            nutrient.unit = unit
            nutrient.daily_recommended = nutrient_standards.get(nutrient_name, {}).get('recommended_amount', 100)
            nutrient.description = nutrient_standards.get(nutrient_name, {}).get('description', '')
            nutrient.save()
            print(f"기존 영양소 업데이트: {nutrient_name}, 권장량: {nutrient.daily_recommended}")
        else:
            print(f"새 영양소 생성: {nutrient_name}, 권장량: {nutrient.daily_recommended}")

        # 영양소 섭취 기록 생성 (amount, date 없이)
        intake = UserNutrientIntake.objects.create(
            user=request.user,
            nutrient=nutrient,
            status='수동입력'  # 또는 적절한 상태값
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
                'unit': nutrient.unit
            }
        })
    except Exception as e:
        print("영양소 추가 오류:", str(e))
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
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
            date__range=[start_date, end_date]
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
                'status': 'error',
                'message': '영양분석 결과가 없습니다.'
            }, status=404)

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
        # 사용자가 좋아요한 영양제 가져오기
        likes = Like.objects.filter(user=request.user).select_related('product')
        liked_products = []
        
        for like in likes:
            product = like.product
            liked_products.append({
                'id': product.id,
                'title': product.title,
                'description': product.description,
                'image_url': product.image_url,
                'price': product.price,
                'created_at': like.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'status': 'success',
            'data': liked_products
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def parse_number(value_str):
    """
    Parsuje liczbę z przecinkami w prawidłowy sposób:
    - "10,000" -> 10.0
    - "1,234" -> 1.234
    - "1.5" -> 1.5
    """
    try:
        # Jeśli to liczba bez przecinków, po prostu konwertuj
        if ',' not in value_str:
            return float(value_str)
        
        # Usuń spacje
        value_str = value_str.strip()
        
        # Sprawdź czy to format amerykański (np. 10,000)
        parts = value_str.split(',')
        if len(parts) == 2 and len(parts[1]) == 3:
            # Format amerykański: zamień przecinek na kropkę
            return float(parts[0])
        
        # W przeciwnym razie usuń wszystkie przecinki
        return float(value_str.replace(',', ''))
    except ValueError:
        print(f"Błąd parsowania liczby: {value_str}")
        return 0.0

def parse_ingredients(text):
    ingredients = {}
    
    # Mapowanie nazw angielskich na koreańskie
    name_mapping = {
        'biotin': '비오틴',
        'vitamin a': '비타민A',
        'vitamin b1': '비타민B1',
        'vitamin b2': '비타민B2',
        'vitamin b3': '비타민B3',
        'vitamin b6': '비타민B6',
        'vitamin b12': '비타민B12',
        'vitamin c': '비타민C',
        'vitamin d': '비타민D',
        'vitamin e': '비타민E',
        'vitamin k': '비타민K',
        'folate': '엽산',
        'calcium': '칼슘',
        'iron': '철',
        'magnesium': '마그네슘',
        'zinc': '아연',
        'selenium': '셀레늄',
        'copper': '구리',
        'manganese': '망간',
        'chromium': '크롬',
        'molybdenum': '몰리브덴',
        'iodine': '요오드',
        'potassium': '칼륨',
        'sodium': '나트륨',
        'phosphorus': '인',
        'omega-3': '오메가3',
        'omega-6': '오메가6',
        'dha': 'DHA',
        'epa': 'EPA',
        'coq10': '코엔자임Q10',
        'lutein': '루테인',
        'zeaxanthin': '제아잔틴',
        'probiotics': '프로바이오틱스',
        'collagen': '콜라겐',
        'creatine': '크레아틴',
        'glutamine': '글루타민',
        'bcaa': 'BCAA',
        'protein': '단백질',
        'fiber': '식이섬유',
        'carbohydrates': '탄수화물',
        'fat': '지방',
        'sugar': '당류',
        'cholesterol': '콜레스테롤',
        # 추가 영양소 매핑
        'thiamin': '비타민B1',
        'riboflavin': '비타민B2',
        'niacin': '비타민B3',
        'pantothenic acid': '판토텐산',
        'pyridoxine': '비타민B6',
        'cobalamin': '비타민B12',
        'ascorbic acid': '비타민C',
        'retinol': '비타민A',
        'calciferol': '비타민D',
        'tocopherol': '비타민E',
        'phylloquinone': '비타민K',
        'folic acid': '엽산',
        'folacin': '엽산'
    }
    
    # Lista głównych składników odżywczych do rozpoznania (angielskie i koreańskie)
    main_nutrients = list(name_mapping.keys()) + list(name_mapping.values())
    
    # Słowa do ignorowania (instrukcje dawkowania, itp.)
    ignore_words = [
        'take', 'tablet', 'capsule', 'pill', 'serving', 'daily', 'dose', 'dosage',
        'directions', 'use', 'recommended', 'suggested', 'intake', 'per', 'each',
        'with', 'food', 'meal', 'water', 'morning', 'evening', 'night', 'before',
        'after', 'during', 'breakfast', 'lunch', 'dinner', 'snack', 'other',
        'ingredients', 'gelatin', 'rice', 'flour', 'natural', 'life', 'naruraisimo'
    ]
    
    # Szukaj linii z wartościami odżywczymi - rozszerzone wzorce
    patterns = [
        # Format: Nazwa: Liczba Jednostka Procent
        re.compile(r'([A-Za-z\s]+):\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)\s+([\d,]+%)'),
        # Format: Nazwa: Liczba Jednostka
        re.compile(r'([A-Za-z\s]+):\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)'),
        # Format: Nazwa Liczba Jednostka Procent
        re.compile(r'([A-Za-z\s]+)\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)\s+([\d,]+%)'),
        # Format: Nazwa Liczba Jednostka
        re.compile(r'([A-Za-z\s]+)\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)'),
        # Format: Nazwa Liczba Jednostka (Procent)
        re.compile(r'([A-Za-z\s]+)\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)\s*\(([\d,]+%)\)'),
        # Format: Nazwa (Procent) Liczba Jednostka
        re.compile(r'([A-Za-z\s]+)\s*\(([\d,]+%)\)\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)'),
        # Format: Nazwa Liczba Jednostka bez spacji
        re.compile(r'([A-Za-z\s]+)([\d,]+\.?\d*)([a-zA-Z㎍mgREµ]+)'),
        # Format: Nazwa z myślnikiem
        re.compile(r'([A-Za-z\s-]+)\s+([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)'),
        # Format: Liczba Jednostka Nazwa
        re.compile(r'([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)\s+([A-Za-z\s]+)'),
        # Format: Nazwa - Liczba Jednostka
        re.compile(r'([A-Za-z\s]+)\s*-\s*([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)'),
    ]
    
    print(f"OCR Raw text: {text}")  # Debug: pokaż surowy tekst
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        print(f"Processing line: {line}")  # Debug: pokaż każdą linię
        
        # Sprawdź czy linia zawiera słowa do ignorowania
        line_lower = line.lower()
        if any(ignore_word in line_lower for ignore_word in ignore_words):
            print(f"Ignoring line (contains ignore words): {line}")
            continue
        
        for pattern in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                name = match.group(1).strip()
                raw_value = match.group(2)
                value = str(parse_number(raw_value))  # Użyj nowej funkcji parse_number
                unit = match.group(3)
                
                # Sprawdź czy nazwa zawiera główne składniki odżywcze
                is_main_nutrient = any(nutrient.lower() in name.lower() for nutrient in main_nutrients)
                
                # Sprawdź czy nazwa nie zawiera słów do ignorowania
                name_lower = name.lower()
                contains_ignore_words = any(ignore_word in name_lower for ignore_word in ignore_words)
                
                if is_main_nutrient and not contains_ignore_words:
                    # Mapuj angielską nazwę na koreańską
                    korean_name = name_mapping.get(name_lower, name)
                    
                    # Dodaj procent jeśli istnieje
                    if len(match.groups()) > 3 and match.group(4):
                        percentage = match.group(4)
                        ingredients[korean_name] = f"{value} {unit} ({percentage})"
                    else:
                        ingredients[korean_name] = f"{value} {unit}"
                    
                    print(f"Rozpoznano składnik: {name} -> {korean_name} = {ingredients[korean_name]}")  # Debug
                else:
                    print(f"Odrzucono: {name} (główny: {is_main_nutrient}, ignorowane: {contains_ignore_words})")
    
    # Jeśli nie znaleziono żadnych składników, spróbuj prostszego podejścia
    if not ingredients:
        print("Nie znaleziono składników standardowymi wzorcami, próbuję prostszego podejścia...")
        simple_patterns = [
            re.compile(r'([A-Za-z]+)\s*([\d,]+)'),
            re.compile(r'([A-Za-z]+)\s*([\d,]+\.?\d*)'),
            # 추가 패턴: 숫자와 단위만 있는 경우
            re.compile(r'([\d,]+\.?\d*)\s+([a-zA-Z㎍mgREµ]+)'),
        ]
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Sprawdź czy linia zawiera słowa do ignorowania
            line_lower = line.lower()
            if any(ignore_word in line_lower for ignore_word in ignore_words):
                continue
                
            for pattern in simple_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    name = match.group(1).strip()
                    value = match.group(2).replace(',', '')
                    
                    # 숫자만 있는 경우 건너뛰기
                    if name.isdigit():
                        continue
                    
                    # Sprawdź czy nazwa zawiera główne składniki odżywcze
                    is_main_nutrient = any(nutrient.lower() in name.lower() for nutrient in main_nutrients)
                    
                    # Sprawdź czy nazwa nie zawiera słów do ignorowania
                    name_lower = name.lower()
                    contains_ignore_words = any(ignore_word in name_lower for ignore_word in ignore_words)
                    
                    if is_main_nutrient and not contains_ignore_words:
                        # Mapuj angielską nazwę na koreańską
                        korean_name = name_mapping.get(name_lower, name)
                        ingredients[korean_name] = value
                        print(f"Proste rozpoznanie: {name} -> {korean_name} = {value}")
    
    # 마지막 시도: 전체 텍스트에서 영양소 키워드 검색
    if not ingredients:
        print("마지막 시도: 전체 텍스트에서 영양소 키워드 검색...")
        text_lower = text.lower()
        
        for nutrient in main_nutrients:
            nutrient_lower = nutrient.lower()
            if nutrient_lower in text_lower:
                # 해당 영양소가 포함된 라인 찾기
                for line in text.split('\n'):
                    line_lower = line.lower()
                    if nutrient_lower in line_lower:
                        # 숫자 추출
                        numbers = re.findall(r'[\d,]+\.?\d*', line)
                        if numbers:
                            value = numbers[0].replace(',', '')
                            # 단위 추출
                            units = re.findall(r'[a-zA-Z㎍mgREµ]+', line)
                            unit = units[0] if units else 'mg'
                            
                            korean_name = name_mapping.get(nutrient_lower, nutrient)
                            ingredients[korean_name] = f"{value} {unit}"
                            print(f"키워드 검색 결과: {nutrient} -> {korean_name} = {ingredients[korean_name]}")
                            break
    
    return ingredients

@login_required
@csrf_exempt
@require_POST
def ocr_extract(request):
    if 'image' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No image uploaded'}, status=400)
    image_file = request.FILES['image']
    try:
        image = Image.open(image_file)
        # Zmieniam na tylko angielski dla lepszej wydajności
        text = pytesseract.image_to_string(image, lang='eng')
        print(f"OCR Raw text: {text}")  # Debug: sprawdź co zwraca OCR
        
        # Sprawdź czy to jest żądanie debugowania
        debug_mode = request.POST.get('debug', 'false').lower() == 'true'
        if debug_mode:
            return JsonResponse({
                'status': 'debug', 
                'raw_text': text,
                'message': 'Raw OCR text for debugging'
            })
        
        ingredients = parse_ingredients(text)
        
        # 영양소 추출 결과에 대한 상세한 메시지
        if not ingredients:
            # 추출된 텍스트에서 숫자와 단위가 있는지 확인
            has_numbers = bool(re.search(r'[\d,]+\.?\d*', text))
            has_units = bool(re.search(r'[a-zA-Z㎍mgREµ]+', text))
            
            if has_numbers and has_units:
                ingredients = {
                    'Message': '영양소 정보를 찾을 수 없습니다. 이미지가 영양성분표를 포함하고 있는지 확인해주세요.',
                    'debug_info': {
                        'raw_text': text,
                        'has_numbers': has_numbers,
                        'has_units': has_units
                    }
                }
            else:
                ingredients = {
                    'Message': '이미지에서 텍스트를 인식할 수 없습니다. 더 선명한 이미지를 사용해주세요.',
                    'debug_info': {
                        'raw_text': text,
                        'has_numbers': has_numbers,
                        'has_units': has_units
                    }
                }
        else:
            # 성공적으로 추출된 경우에도 디버그 정보 추가
            ingredients['debug_info'] = {
                'raw_text': text,
                'extracted_count': len([k for k in ingredients.keys() if k != 'debug_info'])
            }
        
        # Sprawdź przydatność suplementu
        compatibility_result = check_supplement_compatibility(request.user, ingredients)
        
        return JsonResponse({
            'status': 'success', 
            'ingredients': ingredients,
            'compatibility': compatibility_result
        })
    except Exception as e:
        print(f"OCR 처리 중 오류 발생: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': f'이미지 처리 중 오류가 발생했습니다: {str(e)}'
        })

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

@require_POST
# @login_required
def product_click(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    user = User.objects.get(pk=1)
    try:
        product = Products.objects.get(pk=product_id)
        # UserLog 저장 (click)
        UserLog.objects.create(user=user, product=product, action='click')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def chatbot_view(request):
    try:
        return render(request, 'Chatbot/ChatNuti.html', {
            'user': request.user
        })
    except Exception as e:
        messages.error(request, f'챗봇 페이지를 불러오는 중 오류가 발생했습니다: {str(e)}')
        return redirect('mypage')

def import_kdris_data():
    csv_path = os.path.join(settings.STATICFILES_DIRS[0], 'csv', 'kdris.csv')
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                KDRIs.objects.update_or_create(
                    category=row['분류'],
                    age_range=row['연령'],
                    defaults={
                        'energy': float(row['에너지(kcal/일)']) if row['에너지(kcal/일)'] else 0,
                        'carbohydrates': float(row['탄수화물(g/일)']) if row['탄수화물(g/일)'] else 0,
                        'dietary_fiber': float(row['식이섬유(g/일)']) if row['식이섬유(g/일)'] else 0,
                        'protein': float(row['단백질(g/일)']) if row['단백질(g/일)'] else 0,
                        'vitamin_a': float(row['비타민 A(µg RAE/일)']) if row['비타민 A(µg RAE/일)'] else 0,
                        'vitamin_d': float(row['비타민 D(µg/일)']) if row['비타민 D(µg/일)'] else 0,
                        'vitamin_e': float(row['비타민 E(mg ɑ-TE/일)']) if row['비타민 E(mg ɑ-TE/일)'] else 0,
                        'vitamin_k': float(row['비타민 K(µg/일)']) if row['비타민 K(µg/일)'] else 0,
                        'vitamin_c': float(row['비타민 C(mg/일)']) if row['비타민 C(mg/일)'] else 0,
                        'thiamin': float(row['티아민(mg/일)']) if row['티아민(mg/일)'] else 0,
                        'riboflavin': float(row['리보플라빈(mg/일)']) if row['리보플라빈(mg/일)'] else 0,
                        'niacin': float(row['니아신(mg NE/일)']) if row['니아신(mg NE/일)'] else 0,
                        'vitamin_b6': float(row['비타민 B6(mg/일)']) if row['비타민 B6(mg/일)'] else 0,
                        'folate': float(row['엽산(µg DFE/일)']) if row['엽산(µg DFE/일)'] else 0,
                        'vitamin_b12': float(row['비타민B12(µg/일)']) if row['비타민B12(µg/일)'] else 0,
                        'calcium': float(row['칼슘(mg/일)']) if row['칼슘(mg/일)'] else 0,
                        'phosphorus': float(row['인(mg/일)']) if row['인(mg/일)'] else 0,
                        'sodium': float(row['나트륨(mg/일)']) if row['나트륨(mg/일)'] else 0,
                        'potassium': float(row['칼륨(mg/일)']) if row['칼륨(mg/일)'] else 0,
                        'magnesium': float(row['마그네슘(mg/일)']) if row['마그네슘(mg/일)'] else 0,
                        'iron': float(row['철(mg/일)']) if row['철(mg/일)'] else 0,
                        'zinc': float(row['아연(mg/일)']) if row['아연(mg/일)'] else 0,
                        'selenium': float(row['셀레늄(µg/일)']) if row['셀레늄(µg/일)'] else 0,
                    }
                )
        return True
    except Exception as e:
        print(f"KDRIs 데이터 임포트 실패: {str(e)}")
        return False

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
                'status': intake.status,
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
        status = data.get('status')

        # Sprawdź, czy wszystkie wymagane pola są obecne
        if not all([intake_id, nutrient_name, status]):
            return JsonResponse({
                'status': 'error',
                'message': '모든 필수 필드를 입력해주세요.'
            }, status=400)

        # Pobierz obiekt nutrient
        try:
            nutrient = Nutrient.objects.get(name=nutrient_name)
        except Nutrient.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '해당 영양소를 찾을 수 없습니다.'
            }, status=404)

        # Pobierz i zaktualizuj intake
        try:
            intake = UserNutrientIntake.objects.get(id=intake_id, user=request.user)
            intake.nutrient = nutrient
            intake.status = status
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
        intake_id = data.get('id')

        intake = UserNutrientIntake.objects.get(id=intake_id, user=request.user)
        intake.delete()

        # 영양분석 실행
        try:
            analyze_nutrients(request)
        except Exception as e:
            print(f"영양분석 실행 중 오류 발생: {str(e)}")

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

def check_supplement_compatibility(user, ingredients):
    """
    Sprawdza przydatność suplementu na podstawie składników i profilu użytkownika
    """
    compatibility_result = {
        'is_suitable': True,
        'score': 0,
        'warnings': [],
        'benefits': [],
        'recommendations': []
    }
    
    try:
        # Pobierz najnowszy profil użytkownika
        latest_survey = SurveyResult.objects.filter(user=user).order_by('-created_at').first()
        if not latest_survey:
            compatibility_result['warnings'].append('사용자 프로필 정보가 없습니다. 설문을 먼저 완료해주세요.')
            compatibility_result['is_suitable'] = False
            return compatibility_result
        
        answers = latest_survey.answers
        score = 0
        max_score = 0
        
        # Analiza składników
        for ingredient_name, ingredient_value in ingredients.items():
            ingredient_lower = ingredient_name.lower()
            
            # Biotin - dla zdrowia włosów, skóry i paznokci
            if 'biotin' in ingredient_lower or '비오틴' in ingredient_lower:
                max_score += 8
                score += 8
                compatibility_result['benefits'].append('비오틴은 모발, 피부, 손톱 건강에 도움이 됩니다.')
            
            # Witamina D - dla osób spędzających dużo czasu w pomieszczeniach
            elif 'vitamin d' in ingredient_lower or '비타민 d' in ingredient_lower:
                max_score += 10
                if answers.get('indoor_daytime') == '예':
                    score += 10
                    compatibility_result['benefits'].append('비타민 D는 실내 생활이 많은 사용자에게 적합합니다.')
                else:
                    compatibility_result['warnings'].append('비타민 D는 햇빛 노출이 충분한 경우 과다 섭취될 수 있습니다.')
            
            # Witamina B - dla osób z objawami zmęczenia
            elif any(b_vitamin in ingredient_lower for b_vitamin in ['vitamin b', '비타민 b', 'thiamin', 'riboflavin', 'niacin']):
                max_score += 8
                if answers.get('fatigue') == '예' or answers.get('still_tired') == '예':
                    score += 8
                    compatibility_result['benefits'].append('비타민 B는 피로감이 있는 사용자에게 도움이 됩니다.')
                else:
                    score += 4
                    compatibility_result['recommendations'].append('비타민 B는 에너지 대사에 도움이 되지만, 필요에 따라 섭취하세요.')
            
            # Witamina C - dla palaczy
            elif 'vitamin c' in ingredient_lower or '비타민 c' in ingredient_lower:
                max_score += 8
                if answers.get('smoking') == '예':
                    score += 8
                    compatibility_result['benefits'].append('비타민 C는 흡연자에게 특히 유용합니다.')
                else:
                    score += 6
                    compatibility_result['benefits'].append('비타민 C는 면역력 강화에 도움이 됩니다.')
            
            # Omega-3 - dla osób prowadzących siedzący tryb życia
            elif any(omega in ingredient_lower for omega in ['omega-3', 'omega 3', 'dha', 'epa', '오메가']):
                max_score += 10
                if answers.get('sitting_work') == '예' and answers.get('exercise_frequency') in ['전혀 안함', '1-2회']:
                    score += 10
                    compatibility_result['benefits'].append('오메가-3는 장시간 앉아서 일하는 사용자에게 적합합니다.')
                else:
                    score += 6
                    compatibility_result['benefits'].append('오메가-3는 전반적인 심장 건강에 도움이 됩니다.')
            
            # Magnez - dla osób z problemami ze snem
            elif 'magnesium' in ingredient_lower or '마그네슘' in ingredient_lower:
                max_score += 8
                if answers.get('sleep_well') == '아니오' or (answers.get('sleep_hours') and float(answers.get('sleep_hours', 0)) < 7):
                    score += 8
                    compatibility_result['benefits'].append('마그네슘은 수면의 질을 개선하는 데 도움이 됩니다.')
                else:
                    score += 5
                    compatibility_result['benefits'].append('마그네슘은 근육 이완과 신경 기능에 도움이 됩니다.')
            
            # Żelazo - dla kobiet
            elif 'iron' in ingredient_lower or '철' in ingredient_lower:
                max_score += 8
                if answers.get('gender') == '여성':
                    score += 8
                    compatibility_result['benefits'].append('철분은 여성에게 특히 중요한 영양소입니다.')
                else:
                    score += 4
                    compatibility_result['warnings'].append('남성의 경우 철분 과다 섭취에 주의하세요.')
            
            # Wapń - dla osób z problemami z kośćmi
            elif 'calcium' in ingredient_lower or '칼슘' in ingredient_lower:
                max_score += 6
                if answers.get('indoor_daytime') == '예':  # Brak witaminy D może wpływać na wchłanianie wapnia
                    score += 4
                    compatibility_result['warnings'].append('칼슘은 비타민 D와 함께 섭취하는 것이 좋습니다.')
                else:
                    score += 6
                    compatibility_result['benefits'].append('칼슘은 뼈 건강에 중요합니다.')
            
            # Inne składniki
            else:
                max_score += 3
                score += 2
                compatibility_result['benefits'].append(f'{ingredient_name}은 일반적으로 유용한 영양소입니다.')
        
        # Sprawdź interakcje i przeciwwskazania
        if answers.get('drinking') == '예':
            compatibility_result['warnings'].append('음주 시 일부 영양제와의 상호작용에 주의하세요.')
        
        if answers.get('smoking') == '예':
            compatibility_result['warnings'].append('흡연은 일부 비타민의 흡수를 감소시킬 수 있습니다.')
        
        # Oblicz końcowy wynik
        if max_score > 0:
            compatibility_result['score'] = int((score / max_score) * 100)
        
        # Określ ogólną przydatność
        if compatibility_result['score'] >= 70:
            compatibility_result['is_suitable'] = True
        elif compatibility_result['score'] >= 40:
            compatibility_result['is_suitable'] = True
            compatibility_result['recommendations'].append('이 영양제는 부분적으로 적합합니다. 개인적인 필요에 따라 섭취하세요.')
        else:
            compatibility_result['is_suitable'] = False
            compatibility_result['warnings'].append('이 영양제는 현재 프로필에 적합하지 않을 수 있습니다.')
        
        return compatibility_result
        
    except Exception as e:
        print(f"영양제 호환성 검사 오류: {str(e)}")
        compatibility_result['is_suitable'] = False
        compatibility_result['warnings'].append('호환성 검사 중 오류가 발생했습니다.')
        return compatibility_result

@login_required
@require_POST
def save_ocr_ingredients(request):
    """
    OCR로 rozpoznane składniki를 데이터베이스에 저장
    """
    try:
        data = json.loads(request.body)
        ingredients = data.get('ingredients', {})
        date = data.get('date', timezone.now().date())
        
        saved_ingredients = []
        
        for ingredient_name, ingredient_value in ingredients.items():
            # Skip if it's a message or debug info
            if ingredient_name == 'Message' or ingredient_name == 'debug_info':
                continue
                
            # Parse ingredient value to extract amount and unit
            amount = 0
            unit = 'mg'  # default unit
            
            if isinstance(ingredient_value, str):
                # Try to extract amount and unit from string like "10000 mcg" or "100 mg"
                import re
                match = re.match(r'([\d,]+\.?\d*)\s*([a-zA-Z㎍mgREµ]+)', ingredient_value)
                if match:
                    amount = parse_number(match.group(1))
                    unit = match.group(2)
                else:
                    # Try to extract just the number
                    num_match = re.search(r'([\d,]+\.?\d*)', ingredient_value)
                    if num_match:
                        amount = parse_number(num_match.group(1))
            elif isinstance(ingredient_value, (int, float)):
                amount = float(ingredient_value)
            
            # Skip if amount is 0 or invalid
            if amount <= 0:
                print(f"유효하지 않은 양 건너뛰기: {ingredient_name} = {amount}")
                continue
            
            # Load nutrient standards
            json_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    nutrient_standards = json.load(f)
            except Exception as e:
                print(f"영양소 기준치 파일 로드 실패: {str(e)}")
                nutrient_standards = {}
            
            # Create or get nutrient
            nutrient, created = Nutrient.objects.get_or_create(
                name=ingredient_name,
                defaults={
                    'unit': unit,
                    'daily_recommended': nutrient_standards.get(ingredient_name, {}).get('recommended_amount', 100),
                    'description': nutrient_standards.get(ingredient_name, {}).get('description', ''),
                    'category': '기타'
                }
            )
            
            # 기존 영양소인 경우 권장량 업데이트
            if not created:
                nutrient.unit = unit
                nutrient.daily_recommended = nutrient_standards.get(ingredient_name, {}).get('recommended_amount', 100)
                nutrient.description = nutrient_standards.get(ingredient_name, {}).get('description', '')
                nutrient.save()
                print(f"기존 영양소 업데이트: {ingredient_name}, 권장량: {nutrient.daily_recommended}")
            else:
                print(f"새 영양소 생성: {ingredient_name}, 권장량: {nutrient.daily_recommended}")
            
            # Create nutrient intake record
            intake = UserNutrientIntake.objects.create(
                user=request.user,
                nutrient=nutrient,
                amount=amount,
                date=date
            )
            
            saved_ingredients.append({
                'id': intake.id,
                'nutrient_name': nutrient.name,
                'amount': amount,
                'unit': nutrient.unit
            })
        
        # Run nutrient analysis
        try:
            analyze_nutrients(request)
        except Exception as e:
            print(f"영양분석 실행 중 오류 발생: {str(e)}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'{len(saved_ingredients)}개의 영양소가 저장되었습니다.',
            'saved_ingredients': saved_ingredients
        })
        
    except Exception as e:
        print(f"OCR 성분 저장 오류: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def like_list(request):
    User = get_user_model()
    # user = User.objects.get(pk=1)
    user = request.user
    like_list = Like.objects.filter(user=user).select_related('product')
    for like in like_list:
        setattr(like.product, 'is_liked', True)
    return render(request, 'Mypage/like.html', {'user': user, 'like_list': like_list})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_delete(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    # user = User.objects.get(pk=1)
    user = request.user
    try:
        product = Products.objects.get(pk=product_id)
        like = Like.objects.get(user=user, product_id=product_id)
        like.delete()
        UserLog.objects.create(user=user, product=product, action='unlike')
        return JsonResponse({'success': True})
    except Like.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    except Exception as e:
        print("LIKE_API ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_add(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    # user = User.objects.get(pk=1)
    user = request.user
    try:
        product = Products.objects.get(pk=product_id)
        Like.objects.get_or_create(user=user, product_id=product_id)
        UserLog.objects.create(user=user, product=product, action='like')
        return JsonResponse({'success': True})
    except Exception as e:
        print("LIKE_API ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

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
    try:
        return render(request, 'Chatbot/ChatNuti.html', {
            'user': request.user
        })
    except Exception as e:
        messages.error(request, f'챗봇 페이지를 불러오는 중 오류가 발생했습니다: {str(e)}')
        return redirect('mypage')

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
            data = json.loads(request.body)
            product_id = data.get('product_id')
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
            print("LIKE_API ERROR:", e)
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
