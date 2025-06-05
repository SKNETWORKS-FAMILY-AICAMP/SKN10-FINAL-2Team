from django.urls import path
from . import views

app_name = 'survey'

urlpatterns = [
    path('', views.survey_view, name='survey'),
    path('save/', views.save_survey_results, name='save_survey_results'),
] 