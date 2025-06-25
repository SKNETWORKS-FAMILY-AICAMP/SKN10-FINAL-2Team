from django.urls import path
from . import views

app_name = 'mypage'

urlpatterns = [
    path('', views.mypage_view, name='mypage'),
    path('survey/', views.survey, name='survey'),
    path('submit-survey/', views.submit_survey, name='submit_survey'),
    path('survey-result/', views.survey_result, name='survey_result'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('like/', views.favorite_view, name='like_list'),
    path('like-add/', views.like_add, name='like_add'),
    path('like-delete/', views.like_delete, name='like_delete'),
    path('product/<int:product_id>/nutrients/', views.get_product_nutrients, name='get_product_nutrients'),
    path('product/click/', views.product_click, name='product_click'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('ocr_extract/', views.ocr_extract, name='ocr_extract'),
    path('save-ocr-ingredients/', views.save_ocr_ingredients, name='save_ocr_ingredients'),
    path('api/like/', views.like_api, name='like_api'),
    path('product/purchase/', views.product_purchase, name='product_purchase'),
    path('get-available-nutrients/', views.get_available_nutrients, name='get_available_nutrients'),
]
