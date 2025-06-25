from django.shortcuts import render
import os
import json
from django.http import JsonResponse
from django.conf import settings
from sklearn.preprocessing import MinMaxScaler
import re
import numpy as np
import pandas as pd
from Product.models import Products
from django.db.models import F, FloatField, ExpressionWrapper, Q
from django.views import View
from django.http import JsonResponse
from django.db.models import F, FloatField, ExpressionWrapper
from Product.models import Products

def landing(request):
    return render(request, 'landing/landing.html')

# def get_product_details(request):
#     ids = request.GET.get('ids', '')
#     id_list = [int(i) for i in ids.split(',') if i.isdigit()]
#     print("🔍 요청 받은 ID들:", id_list)

#     products = Products.objects.filter(id__in=id_list)
#     print("✅ 실제 조회된 상품 수:", products.count())

#     data = [{
#         'id': p.id,
#         'title': p.title,
#         'url': p.url,
#         'image_link': p.image_link,
#         'average_rating': p.average_rating,
#         'price_value': p.price_value,
#     } for p in products]

#     return JsonResponse({'products': data})




class ProductRankingView(View):
    def get(self, request, *args, **kwargs):
        mode = kwargs.get('mode', request.GET.get('mode', 'weighted'))
        
        products = Products.objects.all()

        if mode == "weighted":
            products = products.annotate(
                score=ExpressionWrapper(
                    F('popularity_score') / F('price_value'),
                    output_field=FloatField()
                )
            ).order_by("-score")[:10]
            results = [{'id': p.id, 'score': p.score} for p in products]

        elif mode == "popular":
            products = products.order_by("-popularity_score")[:10]
            results = [{'id': p.id, 'popularity_score': p.popularity_score} for p in products]

        elif mode == "sales":
            products = products.order_by("sales_ranks")[:10]
            results = [{'id': p.id, 'sales_ranks': p.sales_ranks} for p in products]

        else:
            return JsonResponse({"error": "Invalid mode"}, status=400)

        return JsonResponse({"results": results})


def search_products(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'products': []})
    
    # 제목, 브랜드, 성분 등에서 검색
    products = Products.objects.filter(
        Q(title__icontains=query) |
        Q(brand__icontains=query) |
        Q(ingredients__icontains=query)
    )[:20]  # 최대 20개 결과만 반환
    
    # 상품 데이터 직렬화
    product_list = []
    for product in products:
        product_list.append({
            'id': product.id,
            'title': product.title,
            'brand': product.brand,
            'image_link': product.image_link,
            'price_value': product.price_value,
            'total_price': product.total_price,
            'average_rating': product.average_rating,
            'total_reviews': product.total_reviews,
            'vegan': product.vegan,
            'supplement_type': product.supplement_type,
            # 필요한 다른 필드들도 추가
        })
    
    return JsonResponse({'products': product_list})


