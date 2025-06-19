from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from Product.models import Products

class Supplement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    benefits = models.TextField()
    dosage = models.CharField(max_length=100)
    precautions = models.TextField()
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Nutrient(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    daily_recommended = models.FloatField()
    unit = models.CharField(max_length=20)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UserNutrientIntake(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nutrient = models.ForeignKey(Nutrient, on_delete=models.CASCADE)
    amount = models.FloatField(default=0.0)  # 입력수량
    unit = models.CharField(max_length=20, default='')  # 단위 (mg, 정 등)
    created_at = models.DateTimeField(auto_now_add=True)  # 등록일

    def __str__(self):
        return f"{self.user.username}'s nutrient intake - {self.nutrient.name}"

class NutrientAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    total_nutrients = models.JSONField(default=dict)
    analysis_result = models.TextField()
    overall_score = models.IntegerField()
    details = models.TextField()
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Nutrient Analyses"

    def __str__(self):
        return f"{self.user.username}'s nutrient analysis - {self.date}"

class SurveyResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    responses = models.JSONField(default=dict)
    answers = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    age_range = models.CharField(max_length=20, null=True, blank=True)  # 연령대
    gender = models.CharField(max_length=10, null=True, blank=True)  # 성별
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
    sleep_hours = models.FloatField(null=True, blank=True)
    exercise_frequency = models.CharField(max_length=20, null=True, blank=True)
    water_intake = models.FloatField(null=True, blank=True)
    health_status = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s survey response - {self.created_at}"

class SurveyResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    answers = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    health_status = models.CharField(max_length=100, null=True, blank=True)
    recommended_supplements = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s survey result - {self.created_at}"

class UserHealthReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    survey_result = models.ForeignKey(SurveyResult, on_delete=models.CASCADE)
    health_score = models.IntegerField()
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s health report - {self.created_at}" 


class Like(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # 같은 유저가 같은 영양제에 중복 좋아요 방지

    def __str__(self):
        return f"{self.user.email} liked {self.product.title}"
    
class Survey(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='surveys'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    responses_json = models.TextField()

    def __str__(self):
        return f"Survey by {self.user.email} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
class Report(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    survey = models.ForeignKey(
        Survey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )

    markdown_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.user.email} ({self.created_at.strftime('%Y-%m-%d')})"
    
class NutrientTag(models.Model):
    id = models.AutoField(primary_key=True)

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='nutrient_tags'
    )

    tag_type = models.CharField(max_length=50)  # 예: '부족', '과다', '적정'
    nutrient_name = models.CharField(max_length=100)  # 예: '비타민C', '철분'
    coverage_percent = models.FloatField()  # 예: 75.0, 120.0 (% 기준)

    def __str__(self):
        return f"{self.nutrient_name} - {self.tag_type} ({self.coverage_percent}%)"
    
class NutrientIntake(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='nutrient_intakes'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='nutrient_intakes'
    )

    nutrient_name = models.CharField(max_length=100)  # 예: '비타민C', '마그네슘'
    amount = models.FloatField()  # 섭취량 (단위: mg, µg 등 기준 명확히 정할 것)
    source = models.CharField(max_length=100)  # 예: 'manual', 'survey', 'auto_tracking'
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.nutrient_name} ({self.amount}) from {self.source}"
    
class OCRResult(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ocr_results'
    )

    image_url = models.CharField(max_length=500)  # S3 또는 외부 URL 등
    parsed_json = models.TextField()  # OCR 결과 JSON 문자열
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OCRResult for {self.user.email} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class UserLog(models.Model):
    ACTION_CHOICES = [
        ('click', 'Click'),
        ('purchase', 'Purchase'),
    ]

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_logs',
        verbose_name='사용자'
    )

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='user_logs',
        verbose_name='제품'
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES,verbose_name='액션')
    timestamp = models.DateTimeField(auto_now_add=True,verbose_name='기록 시각')

    class Meta:
        verbose_name = '사용자 로그'
        verbose_name_plural = '사용자 로그'
        ordering = ['-timestamp'] # Order by latest logs first
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.product.title}"
    
class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        verbose_name = '즐겨찾기'
        verbose_name_plural = '즐겨찾기'

    def __str__(self):
        return f"{self.user.email}의 {self.product.title} 즐겨찾기"
    
class KDRIs(models.Model):
    category = models.CharField(max_length=50)  # 분류 (유아, 남자, 여자, 임신부, 수유부)
    age_range = models.CharField(max_length=50)  # 연령
    energy = models.FloatField()  # 에너지(kcal/일)
    carbohydrates = models.FloatField()  # 탄수화물(g/일)
    dietary_fiber = models.FloatField()  # 식이섬유(g/일)
    linoleic_acid = models.FloatField(default=0.0)  # 리놀레산(g/일)
    alpha_linolenic_acid = models.FloatField(default=0.0)  # 알파-리놀렌산(g/일)
    epa_dha = models.FloatField(default=0.0)  # EPA+DHA(mg/일)
    protein = models.FloatField()  # 단백질(g/일)
    methionine_cysteine = models.FloatField(default=0.0)  # 메티오닌+시스테인(g/일)
    leucine = models.FloatField(default=0.0)  # 류신(g/일)
    isoleucine = models.FloatField(default=0.0)  # 이소류신(g/일)
    valine = models.FloatField(default=0.0)  # 발린(g/일)
    lysine = models.FloatField(default=0.0)  # 라이신(g/일)
    phenylalanine_tyrosine = models.FloatField(default=0.0)  # 페닐알라닌+티로신(g/일)
    threonine = models.FloatField(default=0.0)  # 트레오닌(g/일)
    tryptophan = models.FloatField(default=0.0)  # 트립토판(g/일)
    histidine = models.FloatField(default=0.0)  # 히스티딘(g/일)
    water = models.FloatField(default=0.0)  # 수분(mL/일)
    vitamin_a = models.FloatField()  # 비타민 A(µg RAE/일)
    vitamin_d = models.FloatField()  # 비타민 D(µg/일)
    vitamin_e = models.FloatField()  # 비타민 E(mg ɑ-TE/일)
    vitamin_k = models.FloatField()  # 비타민 K(µg/일)
    vitamin_c = models.FloatField()  # 비타민 C(mg/일)
    thiamin = models.FloatField()  # 티아민(mg/일)
    riboflavin = models.FloatField()  # 리보플라빈(mg/일)
    niacin = models.FloatField()  # 니아신(mg NE/일)
    vitamin_b6 = models.FloatField()  # 비타민 B6(mg/일)
    folate = models.FloatField()  # 엽산(µg DFE/일)
    vitamin_b12 = models.FloatField()  # 비타민B12(µg/일)
    pantothenic_acid = models.FloatField(default=0.0)  # 판토텐산(mg/일)
    biotin = models.FloatField(default=0.0)  # 비오틴(µg/일)
    calcium = models.FloatField()  # 칼슘(mg/일)
    phosphorus = models.FloatField()  # 인(mg/일)
    sodium = models.FloatField()  # 나트륨(mg/일)
    chloride = models.FloatField(default=0.0)  # 염소(mg/일)
    potassium = models.FloatField()  # 칼륨(mg/일)
    magnesium = models.FloatField()  # 마그네슘(mg/일)
    iron = models.FloatField()  # 철(mg/일)
    zinc = models.FloatField()  # 아연(mg/일)
    copper = models.FloatField(default=0.0)  # 구리(µg/일)
    fluoride = models.FloatField(default=0.0)  # 불소(mg/일)
    manganese = models.FloatField(default=0.0)  # 망간(mg/일)
    iodine = models.FloatField(default=0.0)  # 요오드(µg/일)
    selenium = models.FloatField()  # 셀레늄(µg/일)
    molybdenum = models.FloatField(default=0.0)  # 몰리브덴(µg/일)
    chromium = models.FloatField(default=0.0)  # 크롬(µg/일)

    class Meta:
        verbose_name_plural = "KDRIs"
        unique_together = ('category', 'age_range')

    def __str__(self):
        return f"{self.category} - {self.age_range}"
    