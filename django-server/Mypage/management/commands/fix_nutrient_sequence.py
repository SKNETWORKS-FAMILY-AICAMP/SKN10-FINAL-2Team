from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix Nutrient table sequence to prevent ID conflicts'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                # 현재 최대 ID 확인
                cursor.execute('SELECT MAX(id) FROM "Mypage_nutrient";')
                max_id = cursor.fetchone()[0]
                
                if max_id is None:
                    max_id = 0
                
                self.stdout.write(f"Current max ID: {max_id}")
                
                # 시퀀스 재설정
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence('\"Mypage_nutrient\"', 'id'), %s);",
                    [max_id + 1]
                )
                
                # 재설정된 시퀀스 값 확인
                cursor.execute("SELECT currval(pg_get_serial_sequence('\"Mypage_nutrient\"', 'id'));")
                current_val = cursor.fetchone()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully reset sequence to {current_val}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error fixing sequence: {str(e)}')
            ) 