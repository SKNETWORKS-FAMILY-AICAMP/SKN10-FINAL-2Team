from django.core.management.base import BaseCommand
from Mypage.models import Nutrient
import csv
import re
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'kdris.csv의 영양소 기준치를 Nutrient 테이블에 등록합니다.'

    def handle(self, *args, **options):
        # base_dir: django-server
        # base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # csv_path = os.path.join(base_dir, 'static', 'csv', 'kdris.csv')
        csv_path = os.path.join(settings.STATICFILES_DIRS[0], 'csv', 'kdris.csv')

        def parse_nutrient_column(col):
            m = re.match(r'(.+?)\((.*?)\/?.*\)', col)
            if m:
                name = m.group(1).strip()
                unit = m.group(2).strip()
            else:
                name = col.strip()
                unit = ''
            return name, unit

        nutrient_dict = {}

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col, value in row.items():
                    name, unit = parse_nutrient_column(col)
                    if not name or name in ['분류', '연령']:
                        continue
                    try:
                        amount = float(value.replace(',', '')) if value else None
                    except:
                        amount = None
                    
                    # Sprawdź czy składnik już istnieje w słowniku
                    current_amount = nutrient_dict.get(name, {}).get('recommended_amount', 0)
                    
                    # Aktualizuj tylko jeśli:
                    # 1. Składnika nie ma w słowniku LUB
                    # 2. Nowa wartość nie jest None i jest większa od obecnej
                    if name not in nutrient_dict or (amount is not None and (current_amount is None or amount > current_amount)):
                        nutrient_dict[name] = {
                            'recommended_amount': amount,
                            'unit': unit,
                        }

        for name, info in nutrient_dict.items():
            nutrient, created = Nutrient.objects.get_or_create(
                name=name,
                defaults={
                    'unit': info['unit'],
                    'daily_recommended': info['recommended_amount'],
                    'description': '',
                    'category': '기준치'
                }
            )
            if not created:
                nutrient.unit = info['unit']
                nutrient.daily_recommended = info['recommended_amount']
                nutrient.save()
            self.stdout.write(f"{'생성' if created else '업데이트'}: {name} ({info['unit']}) - {info['recommended_amount']}")
        self.stdout.write(self.style.SUCCESS(f"총 {len(nutrient_dict)}개 영양소 기준치가 DB에 반영되었습니다."))