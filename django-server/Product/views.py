from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Products
from django.http import JsonResponse
from Mypage.models import Like
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
import os, json
from django.conf import settings
from django.http import JsonResponse

def get_product_details(request, product_id=None):
    """
    단일 상품 또는 여러 상품의 상세 정보를 반환하는 API
    
    GET /product/details/{product_id}/ - 단일 상품 정보 반환
    GET /product/details/?ids=1,2,3 - 여러 상품 정보 반환
    """
    try:
        user_id = request.user.id if request.user.is_authenticated else None
        if product_id:
            # 단일 상품 조회
            product = get_object_or_404(Products, id=product_id)
            
            # 임시 사용자 ID (실제 구현에서는 인증된 사용자 정보 사용)
            user = request.user
            user_id = user.id
            
            # 좋아요 여부 확인
            if user_id:
                is_liked = Like.objects.filter(user_id=user_id, product=product).exists()
            
            product_data = {
                'id': product.id,
                'url': product.url,
                'title': product.title,
                'safety_info': product.safety_info,
                'ingredients': product.ingredients,
                'directions': product.directions,
                'brand': product.brand,
                'flavor': product.flavor,
                'supplement_type': product.supplement_type,
                'quantity': product.quantity,
                'product_form': product.product_form,
                'average_rating': product.average_rating,
                'total_reviews': product.total_reviews,
                'image_link': product.image_link,
                'total_price': product.total_price,
                'price_value': product.price_value,
                'vegan': product.vegan,
                'country_of_origin': product.country_of_origin,
                'is_liked': is_liked,
            }
            return JsonResponse(product_data)
        else:
            # 여러 상품 조회 (ids 쿼리 파라미터 사용)
            product_ids = request.GET.get('ids', '')
            if not product_ids:
                return JsonResponse({'error': '상품 ID가 제공되지 않았습니다.'}, status=400)
            
            # 쉼표로 구분된 ID 목록을 리스트로 변환
            id_list = [int(pid.strip()) for pid in product_ids.split(',') if pid.strip().isdigit()]
            
            if not id_list:
                return JsonResponse({'error': '유효한 상품 ID가 없습니다.'}, status=400)
            
            # 요청된 ID에 해당하는 상품들 조회
            products = Products.objects.filter(id__in=id_list)
            
            # 임시 사용자 ID (실제 구현에서는 인증된 사용자 정보 사용)
            user = request.user
            user_id = user.id
            
            # 좋아요한 상품 ID 목록 가져오기
            liked_product_ids = Like.objects.filter(user_id=user_id).values_list('product_id', flat=True)
            
            # 상품 목록에 좋아요 정보 추가
            for product in products:
                product.is_liked = product.id in liked_product_ids
            
            # 결과 포맷팅
            products_data = []
            for product in products:
                products_data.append({
                    'id': product.id,
                    'url': product.url,
                    'title': product.title,
                    'safety_info': product.safety_info,
                    'ingredients': product.ingredients,
                    'directions': product.directions,
                    'brand': product.brand,
                    'flavor': product.flavor,
                    'supplement_type': product.supplement_type,
                    'quantity': product.quantity,
                    'product_form': product.product_form,
                    'average_rating': product.average_rating,
                    'total_reviews': product.total_reviews,
                    'image_link': product.image_link,
                    'total_price': product.total_price,
                    'price_value': product.price_value,
                    'vegan': product.vegan,
                    'country_of_origin': product.country_of_origin,
                    'is_liked': product.is_liked,
                })
            
            return JsonResponse({'products': products_data})
    
    except Products.DoesNotExist:
        return JsonResponse({'error': f'상품 ID {product_id}를 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'오류가 발생했습니다: {str(e)}'}, status=500)

class ProductDetailsAPIView(APIView):
    """
    상품 상세 정보를 반환하는 API 클래스 뷰
    """
    def get(self, request, product_id=None):
        return get_product_details(request, product_id)

def product_list(request):
    """
    상품 목록 페이지 뷰
    """
    products = Products.objects.all().order_by('-average_rating')
    
    # 임시 사용자 ID (실제 구현에서는 인증된 사용자 정보 사용)
    user_id = 1
    
    # 좋아요한 상품 ID 목록 가져오기
    liked_product_ids = Like.objects.filter(user_id=user_id).values_list('product_id', flat=True)
    
    # 상품 목록에 좋아요 정보 추가
    for product in products:
        product.is_liked = product.id in liked_product_ids
    
    context = {
        'products': products
    }
    
    return render(request, 'Product/product_list.html', context)



def get_weighted_scores(request):
    products = Products.objects.order_by('sales_ranks')[:10]
    print(products)
    return JsonResponse({'results': products})


def get_popular_products(request):
    products = Products.objects.order_by('-average_rating')[:10]
    print(products)
    return JsonResponse({'products': products})


def get_best_selling_products(request):
    products = Products.objects.order_by('sales_ranks')[:10]

    data = [
        {
            'id': p.id,
            'title': p.title,
            'url': p.url,
            'image_link': p.image_link or 'https://via.placeholder.com/150',
            'average_rating': p.average_rating,
            'price_value': p.price_value,
            'sales_ranks': p.sales_ranks,
        }
        for p in products
    ]

    return JsonResponse({'results': data})