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
        ('like', 'Like'),
        ('unlike', 'Unlike'),
    ]

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_logs'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='user_logs'
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.product.title}"
    