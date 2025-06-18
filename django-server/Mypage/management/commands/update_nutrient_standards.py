from django.core.management.base import BaseCommand
from django.conf import settings
import json
import os
from Mypage.models import Nutrient

class Command(BaseCommand):
    help = '기존 영양소의 권장량을 기준치 파일에서 업데이트합니다.'

    def handle(self, *args, **options):
        try:
            # 영양소 기준치 파일 로드
            json_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
            
            with open(json_path, 'r', encoding='utf-8') as f:
                nutrient_standards = json.load(f)
            
            self.stdout.write(f"기준치 파일 로드 완료: {len(nutrient_standards)}개 영양소")
            
            # 모든 영양소 가져오기
            nutrients = Nutrient.objects.all()
            updated_count = 0
            
            for nutrient in nutrients:
                if nutrient.name in nutrient_standards:
                    standard = nutrient_standards[nutrient.name]
                    
                    # 권장량 업데이트
                    nutrient.daily_recommended = standard.get('recommended_amount', 100)
                    nutrient.unit = standard.get('unit', 'mg')
                    nutrient.description = standard.get('description', '')
                    nutrient.save()
                    
                    updated_count += 1
                    self.stdout.write(f"업데이트: {nutrient.name} - 권장량: {nutrient.daily_recommended} {nutrient.unit}")
                else:
                    self.stdout.write(f"기준치 없음: {nutrient.name}")
            
            self.stdout.write(
                self.style.SUCCESS(f'성공적으로 {updated_count}개 영양소의 권장량을 업데이트했습니다.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'오류 발생: {str(e)}')
            ) 