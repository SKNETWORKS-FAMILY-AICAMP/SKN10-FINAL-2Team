from django.contrib import admin
from .models import SurveyResponse

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'height', 'weight', 'sitting_work', 'created_at')
    list_filter = ('sitting_work', 'exercise', 'smoking')
    search_fields = ('id',)
    ordering = ('-created_at',) 