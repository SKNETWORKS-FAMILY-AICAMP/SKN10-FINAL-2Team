from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.utils import timezone
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) # Superusers are usually active by default

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # If your User model doesn't explicitly have a 'username' field,
        # you might not need to pass it here.
        # However, if 'createsuperuser' command still tries to pass it,
        # ensure your create_superuser signature matches.
        # In this case, we remove it from extra_fields if it's there
        # because the User model doesn't use it as USERNAME_FIELD.
        if 'username' in extra_fields:
            del extra_fields['username'] # This is the key fix if createsuperuser passes it unexpectedly.

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    # username, first_name, last_name, password 등 기본 필드 존재
    email = models.EmailField(unique=True, null=False, blank=False)
    USERNAME_FIELD = 'email'
    birth_date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=20, null=True, blank=True)
    GENDER_CHOICES = [
        ('male', '남성'),
        ('female', '여성'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    REQUIRED_FIELDS = ['birth_date', 'name']
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()
    def __str__(self):
        return self.email

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