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
    overall_score = models.IntegerField()
    details = models.TextField()
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s nutrient analysis - {self.created_at}"

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
    health_status = models.CharField(max_length=100, default='')
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

from django.db import models
from django.conf import settings
from Product.models import Products

class Like(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # 같은 유저가 같은 영양제에 중복 좋아요 방지

    def __str__(self):
        return f"{self.user.email} liked {self.product.title}"
    
class Survey(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='surveys'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    responses_json = models.TextField()

    def __str__(self):
        return f"Survey by {self.user.email} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
class Report(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    survey = models.ForeignKey(
        Survey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )

    markdown_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.user.email} ({self.created_at.strftime('%Y-%m-%d')})"
    
class NutrientTag(models.Model):
    id = models.AutoField(primary_key=True)

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='nutrient_tags'
    )

    tag_type = models.CharField(max_length=50)  # 예: '부족', '과다', '적정'
    nutrient_name = models.CharField(max_length=100)  # 예: '비타민C', '철분'
    coverage_percent = models.FloatField()  # 예: 75.0, 120.0 (% 기준)

    def __str__(self):
        return f"{self.nutrient_name} - {self.tag_type} ({self.coverage_percent}%)"
    
class NutrientIntake(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='nutrient_intakes'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='nutrient_intakes'
    )

    nutrient_name = models.CharField(max_length=100)  # 예: '비타민C', '마그네슘'
    amount = models.FloatField()  # 섭취량 (단위: mg, µg 등 기준 명확히 정할 것)
    source = models.CharField(max_length=100)  # 예: 'manual', 'survey', 'auto_tracking'
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.nutrient_name} ({self.amount}) from {self.source}"
    
class OCRResult(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ocr_results'
    )

    image_url = models.CharField(max_length=500)  # S3 또는 외부 URL 등
    parsed_json = models.TextField()  # OCR 결과 JSON 문자열
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OCRResult for {self.user.email} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
from Product.models import Products    
class UserLog(models.Model):
    ACTION_CHOICES = [
        ('click', 'Click'),
        ('purchase', 'Purchase'),
    ]

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_logs',
        verbose_name='사용자'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='user_logs',
        verbose_name='제품'
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES,verbose_name='액션')
    timestamp = models.DateTimeField(auto_now_add=True,verbose_name='기록 시각')

    class Meta:
        verbose_name = '사용자 로그'
        verbose_name_plural = '사용자 로그'
        ordering = ['-timestamp'] # Order by latest logs first
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.product.title}"
    