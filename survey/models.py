from django.db import models

class SurveyResponse(models.Model):
    SEDENTARY_CHOICES = [
        ('yes', '예'),
        ('no', '아니오'),
    ]

    GENDER_CHOICES = [
        ('male', '남성'),
        ('female', '여성'),
    ]

    sedentary = models.CharField(
        max_length=3,
        choices=SEDENTARY_CHOICES,
        verbose_name='주로 앉아서 하는 일'
    )
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICES,
        verbose_name='성별'
    )
    birth_year = models.IntegerField(
        verbose_name='출생년도'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='작성일시'
    )

    class Meta:
        verbose_name = '설문 응답'
        verbose_name_plural = '설문 응답'
        ordering = ['-created_at']

    def __str__(self):
        return f'설문 응답 ({self.created_at.strftime("%Y-%m-%d %H:%M")})' 