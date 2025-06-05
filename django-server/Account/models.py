from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    # username, first_name, last_name, password 등 기본 필드 존재
    email = models.EmailField(unique=True, null=False, blank=False)
    birth_date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=20, null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    REQUIRED_FIELDS = ['email', 'birth_date', 'gender']

    def __str__(self):
        return self.username

from django.conf import settings

class EmailVerification(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,   # CustomUser와 연결
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    token = models.CharField(max_length=512)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.token}"
    

class PasswordReset(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_resets'
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.id}"
    
class OAuthAccount(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oauth_accounts'
    )
    provider = models.CharField(max_length=50)  # 예: 'google', 'kakao', 'naver'
    provider_user_id = models.CharField(max_length=255)  # 소셜 서비스의 고유 사용자 ID
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'provider_user_id')  # 같은 provider_user_id 중복 방지

    def __str__(self):
        return f"{self.user.email} - {self.provider}"

class TermsAgreement(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='terms_agreements'
    )
    agreed_at = models.DateTimeField(auto_now_add=True)
    agreed_terms = models.TextField()

    def __str__(self):
        return f"{self.user.email} - {self.agreed_at}"