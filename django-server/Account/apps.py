from django.apps import AppConfig



class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Account'

    def ready(self):
        # 시그널 핸들러를 로드합니다.
        import Account.signals