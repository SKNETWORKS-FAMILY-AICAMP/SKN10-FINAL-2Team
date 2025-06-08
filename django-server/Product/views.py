from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Products, Favorite
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os
from django.conf import settings
import cv2
import numpy as np
from PIL import Image
import io
from django.contrib.auth.models import User

def product_list(request):
    """제품 목록 페이지를 렌더링합니다."""
    return render(request, 'product/product_list.html')

@login_required
def like_product(request):
    if request.method == 'GET':
        favorites = Favorite.objects.filter(user=request.user).select_related('product')
        return render(request, 'like_product.html', {'favorites': favorites})
    return redirect('home')

@login_required
def analysis(request):
    """영양분석 페이지를 렌더링합니다."""
    return render(request, 'analysis.html')

@login_required
def analysis_view(request):
    """영양제 분석 화면"""
    return render(request, 'analysis.html')

@login_required
def like_product_view(request):
    """좋아요한 제품 목록"""
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    return render(request, 'like_product.html', {'favorites': favorites})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def analyze_image_view(request):
    """이미지 분석 API"""
    if 'image' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': '이미지가 없습니다.'})
    
    try:
        image = request.FILES['image']
        # 지원하는 이미지 형식 확인
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if image.content_type not in allowed_types:
            return JsonResponse({
                'status': 'error',
                'message': '지원하지 않는 이미지 형식입니다. JPG 또는 PNG 파일만 업로드 가능합니다.'
            })
            
        # 이미지를 PIL Image로 변환
        img = Image.open(image)
        
        # PNG 이미지의 경우 RGBA를 RGB로 변환
        if image.content_type == 'image/png':
            if img.mode == 'RGBA':
                img = img.convert('RGB')
        
        # OpenCV 형식으로 변환
        img_array = np.array(img)
        
        # TODO: 실제 이미지 분석 로직 구현
        # 임시 결과 반환
        results = [
            {'name': '비타민 C', 'percentage': 100},
            {'name': '비타민 D', 'percentage': 75},
            {'name': '칼슘', 'percentage': 50}
        ]
        
        return JsonResponse({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'이미지 분석 중 오류가 발생했습니다: {str(e)}'
        })

def load_nutrient_standards():
    """영양소 기준치를 로드합니다."""
    json_path = os.path.join(settings.BASE_DIR, 'Product', 'data', 'nutrient_standards.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def analyze_ingredients_view(request):
    """성분 분석 API"""
    try:
        data = json.loads(request.body)
        ingredients = data.get('ingredients', '')
        
        if not ingredients:
            return JsonResponse({
                'status': 'error',
                'message': '성분이 입력되지 않았습니다.'
            })
        
        # 영양소 기준치 로드
        standards = load_nutrient_standards()
        
        # TODO: 실제 성분 분석 로직 구현
        # 임시 결과 반환 (기준치와 비교)
        results = []
        for nutrient, standard in standards['nutrients'].items():
            # 임시로 100mg로 설정된 실제 섭취량
            actual_amount = 100
            
            # 기준치 대비 백분율 계산
            percentage = (actual_amount / standard['recommended_amount']) * 100
            
            results.append({
                'name': nutrient,
                'actual_amount': actual_amount,
                'recommended_amount': standard['recommended_amount'],
                'unit': standard['unit'],
                'percentage': percentage,
                'description': standard['description']
            })
        
        return JsonResponse({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'성분 분석 중 오류가 발생했습니다: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def add_favorite(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Products, id=product_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def remove_favorite(request, product_id):
    if request.method == 'POST':
        favorite = get_object_or_404(Favorite, user=request.user, product_id=product_id)
        favorite.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@csrf_exempt
@require_http_methods(["GET"])
def load_favorites_view(request):
    """좋아요한 제품 목록 API"""
    try:
        favorites = Favorite.objects.filter(user=request.user).select_related('product')
        favorites_list = [{
            'id': fav.product.id,
            'title': fav.product.title,
            'brand': fav.product.brand,
            'image_link': fav.product.image_link
        } for fav in favorites]
        
        return JsonResponse({
            'status': 'success',
            'favorites': favorites_list
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'데이터 로딩 중 오류가 발생했습니다: {str(e)}'
        }) 