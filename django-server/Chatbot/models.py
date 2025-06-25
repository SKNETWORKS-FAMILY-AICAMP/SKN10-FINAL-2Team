from django.db import models
from django.conf import settings
from Product.models import Products

class RecommendationLog(models.Model):
    id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendation_logs'
    )
    
    recommended_product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='recommendation_logs'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()

    def __str__(self):
        return f"{self.user.email} → {self.recommended_product.title} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
    
class LLMRequest(models.Model):
    id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='llm_requests'
    )
    
    input_prompt = models.TextField()
    llm_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    model = models.CharField(max_length=100)  # 예: 'gpt-4', 'claude', 'koalpaca'
    status = models.CharField(max_length=50)  # 예: 'success', 'error', 'timeout'

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.model} - {self.status}"

class ChatRooms(models.Model):
    id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_rooms'
    )
    
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} (User: {self.user.email})"

class ChatMessages(models.Model):
    id = models.AutoField(primary_key=True)
    
    chat_room = models.ForeignKey(
        ChatRooms,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    sender_type = models.CharField(max_length=20)  # 예: 'user', 'assistant'
    message = models.TextField()
    product_ids = models.JSONField(blank=True, null=True)  # 추천된 상품 ID 리스트를 저장
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.sender_type}] {self.message[:30]}..."
    
class ChatMetadata(models.Model):
    id = models.AutoField(primary_key=True)
    
    chat_room = models.OneToOneField(
        ChatRooms,
        on_delete=models.CASCADE,
        related_name='metadata'
    )
    
    health_conditions = models.TextField(blank=True)
    used_products = models.TextField(blank=True)

    def __str__(self):
        return f"Metadata for ChatRoom {self.chat_room.id}"
    

class RecommendationStat(models.Model):
    id = models.AutoField(primary_key=True)

    product = models.OneToOneField(
        Products,
        on_delete=models.CASCADE,
        related_name='recommendation_stat'
    )

    liked_count = models.PositiveIntegerField(default=0)
    recommended_count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.title} - {self.recommended_count} recommendations, {self.liked_count} likes"
class ModelVersion(models.Model):
    id = models.AutoField(primary_key=True)
    
    model_name = models.CharField(max_length=100)  # 예: 'gpt-4', 'custom-recommender'
    deployed_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=50)  # 예: 'v1.0.3', '2025-06-01-release'

    def __str__(self):
        return f"{self.model_name} ({self.version})"



class NutritionDailyRec(models.Model):
    CATEGORY_CHOICES = [
        ('남자', '남자'),
        ('여자', '여자'),
    ]

    id = models.AutoField(primary_key=True)
    sex = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    age_range = models.CharField(max_length=20, verbose_name='연령대')
    nutrient = models.CharField(max_length=50)
    daily = models.FloatField()
    
    def __str__(self):
        return f"{self.sex} {self.age} - {self.nutrient}: {self.daily}"

class ChatbotRecommendation(models.Model):
    id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chatbot_recommendations'
    )
    
    recommended_products = models.JSONField()  # 추천된 상품 정보를 JSON으로 저장
    recommendation_reason = models.TextField()  # 추천 이유
    health_recommendations = models.JSONField(default=list)  # 건강 추천사항을 JSON 배열로 저장
    user_query = models.TextField()  # 사용자 질문
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # 활성 상태 (최신 추천만 표시)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"