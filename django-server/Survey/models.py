from django.db import models

class SurveyResponse(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    sedentary = models.CharField(max_length=10)  # yes/no
    gender = models.CharField(max_length=10)     # male/female
    birth_year = models.CharField(max_length=4)

    def __str__(self):
        return f"Survey Response {self.id} - {self.created_at}" 