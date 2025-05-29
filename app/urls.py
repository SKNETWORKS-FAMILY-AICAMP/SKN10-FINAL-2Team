from django.urls import path
from . import views

urlpatterns = [
    path('survey/', views.survey_view, name='survey'),
    path('api/save_survey_results/', views.save_survey_results, name='save_survey_results'),
] 