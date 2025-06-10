# Account/signals.py

from allauth.account.signals import email_confirmed
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(email_confirmed)
def update_user_is_verified(sender, request, email_address, **kwargs):
    """
    이메일 인증이 성공적으로 완료되었을 때 호출되는 시그널 핸들러.
    사용자 모델의 is_verified 필드를 True로 업데이트합니다.
    """
    try:
        user = User.objects.get(email=email_address.email)
        if not user.is_verified:
            user.is_verified = True
            user.save()
            print(f"User {user.email} (ID: {user.id})'s is_verified status updated to True.")
    except User.DoesNotExist:
        print(f"Error: User with email {email_address.email} not found for verification.")
    except Exception as e:
        print(f"Error updating is_verified for {email_address.email}: {e}")
from allauth.account.signals import user_logged_in
from rest_framework_simplejwt.tokens import RefreshToken
@receiver(user_logged_in)
def post_login_token(sender, request, user, **kwargs):
    refresh = RefreshToken.for_user(user)
    
    # request에 JWT를 저장해둡니다 (후속 처리에 활용 가능)
    request.jwt_token = {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }