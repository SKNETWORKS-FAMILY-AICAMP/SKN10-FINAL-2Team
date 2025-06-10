import os
import json
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from .models import SurveyResponse, SurveyResult, Supplement, UserHealthReport, Nutrient, UserNutrientIntake, NutrientAnalysis
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from Product.models import Favorite, Products  # 파일 상단에 추가
import pytesseract
from PIL import Image
import re

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
def survey_view(request):
    # survey_questions.json 파일 경로
    json_file_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'survey_questions.json')
    print(f"Loading survey questions from: {json_file_path}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            survey_questions = json.load(f)
            print(f"Loaded {len(survey_questions)} questions")
            print("Questions:", survey_questions)
    except FileNotFoundError:
        survey_questions = []
        print(f"Error: {json_file_path} not found")
    except json.JSONDecodeError as e:
        survey_questions = []
        print(f"Error: Invalid JSON in {json_file_path}: {str(e)}")
    except Exception as e:
        survey_questions = []
        print(f"Unexpected error: {str(e)}")
    
    context = {
        'user': request.user,
        'survey_questions': survey_questions,
        'debug_info': {
            'file_path': json_file_path,
            'questions_count': len(survey_questions)
        }
    }
    return render(request, 'Mypage/survey.html', context)

@login_required
def favorite_view(request):
    # 사용자가 좋아요한 영양제 가져오기
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    liked_supplements = [fav.product for fav in favorites]

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
    return render(request, 'Mypage/favorite.html', context)

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
        
        context = {
            'health_score': health_score,
            'recommendations': health_report.recommendations,
            'recommended_supplements': recommended_supplements,
            'survey_result': latest_survey
        }
    else:
        context = {
            'message': '아직 설문 결과가 없습니다. 설문을 먼저 진행해주세요.'
        }
    
    context['user'] = request.user
    context['debug_info'] = {
        'file_path': os.path.join(settings.STATIC_ROOT, 'json', 'Mypage', 'nutrient_standards.json'),
        'questions_count': 0
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

@login_required
def save_survey(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 설문 응답 저장
            survey_response = SurveyResponse.objects.create(
                user=request.user,
                responses=data if data else {},
                answers=data if data else {},
                height=data.get('height'),
                weight=data.get('weight'),
                sitting_work=data.get('sitting_work'),
                indoor_daytime=data.get('indoor_daytime'),
                exercise=data.get('exercise'),
                smoking=data.get('smoking'),
                drinking=data.get('drinking'),
                fatigue=data.get('fatigue'),
                sleep_well=data.get('sleep_well'),
                still_tired=data.get('still_tired'),
                sleep_hours=data.get('sleep_hours'),
                exercise_frequency=data.get('exercise_frequency'),
                water_intake=data.get('water_intake'),
                health_status='completed'
            )
            
            # 설문 결과 생성
            health_score = calculate_health_score(survey_response)
            recommended_supplements = get_recommended_supplements(survey_response)
            recommendations = generate_recommendations(survey_response, health_score)
            
            survey_result = SurveyResult.objects.create(
                user=request.user,
                answers=data if data else {},
                result={
                    'health_score': health_score,
                    'recommendations': recommendations,
                    'recommended_supplements': recommended_supplements
                },
                health_status='좋음' if health_score >= 80 else '보통' if health_score >= 60 else '나쁨',
                recommended_supplements=recommended_supplements
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '설문이 저장되었습니다.',
                'redirect_url': '/mypage/survey-result/'  # 절대 경로로 수정
            })
            
        except Exception as e:
            print(f"Error saving survey: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)

@login_required
def survey_result(request):
    # 가장 최근 설문 결과 가져오기
    latest_survey = SurveyResult.objects.filter(user=request.user).order_by('-created_at').first()
    
    if latest_survey:
        context = {
            'survey_result': latest_survey,
            'health_score': latest_survey.result.get('health_score', 0),
            'recommendations': latest_survey.result.get('recommendations', '').split('\n'),
            'recommended_supplements': latest_survey.result.get('recommended_supplements', [])
        }
    else:
        context = {
            'message': '아직 설문 결과가 없습니다.'
        }
    
    context['user'] = request.user
    return render(request, 'Mypage/survey_result.html', context)

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
def analyze_nutrients(request):
    try:
        # 최근 7일간의 영양소 섭취 기록 가져오기
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        intakes = UserNutrientIntake.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        ).select_related('nutrient')

        # 영양소별 평균 섭취량 계산
        nutrient_averages = {}
        for intake in intakes:
            if intake.nutrient.name not in nutrient_averages:
                nutrient_averages[intake.nutrient.name] = {
                    'total': 0,
                    'count': 0,
                    'recommended': intake.nutrient.daily_recommended
                }
            nutrient_averages[intake.nutrient.name]['total'] += intake.amount
            nutrient_averages[intake.nutrient.name]['count'] += 1

        # 평균 섭취량 계산 및 점수 산출
        overall_score = 0
        details = []
        recommendations = []

        for nutrient_name, data in nutrient_averages.items():
            avg_intake = data['total'] / data['count']
            percentage = (avg_intake / data['recommended']) * 100
            score = min(100, percentage)
            overall_score += score

            details.append(f"{nutrient_name}: {avg_intake:.1f}% (권장량 대비)")

            if percentage < 80:
                recommendations.append(f"{nutrient_name} 섭취량이 부족합니다. 권장량의 {percentage:.1f}%만 섭취하고 있습니다.")
            elif percentage > 120:
                recommendations.append(f"{nutrient_name} 섭취량이 과다합니다. 권장량의 {percentage:.1f}%를 섭취하고 있습니다.")

        # 전체 점수 계산 (100점 만점)
        overall_score = overall_score / len(nutrient_averages) if nutrient_averages else 0

        # 분석 결과 저장
        analysis = NutrientAnalysis.objects.create(
            user=request.user,
            analysis_date=end_date,
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
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def get_favorite_products(request):
    try:
        favorites = Favorite.objects.filter(user=request.user).select_related('product')
        products = [{
            'id': fav.product.id,
            'name': fav.product.title,
            'description': fav.product.ingredients,
            'image_url': fav.product.image_link
        } for fav in favorites]
        
        return JsonResponse({
            'status': 'success',
            'products': products
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_nutrient_data(request):
    try:
        # Wczytaj standardy żywieniowe
        with open(os.path.join(settings.BASE_DIR, 'Product', 'data', 'nutrient_standards.json'), 'r', encoding='utf-8') as f:
            standards = json.load(f)
        
        # Pobierz ulubione produkty użytkownika
        favorites = Favorite.objects.filter(user=request.user)
        
        # Przygotuj dane o składnikach
        nutrient_data = {}
        for nutrient, standard in standards.items():
            actual_amount = 0
            for favorite in favorites:
                product = favorite.product
                if hasattr(product, 'ingredients') and nutrient in product.ingredients:
                    actual_amount += float(product.ingredients[nutrient])
            
            percentage = min(100, (actual_amount / standard['recommended_amount']) * 100)
            
            nutrient_data[nutrient] = {
                'actual_amount': round(actual_amount, 2),
                'recommended_amount': standard['recommended_amount'],
                'unit': standard['unit'],
                'description': standard['description'],
                'percentage': round(percentage, 1)
            }
        
        return JsonResponse({
            'status': 'success',
            'nutrients': nutrient_data
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