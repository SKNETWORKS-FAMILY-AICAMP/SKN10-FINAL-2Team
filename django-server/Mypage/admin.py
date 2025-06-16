from django.contrib import admin
from .models import SurveyResponse, SurveyResult, Supplement, UserHealthReport, Nutrient_daily, UserNutrientIntake, NutrientAnalysis

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'health_status')
    search_fields = ('user__username', 'health_status')
    list_filter = ('created_at', 'health_status')

@admin.register(SurveyResult)
class SurveyResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'health_status')
    search_fields = ('user__username', 'health_status')
    list_filter = ('created_at', 'health_status')

@admin.register(Supplement)
class SupplementAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description', 'benefits')
    list_filter = ('created_at',)

@admin.register(UserHealthReport)
class UserHealthReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'health_score', 'created_at')
    search_fields = ('user__username', 'recommendations')
    list_filter = ('created_at', 'health_score')

@admin.register(Nutrient_daily)
class NutrientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'daily_recommended')
    search_fields = ('name', 'description')
    list_filter = ('unit',)

@admin.register(UserNutrientIntake)
class UserNutrientIntakeAdmin(admin.ModelAdmin):
    list_display = ('user', 'nutrient_name', 'amount', 'date')
    search_fields = ('user__username', 'nutrient__name')
    list_filter = ('date', 'nutrient_name')

@admin.register(NutrientAnalysis)
class NutrientAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'created_at')
    search_fields = ('user__username', 'analysis_result')
    list_filter = ('date', 'created_at') 