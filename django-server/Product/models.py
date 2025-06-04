from django.db import models

class Supplement(models.Model):
    supplement_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.brand})"
    

class Ingredient(models.Model):
    ingredient_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    risk_info = models.TextField(blank=True)

    def __str__(self):
        return self.name
    

class SupplementIngredient(models.Model):
    id = models.AutoField(primary_key=True)
    supplement = models.ForeignKey(
        Supplement,
        on_delete=models.CASCADE,
        related_name='supplement_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='supplement_ingredients'
    )
    amount_mg = models.FloatField()

    class Meta:
        unique_together = ('supplement', 'ingredient')  # 중복 방지

    def __str__(self):
        return f"{self.supplement.name} - {self.ingredient.name} ({self.amount_mg} mg)"
    


class Interaction(models.Model):
    id = models.AutoField(primary_key=True)
    
    ingredient_1 = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='interactions_as_source'
    )
    ingredient_2 = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='interactions_as_target'
    )
    
    interaction_type = models.CharField(max_length=100)  # 예: '주의', '권장하지 않음', '상승 효과'
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('ingredient_1', 'ingredient_2')

    def __str__(self):
        return f"{self.ingredient_1.name} ↔ {self.ingredient_2.name} ({self.interaction_type})"
    

class Products(models.Model):
    url = models.URLField()
    title = models.CharField(max_length=500)

    safety_info = models.TextField(blank=True)
    labeling = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    directions = models.TextField(blank=True)
    legal_disclaimer = models.TextField(blank=True)

    brand = models.CharField(max_length=255, blank=True)
    flavor = models.CharField(max_length=100, blank=True)
    supplement_type = models.CharField(max_length=100, blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    product_form = models.CharField(max_length=100, blank=True)
    product_weight = models.CharField(max_length=100, blank=True)
    product_dimensions = models.CharField(max_length=100, blank=True)

    average_rating = models.FloatField(null=True, blank=True)
    total_reviews = models.IntegerField(null=True, blank=True)
    rating_distribution = models.TextField(blank=True)

    features = models.TextField(blank=True)
    image_link = models.URLField(blank=True)

    price_value = models.FloatField(null=True, blank=True)
    price_unit = models.CharField(max_length=50, blank=True)
    diet_type = models.CharField(max_length=100, blank=True)
    product_benefits = models.TextField(blank=True)
    age_range_description = models.CharField(max_length=100, blank=True)

    first_available_date = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)
    sales_ranks = models.TextField(blank=True)

    total_price = models.FloatField(null=True, blank=True)

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