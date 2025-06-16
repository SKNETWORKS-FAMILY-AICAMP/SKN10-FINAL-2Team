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
from datetime import datetime, timedelta
from Product.models import Products  # 파일 상단에 추가
import pytesseract
from PIL import Image
import re
from django.contrib import messages
import csv

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
        amount = data.get('amount')
        date = data.get('date', timezone.now().date())

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

        # 영양소 섭취 기록 생성
        intake = UserNutrientIntake.objects.create(
            user=request.user,
            nutrient=nutrient,
            amount=amount,
            date=date
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
                'amount': amount,
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
            if intake.nutrient.name not in nutrient_averages:
                nutrient_averages[intake.nutrient.name] = {
                    'total': 0,
                    'count': 0,
                    'recommended': intake.nutrient.daily_recommended or 100
                }
            nutrient_averages[intake.nutrient.name]['total'] += intake.amount
            nutrient_averages[intake.nutrient.name]['count'] += 1

        print("영양소별 평균:", nutrient_averages)

        # 평균 섭취량 계산 및 점수 산출
        overall_score = 0
        details = []
        recommendations = []

        for nutrient_name, data in nutrient_averages.items():
            avg_intake = data['total'] / data['count']
            recommended = data['recommended']
            
            if recommended > 0:
                percentage = (avg_intake / recommended) * 100
                score = min(100, percentage)
                overall_score += score

                details.append(f"{nutrient_name}: {avg_intake:.1f}% (권장량 대비)")

                if percentage < 80:
                    recommendations.append(f"{nutrient_name} 섭취량이 부족합니다. 권장량의 {percentage:.1f}%만 섭취하고 있습니다.")
                elif percentage > 120:
                    recommendations.append(f"{nutrient_name} 섭취량이 과다합니다. 권장량의 {percentage:.1f}%를 섭취하고 있습니다.")

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

def parse_ingredients(text):
    ingredients = {}
    # Szukaj linii z wartościami odżywczymi
    # Przykład: "비타민A 210 ㎍ RE(30 %)"
    pattern = re.compile(r'([가-힣A-Za-z0-9]+)\s*([\d\.]+)\s*([a-zA-Z㎍mgRE%]+)')
    for line in text.split('\n'):
        for match in re.finditer(pattern, line):
            name = match.group(1)
            value = match.group(2)
            unit = match.group(3)
            ingredients[name] = value + unit
    return ingredients

@csrf_exempt
@require_POST
def ocr_extract(request):
    if 'image' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No image uploaded'}, status=400)
    image_file = request.FILES['image']
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image, lang='kor+eng')
        print(text)  # Debug: sprawdź co zwraca OCR
        ingredients = parse_ingredients(text)
        if not ingredients:
            ingredients = {'메시지': '성분을 인식하지 못했습니다.'}
        return JsonResponse({'status': 'success', 'ingredients': ingredients})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}) 

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
        # 모든 영양소 섭취 기록 가져오기
        intakes = UserNutrientIntake.objects.filter(
            user=request.user
        ).select_related('nutrient').order_by('-date', '-created_at')

        history = []
        for intake in intakes:
            history.append({
                'id': intake.id,
                'nutrient_name': intake.nutrient.name,
                'amount': intake.amount,
                'unit': intake.nutrient.unit,
                'date': intake.date.strftime('%Y-%m-%d'),
                'created_at': intake.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return JsonResponse({
            'status': 'success',
            'data': history
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
        intake_id = data.get('id')
        amount = data.get('amount')
        date = data.get('date')

        intake = UserNutrientIntake.objects.get(id=intake_id, user=request.user)
        
        if amount is not None:
            intake.amount = amount
        if date is not None:
            intake.date = date
            
        intake.save()

        # 영양분석 실행
        try:
            analyze_nutrients(request)
        except Exception as e:
            print(f"영양분석 실행 중 오류 발생: {str(e)}")

        return JsonResponse({
            'status': 'success',
            'message': '영양소 섭취 기록이 수정되었습니다.'
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
