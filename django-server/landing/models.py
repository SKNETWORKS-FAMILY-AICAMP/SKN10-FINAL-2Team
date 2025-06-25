from django.db import models

# Create your models here.

class Products(models.Model):
    title = models.CharField(max_length=200)
    price_value = models.FloatField()
    popularity_score = models.FloatField()
    sales_ranks = models.IntegerField()
