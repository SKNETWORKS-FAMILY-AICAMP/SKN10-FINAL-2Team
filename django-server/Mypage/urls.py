from django.urls import path
from . import views

app_name = 'mypage'

urlpatterns = [
    path('', views.mypage_view, name='mypage'),
    path('survey/', views.survey_view, name='survey'),
    path('save-survey/', views.save_survey, name='save_survey'),
    path('survey-result/', views.survey_result, name='survey_result'),
    path('favorite/', views.favorite_view, name='favorite'),
    path('toggle-like/', views.toggle_like, name='toggle_like'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('get_favorite_products/', views.get_favorite_products, name='get_favorite_products'),
    path('get_nutrient_data/', views.get_nutrient_data, name='get_nutrient_data'),
    path('ocr_extract/', views.ocr_extract, name='ocr_extract'),
] 