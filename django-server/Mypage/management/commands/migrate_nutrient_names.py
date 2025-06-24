from django.core.management.base import BaseCommand
from Mypage.models import Nutrient
import re

class Command(BaseCommand):
    help = 'Nutrient name에서 괄호(단위)를 분리하여 name/unit 필드로 정리합니다.'

    def handle(self, *args, **options):
        nutrients = Nutrient.objects.all()
        updated = 0
        for nutrient in nutrients:
            m = re.match(r'(.+?)\((.*?)\/?.*\)', nutrient.name)
            if m:
                new_name = m.group(1).strip()
                new_unit = m.group(2).strip()
                if nutrient.name != new_name or nutrient.unit != new_unit:
                    self.stdout.write(f'변경: {nutrient.name} → {new_name} ({new_unit})')
                    nutrient.name = new_name
                    nutrient.unit = new_unit
                    nutrient.save()
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'총 {updated}개 영양소 name/unit 정리 완료!')) 