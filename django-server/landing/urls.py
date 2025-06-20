from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),             # 루트 페이지 (홈)
    # path('Product/details/', views.get_product_details, name='get_product_details'),
    path('get_weighted_scores/', views.get_weighted_scores, name='get_weighted_scores'),
    path('get_popular_products/', views.get_popular_products, name='get_popular_products'),
    path('get_best_selling_products/', views.get_best_selling_products, name='get_best_selling_products'),
    path('Product/search/', views.search_products, name='search_products'),
]