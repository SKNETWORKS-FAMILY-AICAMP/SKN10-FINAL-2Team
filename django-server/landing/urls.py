from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),             # 루트 페이지 (홈)
    path('api/top-products/', views.get_top_products, name='top-products'),
]

