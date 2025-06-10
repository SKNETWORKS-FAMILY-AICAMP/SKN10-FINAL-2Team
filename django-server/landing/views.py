from django.shortcuts import render
import os
import json
from django.http import JsonResponse
from django.conf import settings

def landing(request):
    json_path = os.path.join(settings.BASE_DIR, 'landing', 'processed_data.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    return render(request, 'landing/landing.html', {'products': products})

def get_top_products(request):
    # views.py 파일 기준으로 같은 폴더에 있다고 가정
    current_dir = os.path.dirname(__file__)
    json_path = os.path.join(current_dir, 'processed_data.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JsonResponse(data, safe=False)
    except FileNotFoundError:
        return JsonResponse({'error': '파일이 없습니다.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 형식 오류'}, status=500)

# 가중 평균을 이용한 가성비 영양제 추천.
from django.http import JsonResponse
from sklearn.preprocessing import MinMaxScaler
import re
import numpy as np
import pandas as pd

def extract_price(value):
    if isinstance(value, str):
        match = re.search(r'\$?([0-9.]+)', value)
        if match:
            return float(match.group(1))
    return None
