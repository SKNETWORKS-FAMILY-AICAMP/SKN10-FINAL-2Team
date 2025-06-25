import os
import json
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
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
from Chatbot.models import NutritionDailyRec
import markdown

@login_required
def mypage_view(request):
    # 사용자의 최근 설문 결과 가져오기
    latest_survey = SurveyResult.objects.filter(user=request.user).order_by('-created_at').first()
    
    if latest_survey:
        # 추천 영양제 가져오기 (보고서 기반)
        recommended_supplements = get_recommended_supplements_from_report(latest_survey)
        
        # 건강 리포트 생성 또는 업데이트
        health_report, created = UserHealthReport.objects.get_or_create(
            user=request.user,
            survey_result=latest_survey,
            defaults={
                'health_score': 0,  # 건강점수 제거
                'recommendations': generate_recommendations(latest_survey, 0)
            }
        )
        
        if not created:
            health_report.health_score = 0  # 건강점수 제거
            health_report.recommendations = generate_recommendations(latest_survey, 0)
            health_report.save()
        
        # 설문 이력 가져오기
        survey_history = UserHealthReport.objects.filter(user=request.user).order_by('-created_at')
        
        context = {
            'latest_survey': latest_survey,
            'recommended_supplements': recommended_supplements,
            'recommendations': health_report.recommendations.split('\n'),
            'survey_history': survey_history
        }
    else:
        context = {
            'latest_survey': None,
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
            
            # Nowa struktura: kategorie z pytaniami
            # Konwertuj strukturę na płaską listę pytań dla kompatybilności z szablonem
            questions = []
            question_id = 1
            
            for category, category_questions in survey_data.items():
                for question_text, default_value in category_questions.items():
                    question = {
                        'id': str(question_id),
                        'category': category,
                        'text': question_text,
                        'name': f"question_{question_id}",
                        'default_value': default_value
                    }
                    
                    # Określ typ pytania na podstawie wartości domyślnej
                    if isinstance(default_value, list):
                        question['type'] = 'select'
                        question['options'] = default_value
                    elif isinstance(default_value, dict):
                        question['type'] = 'checkbox'
                        question['options'] = list(default_value.keys())
                    elif default_value in ['예', '아니오']:
                        question['type'] = 'select'
                        question['options'] = ['예', '아니오']
                    else:
                        question['type'] = 'text'
                        question['default_value'] = default_value
                    
                    questions.append(question)
                    question_id += 1
            
            return render(request, 'Mypage/survey.html', {
                'survey_questions': {'questions': questions},
                'survey_categories': survey_data
            })
    except Exception as e:
        print(f"Error loading survey questions: {str(e)}")
        return render(request, 'Mypage/survey.html', {
            'survey_questions': {'questions': []},
            'survey_categories': {},
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
                if key in responses:
                    if isinstance(responses[key], list):
                        responses[key].append(value)
                    else:
                        responses[key] = [responses[key], value]
                else:
                    responses[key] = value
        for key, value in responses.items():
            if isinstance(value, list):
                responses[key] = ', '.join(value)
        print(f"Survey responses: {responses}")

        # 질문 번호 → 의미있는 키로 매핑
        question_map = {
            'question_1': 'gender',
            'question_2': 'age_range',
            'question_3': 'sitting_work',
            'question_4': 'indoor_daytime',
            'question_5': 'exercise',
            'question_6': 'smoking',
            'question_7': 'drinking',
            'question_8': 'fatigue',
            'question_9': 'sleep_well',
            'question_10': 'still_tired',
            'question_11': 'symptom_1',
            'question_12': 'symptom_2',
            'question_13': 'frequent_cold',
            'question_14': 'dry_eyes',
            'question_15': 'skin_care',
            'question_16': 'cognitive_improvement',
            'question_17': 'weight_loss',
            'question_18': 'allergies',
            'question_19': 'chronic_medication',
            'question_20': 'antibiotics',
            'question_21': 'surgery_plan',
            'question_22': 'etc',
        }
        mapped_answers = {}
        for k, v in responses.items():
            mapped_answers[question_map.get(k, k)] = v
        print(f"Mapped answers: {mapped_answers}")

        # 설문 응답 저장
        survey_response = SurveyResponse.objects.create(
            user=request.user,
            responses=responses,
            answers=mapped_answers
        )
        # 설문 결과 분석 및 저장
        result = analyze_survey_responses(survey_response)
        SurveyResult.objects.create(
            user=request.user,
            answers=mapped_answers,
            result=result
        )
        return redirect('mypage:survey_result')
    except Exception as e:
        print(f"Error submitting survey: {str(e)}")
        messages.error(request, f'설문 제출 중 오류가 발생했습니다: {str(e)}')
        return redirect('mypage:survey')

@login_required
def survey_result(request):
    try:
        # 가장 최근 설문 결과 가져오기
        survey_result = SurveyResult.objects.filter(user=request.user).latest('created_at')
        
        # Debug: sprawdź dane
        print(f"DEBUG: Survey result answers: {survey_result.answers}")
        
        # 추천 영양제 가져오기
        recommended_supplements = get_recommended_supplements(survey_result)
        
        # 건강 리포트 생성 또는 업데이트
        health_report, created = UserHealthReport.objects.get_or_create(
            user=request.user,
            survey_result=survey_result,
            defaults={
                'health_score': 0,  # 건강점수 제거
                'recommendations': generate_recommendations(survey_result, 0)
            }
        )
        
        if not created:
            health_report.health_score = 0  # 건강점수 제거
            health_report.recommendations = generate_recommendations(survey_result, 0)
            health_report.save()
        
        # Generuj osobne sekcje raportu
        health_summary = generate_health_summary_section(request.user, survey_result)
        recommended_supplements_section = generate_recommended_supplements_section(survey_result)
        warnings_section = generate_warnings_section(survey_result)
        considerations_section = generate_considerations_section(survey_result)
        
        # Debug: sprawdź wygenerowane sekcje
        print(f"DEBUG: Health summary: {health_summary[:100]}...")
        print(f"DEBUG: Recommended supplements section: {recommended_supplements_section[:100]}...")
        print(f"DEBUG: Warnings section: {warnings_section[:100]}...")
        print(f"DEBUG: Considerations section: {considerations_section[:100]}...")
        
        # Debug: sprawdź długość sekcji
        print(f"DEBUG: Health summary length: {len(health_summary)}")
        print(f"DEBUG: Recommended supplements section length: {len(recommended_supplements_section)}")
        print(f"DEBUG: Warnings section length: {len(warnings_section)}")
        print(f"DEBUG: Considerations section length: {len(considerations_section)}")
        
        # Renderuj markdown do HTML
        health_summary_html = markdown.markdown(health_summary, extensions=['extra'])
        recommended_supplements_html = markdown.markdown(recommended_supplements_section, extensions=['extra'])
        warnings_html = markdown.markdown(warnings_section, extensions=['extra'])
        considerations_html = markdown.markdown(considerations_section, extensions=['extra'])
        
        # Debug: sprawdź HTML po renderowaniu
        print(f"DEBUG: Recommended supplements HTML length: {len(recommended_supplements_html)}")
        print(f"DEBUG: Recommended supplements HTML: {recommended_supplements_html[:200]}...")
        
        context = {
            'survey_result': survey_result,
            'recommended_supplements': recommended_supplements,
            'recommendations': health_report.recommendations.split('\n'),
            'health_summary': health_summary_html,
            'recommended_supplements_section': recommended_supplements_html,
            'warnings_section': warnings_html,
            'considerations_section': considerations_html
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
        amount = float(data.get('amount', 0))
        unit = data.get('unit', 'mg')
        
        if not nutrient_name:
            return JsonResponse({
                'status': 'error',
                'message': '영양소 이름이 필요합니다.'
            }, status=400)
        
        # 기존 영양소만 사용 - 새로 생성하지 않음
        try:
            nutrient = Nutrient.objects.get(name=nutrient_name)
            print(f"기존 영양소 사용: {nutrient_name}")
        except Nutrient.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'영양소 "{nutrient_name}"는 관리되지 않는 영양소입니다. 관리자에게 문의하세요.'
            }, status=400)

        # 영양소 섭취 기록 생성
        intake = UserNutrientIntake.objects.create(
            user=request.user,
            nutrient=nutrient,
            amount=amount,
            unit=unit
        )

        # 영양분석 실행
        try:
            analyze_nutrients(request)
        except Exception as e:            print(f"영양분석 실행 중 오류 발생: {str(e)}")
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

        # 사용자 정보 가져오기 (성별, 연령)
        user = request.user
        gender = getattr(user, 'gender', '남자')  # 기본값 설정
        age = getattr(user, 'age', 30)  # 기본값 설정
        
        # 연령대 계산
        if age < 20:
            age_range = "10대"
        elif age < 30:
            age_range = "20대"
        elif age < 40:
            age_range = "30대"
        elif age < 50:
            age_range = "40대"
        elif age < 60:
            age_range = "50대"
        else:
            age_range = "60대 이상"

        # 영양소별 평균 섭취량 계산
        nutrient_averages = {}
        for intake in intakes:
            nutrient_name = intake.nutrient.name
            if nutrient_name not in nutrient_averages:
                # NutritionDailyRec에서 권장량 가져오기
                daily_rec = NutritionDailyRec.objects.filter(
                    sex=gender,
                    age_range=age_range,
                    nutrient=nutrient_name
                ).first()
                
                if daily_rec:
                    recommended = daily_rec.daily
                    print(f"DB에서 권장량 가져옴: {nutrient_name} = {recommended}")
                else:
                    # DB에 없는 경우 기본값 사용
                    recommended = 100
                    print(f"DB에 권장량 없음, 기본값 사용: {nutrient_name} = {recommended}")
                
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
                        
                        # 기존 영양소만 사용 - 새로 생성하지 않음
                        try:
                            nutrient = Nutrient.objects.get(name=nutrient_name)
                        except Nutrient.DoesNotExist:
                            print(f"관리되지 않는 영양소 건너뛰기: {nutrient_name}")
                            continue
                        
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
                        
                        # 기존 영양소만 사용 - 새로 생성하지 않음
                        try:
                            nutrient = Nutrient.objects.get(name=nutrient_name)
                        except Nutrient.DoesNotExist:
                            print(f"관리되지 않는 영양소 건너뛰기: {nutrient_name}")
                            continue
                        
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

@login_required
def product_click(request):
    """Produkt kliknięcie - logowanie aktywności użytkownika"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            # Log aktywności użytkownika
            UserLog.objects.create(
                user=request.user,
                action='product_click',
                details=f'Product ID: {product_id}'
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Aktywność została zarejestrowana'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Nieprawidłowe żądanie'
    }, status=400)

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

@login_required
def like_api(request):
    """API do zarządzania polubieniami"""
    if request.method == 'GET':
        # Pobierz polubione produkty
        likes = Like.objects.filter(user=request.user).select_related('product')
        liked_products = [{
            'id': like.product.id,
            'title': like.product.title,
            'brand': like.product.brand
        } for like in likes]
        
        return JsonResponse({
            'status': 'success',
            'liked_products': liked_products
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Nieprawidłowe żądanie'
    }, status=400)

@login_required
def product_purchase(request):
    """Zakup produktu - logowanie aktywności"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            # Log zakupu
            UserLog.objects.create(
                user=request.user,
                action='product_purchase',
                details=f'Product ID: {product_id}'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Zakup został zarejestrowany'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Nieprawidłowe żądanie'
    }, status=400)

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
                
                # 기존 영양소만 사용 - 새로 생성하지 않음
                try:
                    nutrient = Nutrient.objects.get(name=nutrient_name)
                except Nutrient.DoesNotExist:
                    print(f"관리되지 않는 영양소 건너뛰기: {nutrient_name}")
                    continue
                
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

@login_required
def get_available_nutrients(request):
    """사용자가 사용할 수 있는 영양소 목록을 반환"""
    try:
        nutrients = Nutrient.objects.all().order_by('name')
        nutrient_list = [{
            'id': nutrient.id,
            'name': nutrient.name,
            'unit': nutrient.unit or 'mg',
            'description': nutrient.description or '',
            'daily_recommended': nutrient.daily_recommended or 0
        } for nutrient in nutrients]
        
        return JsonResponse({
            'status': 'success',
            'nutrients': nutrient_list
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def generate_health_report_markdown(user, survey_result):
    """
    Generuje raport zdrowotny w formacie markdown na podstawie wyników ankiety
    """
    try:
        # Pobierz dane z ankiety
        answers = survey_result.answers
        user_name = user.name or user.email.split('@')[0]
        
        # Analizuj odpowiedzi z ankiety - używaj rzeczywistych odpowiedzi
        gender = answers.get('gender', '')
        age_group = answers.get('age_range', '')
        
        # Analizuj style życia na podstawie rzeczywistych odpowiedzi
        lifestyle_summary = []
        if answers.get('sitting_work') == '예':  # 주로 앉아서 하는 일
            lifestyle_summary.append("주로 앉아서 일하는 생활")
        if answers.get('indoor_daytime') == '예':  # 실내에서 주로 생활
            lifestyle_summary.append("실내에서 주로 생활")
        if answers.get('exercise') == '아니오':  # 규칙적인 운동
            lifestyle_summary.append("규칙적인 운동 부족")
        if answers.get('smoking') == '예':  # 흡연
            lifestyle_summary.append("흡연")
        if answers.get('drinking') == '예':  # 과도한 음주
            lifestyle_summary.append("과도한 음주")
        if answers.get('fatigue') == '예':  # 만성 피로
            lifestyle_summary.append("만성 피로")
        if answers.get('sleep_well') == '아니오':  # 수면의 질
            lifestyle_summary.append("수면의 질 저하")
        if answers.get('still_tired') == '예':  # 수면 후 피로
            lifestyle_summary.append("수면 후에도 피로함")
        
        # Analizuj stan zdrowia na podstawie rzeczywistych odpowiedzi
        health_status = []
        if answers.get('stress') == '예':  # 스트레스
            health_status.append("스트레스 과다")
        if answers.get('digestive_issues') == '예':  # 소화기 문제
            health_status.append("소화기 문제")
        if answers.get('frequent_cold') == '예':  # 면역력 저하
            health_status.append("면역력 저하")
        if answers.get('dry_eyes') == '예':  # 눈 건강 문제
            health_status.append("눈 건강 문제")
        
        # Analizuj cele zdrowotne na podstawie rzeczywistych odpowiedzi
        health_goals = []
        if answers.get('skin_care') == '예':  # 피부 건강
            health_goals.append("피부 건강 개선")
        if answers.get('cognitive_improvement') == '예':  # 인지력 개선
            health_goals.append("인지력 및 기억력 개선")
        if answers.get('weight_loss') == '예':  # 체중 감량
            health_goals.append("체중 감량")
        
        # Analizuj istniejące choroby i leki na podstawie rzeczywistych odpowiedzi
        medical_conditions = []
        if answers.get('allergies'):  # 알레르기
            medical_conditions.append("식품 알레르기")
        if answers.get('chronic_medication'):  # 만성질환 약물
            medical_conditions.append("만성질환 약물 복용")
        if answers.get('antibiotics') == '예':  # 항생제 복용
            medical_conditions.append("최근 항생제 복용")
        if answers.get('surgery_plan') == '예':  # 수술 계획
            medical_conditions.append("수술 계획/경험")
        
        # Generuj spersonalizowane rekomendacje na podstawie rzeczywistych odpowiedzi
        recommended_supplements = []
        
        # 비타민 D - jeśli 실내 생활
        if answers.get('indoor_daytime'):
            recommended_supplements.append({
                'name': '비타민 D',
                'reason': '실내 생활이 많고 햇빛 노출이 부족합니다.',
                'benefits': '면역력 강화와 뼈 건강에 도움을 줍니다.'
            })
        
        # 오메가-3 추천 조건
        if survey_result.answers.get('sitting_work') and survey_result.answers.get('exercise_frequency') in ['전혀 안함', '1-2회']:
            recommended_supplements.append({
                'name': '오메가-3',
                'reason': '장시간 앉아서 일하고 운동이 부족합니다.',
                'benefits': '심장 건강과 염증 감소에 도움을 줍니다.'
            })
        
        # 비타민 B 복합체 추천 조건
        if survey_result.answers.get('fatigue') or survey_result.answers.get('still_tired'):
            recommended_supplements.append({
                'name': '비타민 B 복합체',
                'reason': '피로감이 심하고 수면의 질이 좋지 않습니다.',
                'benefits': '에너지 대사와 신경계 건강에 도움을 줍니다.'
            })
        
        return recommended_supplements
    except Exception as e:
        print(f"Error generating health report: {str(e)}")
        return f"보고서 생성 중 오류가 발생했습니다: {str(e)}"

@login_required
def get_available_nutrients(request):
    try:
        nutrients = Nutrient.objects.all().values('id', 'name', 'unit', 'daily_recommended')
        return JsonResponse({'nutrients': list(nutrients)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generate_health_summary_section(user, survey_result):
    """
    Generuje sekcję 1: 건강 상태 요약
    """
    try:
        # Mapowanie odpowiedzi z ankiety
        answers = survey_result.answers
        
        # Sprawdź czy answers to string JSON
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        user_name = user.name or user.email.split('@')[0]
        
        print(f"DEBUG: All answers in generate_health_summary_section: {answers}")
        
        # Analizuj odpowiedzi z ankiety
        gender = answers.get('gender', '')  # 성별
        age_group = answers.get('age_range', '')  # 연령대
        
        print(f"DEBUG: Gender: {gender}, Age group: {age_group}")
        
        # Analizuj style życia
        lifestyle_summary = []
        sitting_work = answers.get('sitting_work', '')  # 앉아서 일하는지
        if sitting_work == '예':
            lifestyle_summary.append("주로 앉아서 일하는 생활")
        
        indoor_daytime = answers.get('indoor_daytime', '')  # 실내 생활
        if indoor_daytime == '예':
            lifestyle_summary.append("실내에서 주로 생활")
        
        exercise = answers.get('exercise', '')  # 운동 여부
        if exercise == '아니오':
            lifestyle_summary.append("규칙적인 운동 부족")
        
        smoking = answers.get('smoking', '')  # 흡연
        if smoking == '예':
            lifestyle_summary.append("흡연")
        
        drinking = answers.get('drinking', '')  # 음주
        if drinking == '예':
            lifestyle_summary.append("과도한 음주")
        
        fatigue = answers.get('fatigue', '')  # 피로
        if fatigue == '예':
            lifestyle_summary.append("만성 피로")
        
        sleep_well = answers.get('sleep_well', '')  # 수면의 질
        if sleep_well == '아니오':
            lifestyle_summary.append("수면의 질 저하")
        
        still_tired = answers.get('still_tired', '')  # 수면 후 피로
        if still_tired == '예':
            lifestyle_summary.append("수면 후에도 피로함")
        
        print(f"DEBUG: Lifestyle summary: {lifestyle_summary}")
        
        # Analizuj stan zdrowia
        health_status = []
        symptom_1 = answers.get('symptom_1', '')  # 증상 1
        if symptom_1 == '예':
            health_status.append("건강 문제 있음")
        
        symptom_2 = answers.get('symptom_2', '')  # 증상 2
        if symptom_2 == '예':
            health_status.append("소화기 문제")
        
        frequent_cold = answers.get('frequent_cold', '')  # 면역력 저하
        if frequent_cold == '예':
            health_status.append("면역력 저하")
        
        dry_eyes = answers.get('dry_eyes', '')  # 눈 건강 문제
        if dry_eyes == '예':
            health_status.append("눈 건강 문제")
        
        print(f"DEBUG: Health status: {health_status}")
        
        # Analizuj cele zdrowotne
        health_goals = []
        skin_care = answers.get('skin_care', '')  # 피부 관리
        if skin_care == '예':
            health_goals.append("피부 건강 개선")
        
        cognitive_improvement = answers.get('cognitive_improvement', '')  # 인지력 개선
        if cognitive_improvement == '예':
            health_goals.append("인지력 및 기억력 개선")
        
        weight_loss = answers.get('weight_loss', '')  # 체중 감량
        if weight_loss == '예':
            health_goals.append("체중 감량")
        
        if not health_goals:
            health_goals = ["건강 유지 및 개선"]
        
        print(f"DEBUG: Health goals: {health_goals}")
        
        # Analizuj istniejące choroby i leki
        medical_conditions = []
        allergies = answers.get('allergies', '')  # 알레르기
        if allergies == '예':
            medical_conditions.append("식품 알레르기")
        
        chronic_medication = answers.get('chronic_medication', '')  # 만성질환 약물
        if chronic_medication == '예':
            medical_conditions.append("만성질환 약물 복용")
        
        antibiotics = answers.get('antibiotics', '')  # 항생제
        if antibiotics == '예':
            medical_conditions.append("최근 항생제 복용")
        
        surgery_plan = answers.get('surgery_plan', '')  # 수술 계획
        if surgery_plan == '예':
            medical_conditions.append("수술 계획/경험")
        
        print(f"DEBUG: Medical conditions: {medical_conditions}")
        
        # Generuj sekcję
        summary = f"""안녕하세요, {user_name}님! 설문조사를 통해 파악된 건강 상태와 생활 습관을 바탕으로, 꼭 필요한 영양제를 추천해 드립니다.

#### **기본 정보**: {gender}, {age_group}

#### **생활 습관**: {', '.join(lifestyle_summary) if lifestyle_summary else '규칙적인 생활 습관을 유지하고 계십니다'}

#### **현재 건강 상태**: {', '.join(health_status) if health_status else '전반적으로 양호한 건강 상태입니다'}

#### **건강 목표**: {', '.join(health_goals)}

#### **기존 질환 및 약 복용**: {', '.join(medical_conditions) if medical_conditions else '특별한 질환이나 복용 중인 약물이 없습니다'}"""
        
        print(f"DEBUG: Generated summary: {summary}")
        return summary
        
    except Exception as e:
        print(f"Error generating health summary: {str(e)}")
        return f"건강 상태 요약 생성 중 오류가 발생했습니다: {str(e)}"

def is_nutrient_in_db(nutrient_name):
    from Mypage.models import Nutrient
    if not hasattr(is_nutrient_in_db, '_cache'):
        is_nutrient_in_db._cache = set(Nutrient.objects.values_list('name', flat=True))
    return nutrient_name in is_nutrient_in_db._cache


def generate_recommended_supplements_section(survey_result):
    """
    Generuje sekcję 2: 추천하는 핵심 영양제
    """
    try:
        # Mapowanie odpowiedzi z ankiety
        answers = survey_result.answers
        
        # Sprawdź czy answers to string JSON
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        recommended_supplements = []

        # 비타민 D - 실내 생활 여부 확인
        if is_nutrient_in_db('비타민 D') and answers.get('indoor_daytime') == '예':  # 실내에서 주로 생활
            recommended_supplements.append({
                'name': '비타민 D',
                'reason': '실내에서 주로 생활하시므로 햇빛 노출이 부족할 수 있어 비타민 D 보충이 필요합니다. 뼈 건강과 면역력 강화에 도움이 됩니다.'
            })
        
        # 마그네슘 - 수면 문제 확인
        if is_nutrient_in_db('마그네슘') and (answers.get('sleep_well') == '아니오' or answers.get('still_tired') == '예'):  # 수면의 질
            recommended_supplements.append({
                'name': '마그네슘',
                'reason': '수면의 질 저하와 피로 증상 개선을 위해 추천합니다. 근육 이완과 신경 안정에 도움이 됩니다.'
            })
        
        # 비타민 B 복합체 - 피로 확인
        b_complex = ['비타민 B1', '비타민 B2', '비타민 B6', '비타민 B12', '나이아신', '엽산', '판토텐산', '비오틴']
        if any(is_nutrient_in_db(b) for b in b_complex) and answers.get('fatigue') == '예':  # 피로
            recommended_supplements.append({
                'name': '비타민 B 복합체',
                'reason': '에너지 대사와 피로 회복을 위해 추천합니다. 특히 스트레스 상황에서 소모되기 쉬운 영양소입니다.'
            })
        
        # 루테인 - 눈 건강 문제 확인
        if is_nutrient_in_db('루테인') and answers.get('dry_eyes') == '예':  # 눈 건강 문제
            recommended_supplements.append({
                'name': '루테인',
                'reason': '눈 건강 문제 개선을 위해 추천합니다. 시력 보호와 눈 피로 완화에 효과적입니다.'
            })
        
        # 비타민 C - 면역력 확인
        if is_nutrient_in_db('비타민 C') and answers.get('frequent_cold') == '예':  # 면역력 저하
            recommended_supplements.append({
                'name': '비타민 C',
                'reason': '면역력 강화를 위해 추천합니다. 스트레스 상황에서 소모되기 쉬운 영양소입니다.'
            })
        
        # 철분 - 여성, 특히 젊은 여성
        if is_nutrient_in_db('철') and answers.get('gender') == '여성' and answers.get('age_range') in ['19-29', '30-49']:
            recommended_supplements.append({
                'name': '철',
                'reason': '여성의 경우 철분 섭취에 특히 주의가 필요합니다. 월경으로 인한 철분 손실을 보충하는 데 도움이 됩니다.'
            })
        
        # 칼슘 - 나이 많은 여성
        if is_nutrient_in_db('칼슘') and answers.get('gender') == '여성' and answers.get('age_range') in ['50-64', '65+']:
            recommended_supplements.append({
                'name': '칼슘',
                'reason': '골다공증 예방을 위해 충분한 칼슘 섭취가 중요합니다. 특히 폐경 후 여성에게 필요합니다.'
            })
        
        # 기본 추천 (추천이 없을 경우)
        if not recommended_supplements:
            if is_nutrient_in_db('비타민 D'):
                recommended_supplements.append({
                    'name': '비타민 D',
                    'reason': '전반적인 건강 유지를 위한 기본 영양소 보충을 위해 추천합니다. 특히 햇빛 노출이 부족한 현대인에게 필요합니다.'
                })
            elif is_nutrient_in_db('비타민 C'):
                recommended_supplements.append({
                    'name': '비타민 C',
                    'reason': '면역력 강화와 항산화 작용을 위해 추천합니다. 전반적인 건강 유지에 도움이 됩니다.'
                })
            else:
                recommended_supplements.append({
                    'name': '종합 비타민',
                    'reason': '전반적인 건강 유지를 위한 기본 영양소 보충을 위해 추천합니다.'
                })
        
        section = "설문 결과를 종합적으로 고려하여 다음 영양소들을 추천합니다.\n\n"
        for supplement in recommended_supplements:
            section += f"#### **{supplement['name']}**: {supplement['reason']}\n\n"
        
        return section
        
    except Exception as e:
        print(f"Error generating recommended supplements: {str(e)}")
        return f"추천 영양제 생성 중 오류가 발생했습니다: {str(e)}"


def get_recommended_supplements_from_report(survey_result):
    """
    보고서 기반으로 추천 영양제를 가져옵니다 (마이페이지용)
    """
    try:
        answers = survey_result.answers
        recommended_supplements = []
        
        # 비타민 D - 실내 생활 여부 확인
        if is_nutrient_in_db('비타민 D') and answers.get('indoor_daytime') == '예':  # 실내에서 주로 생활
            recommended_supplements.append({
                'name': '비타민 D',
                'reason': '실내에서 주로 생활하시므로 햇빛 노출이 부족할 수 있어 비타민 D 보충이 필요합니다.'
            })
        
        # 마그네슘 - 수면 문제 확인
        if is_nutrient_in_db('마그네슘') and (answers.get('sleep_well') == '아니오' or answers.get('still_tired') == '예'):  # 수면의 질
            recommended_supplements.append({
                'name': '마그네슘',
                'reason': '수면의 질 저하와 피로 증상 개선을 위해 추천합니다.'
            })
        
        # 비타민 B 복합체 - 피로 확인
        b_complex = ['비타민 B1', '비타민 B2', '비타민 B6', '비타민 B12', '나이아신', '엽산', '판토텐산', '비오틴']
        if any(is_nutrient_in_db(b) for b in b_complex) and answers.get('fatigue') == '예':  # 피로
            recommended_supplements.append({
                'name': '비타민 B 복합체',
                'reason': '에너지 대사와 피로 회복을 위해 추천합니다.'
            })
        
        # 루테인 - 눈 건강 문제 확인
        if is_nutrient_in_db('루테인') and answers.get('dry_eyes') == '예':  # 눈 건강 문제
            recommended_supplements.append({
                'name': '루테인',
                'reason': '눈 건강 문제 개선을 위해 추천합니다.'
            })
        
        # 비타민 C - 면역력 확인
        if is_nutrient_in_db('비타민 C') and answers.get('frequent_cold') == '예':  # 면역력 저하
            recommended_supplements.append({
                'name': '비타민 C',
                'reason': '면역력 강화를 위해 추천합니다.'
            })
        
        # 기본 추천 (추천이 없을 경우)
        if not recommended_supplements:
            if is_nutrient_in_db('비타민 D'):
                recommended_supplements.append({
                    'name': '비타민 D',
                    'reason': '전반적인 건강 유지를 위한 기본 영양소 보충을 위해 추천합니다.'
                })
            elif is_nutrient_in_db('비타민 C'):
                recommended_supplements.append({
                    'name': '비타민 C',
                    'reason': '면역력 강화와 항산화 작용을 위해 추천합니다.'
                })
            else:
                recommended_supplements.append({
                    'name': '종합 비타민',
                    'reason': '전반적인 건강 유지를 위한 기본 영양소 보충을 위해 추천합니다.'
                })
        
        return recommended_supplements[:3]
        
    except Exception as e:
        print(f"Error getting recommended supplements from report: {str(e)}")
        return []

def generate_warnings_section(survey_result):
    """
    Generuje sekcję 3: 주의가 필요한 영양소
    """
    try:
        # Mapowanie odpowiedzi z ankiety
        answers = survey_result.answers
        
        # Sprawdź czy answers to string JSON
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        section = "설문 결과를 바탕으로, 다음 영양소들은 섭취에 주의하거나 피하시는 것이 좋습니다.\n\n"
        
        # 비타민 K - 약물 복용 확인
        if is_nutrient_in_db('비타민 K') and answers.get('chronic_medication') == '예':  # 만성질환 약물
            section += "#### **비타민 K**: 만성질환 약물을 복용하고 계시다면, 비타민 K는 혈액 응고에 영향을 줄 수 있으므로 의사와 상담 후 섭취하시기 바랍니다.\n\n"
        
        # 철 - 소화기 문제 확인
        if is_nutrient_in_db('철') and answers.get('symptom_2') == '예':  # 소화기 문제
            section += "#### **철**: 소화기 문제를 경험하고 계시다면, 철분 보충제는 위장 자극을 일으킬 수 있으므로 식사와 함께 섭취하시기 바랍니다.\n\n"
        
        # 칼슘 - 약물 복용 확인
        if is_nutrient_in_db('칼슘') and answers.get('chronic_medication') == '예':  # 만성질환 약물
            section += "#### **칼슘**: 특정 약물을 복용하고 계시다면, 칼슘은 약물 흡수를 방해할 수 있으므로 복용 시간을 조절하시기 바랍니다.\n\n"
        
        # 알레르기 주의사항
        if answers.get('allergies') == '예':
            section += "#### **알레르기 주의**: 알레르기가 있는 성분이 포함된 보충제는 피하시고, 새로운 보충제 섭취 시에는 소량부터 시작하여 반응을 관찰하시기 바랍니다.\n\n"
        
        if section == "설문 결과를 바탕으로, 다음 영양소들은 섭취에 주의하거나 피하시는 것이 좋습니다.\n\n":
            section += "현재 특별한 주의사항이 없습니다. 하지만 새로운 영양제 섭취 시에는 반드시 성분표를 확인하시고, 알레르기 반응이 나타나면 즉시 섭취를 중단하시기 바랍니다.\n\n"
        
        return section
        
    except Exception as e:
        print(f"Error generating warnings: {str(e)}")
        return f"주의사항 생성 중 오류가 발생했습니다: {str(e)}"

def generate_considerations_section(survey_result):
    """
    Generuje sekcję uwag i dodatkowych informacji na podstawie odpowiedzi z ankiety
    """
    try:
        # Mapowanie odpowiedzi z ankiety
        answers = survey_result.answers
        
        # Sprawdź czy answers to string JSON
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        considerations = []
        
        # Sprawdź płeć i wiek
        gender = answers.get('gender', '')
        age_range = answers.get('age_range', '')
        
        if gender == '여성' and age_range in ['19-29', '30-49']:
            considerations.append("• **철분 섭취**: 여성의 경우 철분 섭취에 특히 주의하세요.")
            considerations.append("• **칼슘 섭취**: 골다공증 예방을 위해 충분한 칼슘 섭취가 중요합니다.")
        
        if age_range in ['50-64', '65+']:
            considerations.append("• **노화와 영양소 흡수**: 나이가 들수록 영양소 흡수율이 감소할 수 있으므로 의사와 상담하세요.")
        
        # Sprawdź styl życia
        sitting_work = answers.get('sitting_work', '')
        if sitting_work == '예':
            considerations.append("• **운동 습관**: 장시간 앉아서 일하는 경우 정기적인 운동이 필요합니다.")
        
        exercise = answers.get('exercise', '')
        if exercise == '아니오':
            considerations.append("• **운동 습관**: 규칙적인 운동을 통해 건강을 유지하세요.")
        
        # Sprawdź stres i 피로
        fatigue = answers.get('fatigue', '')
        if fatigue == '예':
            considerations.append("• **피로 관리**: 충분한 휴식과 스트레스 관리가 중요합니다.")
        
        # Sprawdź sen
        sleep_well = answers.get('sleep_well', '')
        still_tired = answers.get('still_tired', '')
        if sleep_well == '아니오' or still_tired == '예':
            considerations.append("• **수면 관리**: 충분한 수면과 휴식이 중요합니다.")
        
        # Sprawdź alergie
        allergies = answers.get('allergies', '')
        if allergies == '예':
            considerations.append("• **알레르기 주의**: 알레르기가 있는 성분이 포함된 보충제는 피하세요.")
        
        # Sprawdź leki
        chronic_medication = answers.get('chronic_medication', '')
        if chronic_medication == '예':
            considerations.append("• **약물 상호작용**: 복용 중인 약물과 보충제 간의 상호작용을 확인하세요.")
            considerations.append("• **의사 상담**: 약물을 복용 중인 경우 보충제 섭취 전 의사와 상담하세요.")
        
        # Dodaj ogólne uwagi
        considerations.append("• **점진적 섭취**: 새로운 보충제는 소량부터 시작하여 점진적으로 늘리세요.")
        considerations.append("• **지속적 모니터링**: 보충제 섭취 후 건강 상태를 지속적으로 관찰하세요.")
        considerations.append("• **균형잡힌 식단**: 보충제는 균형잡힌 식단을 대체할 수 없습니다.")
        considerations.append("• **성분 확인**: 보충제 구매 시 성분표를 꼼꼼히 확인하세요.")
        considerations.append("• **유통기한**: 보충제의 유통기한을 확인하고 올바르게 보관하세요.")
        
        if not considerations:
            considerations = [
                "• **균형잡힌 식단**: 다양한 영양소를 포함한 균형잡힌 식단을 유지하세요.",
                "• **규칙적인 운동**: 건강한 생활습관을 위해 규칙적인 운동을 하세요.",
                "• **충분한 수면**: 하루 7-8시간의 충분한 수면을 취하세요.",
                "• **스트레스 관리**: 적절한 스트레스 관리가 중요합니다.",
                "• **의사 상담**: 보충제 섭취 전 의사와 상담하세요."
            ]
        
        markdown_content = "\n\n".join(considerations)
        
        return markdown_content
        
    except Exception as e:
        print(f"Error generating considerations section: {str(e)}")
        return "• **의사 상담**: 보충제 섭취 전 의사와 상담하세요.\n\n• **균형잡힌 식단**: 보충제는 균형잡힌 식단을 대체할 수 없습니다."
