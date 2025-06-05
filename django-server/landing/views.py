from django.shortcuts import render

def landing(request):
    return render(request, 'landing/landing.html')

from django.http import JsonResponse
import json
import os

def get_ranked_data(request):
    json_path = os.path.join('your_app_name', 'processed_data.json')  # 앱 디렉토리 안에 저장하는 경우
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return JsonResponse({'results': data})