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
