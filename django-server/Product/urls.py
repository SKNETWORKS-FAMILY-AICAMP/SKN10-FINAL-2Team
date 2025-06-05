from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('like/', views.like_product, name='like_product'),
    path('report/', views.nutrition_analysis, name='nutrition_analysis'),
] 