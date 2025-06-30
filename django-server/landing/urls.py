from django.urls import path
from . import views
from .views import ProductRankingView

urlpatterns = [
    path('', views.landing, name='landing'),             # 루트 페이지 (홈)
    # path('Product/details/', views.get_product_details, name='get_product_details'),
    path('Product/search/', views.search_products, name='search_products'),
    path('product_rankings/', ProductRankingView.as_view(), name='product_rankings'),
    path('get_weighted_scores/', ProductRankingView.as_view(), {'mode': 'weighted'}, name='get_weighted_scores'),
    path('get_popular_products/', ProductRankingView.as_view(), {'mode': 'popular'}, name='get_popular_products'),
    path('get_best_selling_products/', ProductRankingView.as_view(), {'mode': 'sales'}, name='get_best_selling_products'),
]