from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import SurveyResponse
import json
import os
from django.conf import settings

def load_survey_questions():
    """JSON 파일에서 설문 질문을 로드합니다."""
    json_path = os.path.join(settings.BASE_DIR, 'Survey', 'static', 'json', 'survey_questions.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('questions', [])
    except Exception as e:
        print(f"Error loading survey questions: {e}")
        return []

def survey_view(request):
    """설문조사 페이지를 렌더링합니다."""
    questions = load_survey_questions()
    context = {
        'survey_questions': questions
    }
    return render(request, 'survey.html', context)

def mypage_view(request):
    return render(request, 'survey/mypage.html')

def favorite_view(request):
    return render(request, 'survey/favorite.html')

def analysis_view(request):
    return render(request, 'survey/analysis.html')

@csrf_exempt
@require_http_methods(["POST"])
def save_survey(request):
    """설문조사 결과를 저장합니다."""
    try:
        data = json.loads(request.body)
        
        # Walidacja wymaganych pól
        required_fields = ['height', 'weight', 'sitting_work', 'indoor_daytime', 
                         'exercise', 'smoking', 'drinking', 'fatigue', 
                         'sleep_well', 'still_tired']
        
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return JsonResponse({
                'status': 'error',
                'message': f'다음 필드를 입력해주세요: {", ".join(missing_fields)}'
            }, status=400)
        
        # Konwersja wartości numerycznych
        try:
            height = float(data.get('height', 0))
            weight = float(data.get('weight', 0))
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': '키와 몸무게는 숫자로 입력해주세요.'
            }, status=400)
        
        # Walidacja wartości numerycznych
        if height <= 0 or weight <= 0:
            return JsonResponse({
                'status': 'error',
                'message': '키와 몸무게는 0보다 큰 값을 입력해주세요.'
            }, status=400)
        
        # Zapisywanie odpowiedzi
        response = SurveyResponse.objects.create(
            height=height,
            weight=weight,
            sitting_work=data.get('sitting_work'),
            indoor_daytime=data.get('indoor_daytime'),
            exercise=data.get('exercise'),
            smoking=data.get('smoking'),
            drinking=data.get('drinking'),
            fatigue=data.get('fatigue'),
            sleep_well=data.get('sleep_well'),
            still_tired=data.get('still_tired')
        )
        
        return JsonResponse({
            'status': 'success',
            'message': '설문조사가 성공적으로 저장되었습니다.',
            'redirect_url': '/mypage/'  # Dodajemy URL do przekierowania
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '잘못된 데이터 형식입니다.'
        }, status=400)
    except Exception as e:
        print(f"Error saving survey: {e}")  # Dodajemy logowanie błędów
        return JsonResponse({
            'status': 'error',
            'message': '서버 오류가 발생했습니다. 다시 시도해주세요.'
        }, status=500)

@csrf_exempt
def save_survey_results(request):
    """설문조사 결과를 저장합니다."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            response = SurveyResponse.objects.create(
                sedentary=data.get('question1'),
                gender=data.get('question2'),
                birth_year=data.get('birthYear')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}) 