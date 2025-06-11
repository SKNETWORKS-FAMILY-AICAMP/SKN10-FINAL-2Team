import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from .models import SurveyResponse, SurveyResult, Supplement, UserHealthReport, Nutrient_daily, UserNutrientIntake, NutrientAnalysis, Like, UserLog, Favorite
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
            print(f"Loaded {len(survey_questions.get('questions', []))} questions")
            print("Questions:", survey_questions)
    except FileNotFoundError:
        survey_questions = {'questions': []}
        print(f"Error: {json_file_path} not found")
    except json.JSONDecodeError as e:
        survey_questions = {'questions': []}
        print(f"Error: Invalid JSON in {json_file_path}: {str(e)}")
    except Exception as e:
        survey_questions = {'questions': []}
        print(f"Unexpected error: {str(e)}")
    
    context = {
        'user': request.user,
        'survey_questions': survey_questions,
        'debug_info': {
            'file_path': json_file_path,
            'questions_count': len(survey_questions.get('questions', []))
        }
    }
    return render(request, 'Mypage/survey.html', context)

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
        return redirect('mypage')

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
            print("POST data received:", request.POST)
            
            # POST 데이터에서 응답 가져오기
            responses = request.POST.get('responses', '{}')
            answers = request.POST.get('answers', '{}')
            height = float(request.POST.get('height', 0))
            weight = float(request.POST.get('weight', 0))
            sitting_work = request.POST.get('sitting_work', '')
            indoor_daytime = request.POST.get('indoor_daytime', '')
            exercise = request.POST.get('exercise', '')
            smoking = request.POST.get('smoking', '')
            drinking = request.POST.get('drinking', '')
            fatigue = request.POST.get('fatigue', '')
            sleep_well = request.POST.get('sleep_well', '')
            still_tired = request.POST.get('still_tired', '')
            sleep_hours = float(request.POST.get('sleep_hours', 0))
            exercise_frequency = request.POST.get('exercise_frequency', '')
            water_intake = float(request.POST.get('water_intake', 0))
            health_status = request.POST.get('health_status', '보통')

            # SurveyResponse 객체 생성 및 저장
            survey_response = SurveyResponse.objects.create(
                user=request.user,
                responses=responses,
                answers=answers,
                height=height,
                weight=weight,
                sitting_work=sitting_work,
                indoor_daytime=indoor_daytime,
                exercise=exercise,
                smoking=smoking,
                drinking=drinking,
                fatigue=fatigue,
                sleep_well=sleep_well,
                still_tired=still_tired,
                sleep_hours=sleep_hours,
                exercise_frequency=exercise_frequency,
                water_intake=water_intake
            )

            # SurveyResult 객체 생성 및 저장
            survey_result = SurveyResult.objects.create(
                user=request.user,
                # survey_response=survey_response,
                answers={
                    'height': height,
                    'weight': weight,
                    'sitting_work': sitting_work,
                    'indoor_daytime': indoor_daytime,
                    'exercise': exercise,
                    'smoking': smoking,
                    'drinking': drinking,
                    'fatigue': fatigue,
                    'sleep_well': sleep_well,
                    'still_tired': still_tired,
                    'sleep_hours': sleep_hours,
                    'exercise_frequency': exercise_frequency,
                    'water_intake': water_intake,
                    'health_status': health_status
                }
            )

            print(f"Survey response saved: {survey_response.id}")
            print(f"Survey result saved: {survey_result.id}")
            return redirect('mypage:survey_result')
        except Exception as e:
            print(f"Error saving survey response: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': '설문 응답을 저장하는 중 오류가 발생했습니다.'
            }, status=500)
    return redirect('mypage:survey')

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

        nutrient = Nutrient_daily.objects.get(id=nutrient_id)
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
def get_nutrient_data(request):
    try:
        # 사용자의 최신 영양소 분석 결과 가져오기
        latest_analysis = NutrientAnalysis.objects.filter(user=request.user).order_by('-date').first()
        
        if not latest_analysis:
            return JsonResponse({
                'status': 'error',
                'message': '영양소 분석 결과가 없습니다.'
            })
        
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
    User = get_user_model()
    # user = User.objects.get(pk=1)
    user = request.user
    like_list = Like.objects.filter(user=user).select_related('product')
    return render(request, 'Mypage/like.html', {'user': user, 'like_list': like_list})

@require_POST
@login_required
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

@require_POST
@login_required
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
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
@login_required
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
@require_http_methods(["POST", "DELETE", "GET"])
@login_required
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
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "지원하지 않는 메서드입니다."}, status=405)
