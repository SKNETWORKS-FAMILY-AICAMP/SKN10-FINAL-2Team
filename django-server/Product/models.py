from django.db import models


class Products(models.Model):
    url = models.URLField()
    title = models.CharField(max_length=500)
    url_images = models.TextField(blank=True)
    safety_info = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    directions = models.TextField(blank=True)
    brand = models.CharField(max_length=255, blank=True)
    flavor = models.CharField(max_length=100, blank=True)
    supplement_type = models.CharField(max_length=100, blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    product_form = models.CharField(max_length=100, blank=True)
    average_rating = models.FloatField(null=True, blank=True)
    total_reviews = models.IntegerField(null=True, blank=True)
    rating_distribution = models.TextField(blank=True)
    image_link = models.URLField(blank=True)
    total_price = models.FloatField(null=True, blank=True)
    price_value = models.FloatField(null=True, blank=True)

    diet_type = models.CharField(max_length=100, blank=True)
    vegan = models.CharField(max_length=30, blank=True)

    first_available_date = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)
    sales_ranks = models.TextField(blank=True)
    popularity_score = models.FloatField(null=True, blank=True)
    nutri = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class Review(models.Model):
    product = models.ForeignKey(
        'Products',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    asin = models.CharField(max_length=20)  # Amazon 제품 코드 (분석용으로 저장)
    date = models.DateField()               # 리뷰 날짜
    stars = models.FloatField()             # 별점 (예: 4.5)
    text = models.TextField()               # 리뷰 본문
    sentiment = models.CharField(max_length=20)  # 예: 'positive', 'neutral', 'negative'

    def __str__(self):
        return f"{self.asin} - {self.stars}★ - {self.sentiment}"