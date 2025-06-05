from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SurveyResponse
import json

def survey_view(request):
    """설문조사 페이지를 렌더링합니다."""
    return render(request, 'survey/survey.html')

def mypage_view(request):
    return render(request, 'survey/mypage.html')

def favorite_view(request):
    return render(request, 'survey/favorite.html')

def analysis_view(request):
    return render(request, 'survey/analysis.html')

@csrf_exempt
def save_survey(request):
    """설문조사 결과를 저장합니다."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 필수 필드 확인
            required_fields = ['sedentary', 'gender', 'birthYear']
            if not all(field in data for field in required_fields):
                return JsonResponse({
                    'status': 'error',
                    'message': '필수 항목이 누락되었습니다.'
                }, status=400)
            
            # 설문 응답 저장
            response = SurveyResponse.objects.create(
                sedentary=data['sedentary'],
                gender=data['gender'],
                birth_year=int(data['birthYear'])
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '설문조사가 성공적으로 저장되었습니다.'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '잘못된 데이터 형식입니다.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'status': 'error',
        'message': '허용되지 않는 메소드입니다.'
    }, status=405)

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