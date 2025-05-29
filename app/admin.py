from django.contrib import admin
from .models import SurveyResult

@admin.register(SurveyResult)
class SurveyResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'weight', 'height', 'created_at')
    list_filter = ('created_at', 'sedentary_work', 'regular_exercise')
    search_fields = ('user__username',)
    date_hierarchy = 'created_at' 