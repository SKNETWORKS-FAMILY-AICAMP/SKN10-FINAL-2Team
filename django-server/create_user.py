import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

# Tworzenie nowego użytkownika
username = 'test'
email = 'test@example.com'
password = 'test1234'

if not User.objects.filter(username=username).exists():
    user = User.objects.create_user(username=username, email=email, password=password)
    print(f'Utworzono użytkownika: {username}')
else:
    print(f'Użytkownik {username} już istnieje') 