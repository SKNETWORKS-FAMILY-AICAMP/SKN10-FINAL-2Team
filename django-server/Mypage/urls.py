from django.urls import path
from . import views

app_name = 'mypage'

urlpatterns = [
    path('', views.mypage_view, name='mypage'),
    path('survey/', views.survey, name='survey'),
    path('submit-survey/', views.submit_survey, name='submit_survey'),
    path('survey-result/', views.survey_result, name='survey_result'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('get-nutrient-data/', views.get_nutrient_data, name='get_nutrient_data'),
    path('add-manual-nutrient/', views.add_manual_nutrient_intake, name='add_manual_nutrient_intake'),
    path('analyze-nutrients/', views.analyze_nutrients, name='analyze_nutrients'),
    path('get-nutrient-history/', views.get_nutrient_history, name='get_nutrient_history'),
    path('update-nutrient-intake/', views.update_nutrient_intake, name='update_nutrient_intake'),
    path('delete-nutrient-intake/', views.delete_nutrient_intake, name='delete_nutrient_intake'),
    path('get-nutrients-list/', views.get_nutrients_list, name='get_nutrients_list'),
    path('load-liked-products-nutrients/', views.load_liked_products_nutrients, name='load_liked_products_nutrients'),
    path('like/', views.like_list, name='like_list'),
    path('like-add/', views.like_add, name='like_add'),
    path('like-delete/', views.like_delete, name='like_delete'),
    path('product/<int:product_id>/nutrients/', views.get_product_nutrients, name='get_product_nutrients'),
    path('product/click/', views.product_click, name='product_click'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('ocr_extract/', views.ocr_extract, name='ocr_extract'),
    path('save-ocr-ingredients/', views.save_ocr_ingredients, name='save_ocr_ingredients'),
    path('api/like/', views.like_api, name='like_api'),
    path('product/purchase/', views.product_purchase, name='product_purchase'),
]
