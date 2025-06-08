from django.db import models

class SurveyResponse(models.Model):
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

    def __str__(self):
        return f"Survey Response {self.id} - {self.created_at}" 