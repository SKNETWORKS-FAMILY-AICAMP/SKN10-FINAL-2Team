from django.shortcuts import render
from django.http import JsonResponse

def product_list(request):
    """제품 목록 페이지를 렌더링합니다."""
    return render(request, 'product/product_list.html')

def like_product(request):
    """좋아요 페이지를 렌더링합니다."""
    return render(request, 'product/like/like.html')

def nutrition_analysis(request):
    """영양분석 페이지를 렌더링합니다."""
    return render(request, 'product/report/report.html') 