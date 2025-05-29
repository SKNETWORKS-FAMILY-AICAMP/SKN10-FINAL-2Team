from django.db import models
from django.contrib.auth.models import User

class SurveyResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    weight = models.FloatField(verbose_name="몸무게")
    height = models.FloatField(verbose_name="키")
    sedentary_work = models.BooleanField(verbose_name="주로 앉아서 하는 일")
    indoor_during_day = models.BooleanField(verbose_name="낮에 실내에 주로 있음")
    regular_exercise = models.BooleanField(verbose_name="규칙적 운동")
    high_stress = models.BooleanField(verbose_name="스트레스 많음")
    no_sweat = models.BooleanField(verbose_name="땀이 잘 안남")
    dizziness = models.BooleanField(verbose_name="어지러움")
    skin_care_goal = models.BooleanField(verbose_name="피부보습 목표")
    allergies = models.JSONField(verbose_name="알레르기", default=list)
    medications = models.JSONField(verbose_name="복용 중인 약", default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "설문 결과"
        verbose_name_plural = "설문 결과들"

    def __str__(self):
        return f'설문 결과 {self.id}' 