from django.shortcuts import render
import os
import json
from django.http import JsonResponse
from django.conf import settings

def landing(request):
    json_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'json', 'processed_data.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    return render(request, 'landing/landing.html', {'products': products})

def get_top_products(request):
    # views.py 파일 기준으로 같은 폴더에 있다고 가정
    json_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'json', 'processed_data.json')
    
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
# from .models import Product
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


def get_weighted_scores(request):
    # 1. DB에서 필요한 데이터 쿼리
    products = Product.objects.all().values('id', 'title', 'average_rating', 'price')

    # 2. pandas DataFrame으로 변환
    df = pd.DataFrame(list(products))

    # 3. 가격 숫자 추출
    df['price_value'] = df['price'].apply(extract_price)

    # 4. 평점과 가격이 없는 행 제거
    valid_df = df[['id', 'title', 'average_rating', 'price_value']].dropna().copy()

    # 5. 정규화
    scaler = MinMaxScaler()
    normalized = scaler.fit_transform(valid_df[['average_rating', 'price_value']])
    valid_df['normalized_rating'] = normalized[:, 0]
    valid_df['normalized_price'] = normalized[:, 1]

    # 6. 가중 평균 점수 계산 (평점 70%, 가격 30% - 가격은 낮을수록 좋음)
    valid_df['score'] = 0.7 * valid_df['normalized_rating'] + 0.3 * (1 - valid_df['normalized_price'])

    # 7. 점수 기준 내림차순 정렬
    valid_df = valid_df.sort_values(by='score', ascending=False)

    # 8. JSON 반환을 위한 리스트 변환
    results = valid_df[['title', 'average_rating', 'price_value', 'score']].to_dict(orient='records')

    return JsonResponse({'results': results})
