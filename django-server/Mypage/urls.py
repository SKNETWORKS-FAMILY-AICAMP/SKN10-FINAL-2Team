from django.urls import path
from . import views

app_name = 'mypage'

urlpatterns = [
    # 기존 URL 패턴들...
    path('api/like/', views.like_api, name='like_api'),
] 