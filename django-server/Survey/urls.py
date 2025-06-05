from django.urls import path
from . import views

app_name = 'survey'

urlpatterns = [
    path('', views.survey_view, name='survey'),
    path('mypage/', views.mypage_view, name='mypage'),
    path('favorite/', views.favorite_view, name='favorite'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('save/', views.save_survey, name='save_survey'),
] 