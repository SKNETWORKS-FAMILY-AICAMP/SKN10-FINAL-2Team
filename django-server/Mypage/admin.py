from django.contrib import admin
from .models import SurveyResult, SurveyResponse, Supplement, UserHealthReport, NutrientAnalysis

@admin.register(SurveyResult)
class SurveyResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'health_status', 'created_at', 'updated_at')
    list_filter = ('health_status', 'created_at')
    search_fields = ('user__username', 'health_status')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)

@admin.register(Supplement)
class SupplementAdmin(admin.ModelAdmin):
    list_display = ('name', 'dosage', 'created_at')
    search_fields = ('name', 'description', 'benefits')
    list_filter = ('created_at',)

@admin.register(UserHealthReport)
class UserHealthReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'health_score', 'created_at')
    list_filter = ('health_score', 'created_at')
    search_fields = ('user__username', 'recommendations')

@admin.register(NutrientAnalysis)
class NutrientAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'overall_score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    readonly_fields = ('created_at',) 