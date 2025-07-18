from django.contrib import admin
from .models import SurveyResponse, SurveyResult, Supplement, UserHealthReport, Nutrient, UserNutrientIntake, NutrientAnalysis, KDRIs

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

@admin.register(Nutrient)
class NutrientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'daily_recommended')
    search_fields = ('name', 'description')
    list_filter = ('unit',)

@admin.register(UserNutrientIntake)
class UserNutrientIntakeAdmin(admin.ModelAdmin):
    list_display = ('user', 'nutrient', 'amount', 'unit', 'created_at')
    list_filter = ('nutrient',)

@admin.register(NutrientAnalysis)
class NutrientAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'created_at')
    search_fields = ('user__username', 'analysis_result')
    list_filter = ('date', 'created_at')

@admin.register(KDRIs)
class KDRIsAdmin(admin.ModelAdmin):
    list_display = ('category', 'age_range', 'energy', 'protein', 'vitamin_c', 'calcium', 'iron')
    list_filter = ('category', 'age_range')
    search_fields = ('category', 'age_range') 