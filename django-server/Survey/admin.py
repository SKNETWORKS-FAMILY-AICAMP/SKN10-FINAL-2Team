from django.contrib import admin
from .models import SurveyResponse

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'sedentary', 'gender', 'birth_year')
    list_filter = ('sedentary', 'gender', 'created_at')
    search_fields = ('gender', 'birth_year')
    ordering = ('-created_at',) 