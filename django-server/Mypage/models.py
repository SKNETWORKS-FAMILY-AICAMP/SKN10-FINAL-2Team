from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Supplement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    benefits = models.TextField()
    dosage = models.CharField(max_length=100)
    precautions = models.TextField()
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Nutrient(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    daily_recommended = models.FloatField()
    unit = models.CharField(max_length=20)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UserNutrientIntake(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nutrient = models.ForeignKey(Nutrient, on_delete=models.CASCADE)
    amount = models.FloatField()
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username}'s {self.nutrient.name} intake on {self.date}"

class NutrientAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    total_nutrients = models.JSONField(default=dict)
    analysis_result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Nutrient Analyses"

    def __str__(self):
        return f"{self.user.username}'s nutrient analysis - {self.date}"

class SurveyResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    responses = models.JSONField(default=dict)
    answers = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    sitting_work = models.CharField(max_length=10, null=True, blank=True)
    indoor_daytime = models.CharField(max_length=10, null=True, blank=True)
    exercise = models.CharField(max_length=10, null=True, blank=True)
    smoking = models.CharField(max_length=10, null=True, blank=True)
    drinking = models.CharField(max_length=10, null=True, blank=True)
    fatigue = models.CharField(max_length=10, null=True, blank=True)
    sleep_well = models.CharField(max_length=10, null=True, blank=True)
    still_tired = models.CharField(max_length=10, null=True, blank=True)
    sleep_hours = models.FloatField(null=True, blank=True)
    exercise_frequency = models.CharField(max_length=20, null=True, blank=True)
    water_intake = models.FloatField(null=True, blank=True)
    health_status = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s survey response - {self.created_at}"

class SurveyResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    answers = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    health_status = models.CharField(max_length=100, null=True, blank=True)
    recommended_supplements = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s survey result - {self.created_at}"

class UserHealthReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    survey_result = models.ForeignKey(SurveyResult, on_delete=models.CASCADE)
    health_score = models.IntegerField()
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s health report - {self.created_at}" 