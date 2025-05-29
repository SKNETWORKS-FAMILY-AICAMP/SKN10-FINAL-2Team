from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def survey_view(request):
    return render(request, 'survey.html')

@csrf_exempt
def save_survey_results(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # TODO: 데이터베이스에 결과 저장
            return JsonResponse({"status": "success"})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"}, status=400)
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405) 