# your_app/adapters.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.shortcuts import render
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Creates or updates a user from a social login.
        This method is called after the user object is created or retrieved
        by allauth's social login process.
        """
        # 1. DefaultSocialAccountAdapter의 save_user 메서드를 호출하여 기본 사용자 저장 로직을 실행합니다.
        #    이것이 User 객체를 생성하거나 기존 User 객체를 가져옵니다.
        user = super().save_user(request, sociallogin, form)

        # 2. Google 로그인 시 사용자의 'is_verified' 필드를 True로 설정합니다.
        #    소셜 로그인은 이미 이메일 인증이 되었다고 간주할 수 있습니다.
        if not user.is_verified: # 이미 True가 아니라면 (불필요한 DB 저장 방지)
            user.is_verified = True
            user.save(update_fields=['is_verified']) # 'is_verified' 필드만 업데이트

        # 3. (선택 사항) Google 계정에서 이름 정보를 가져와 'name' 필드를 업데이트합니다.
        #    이전 답변에서 설명드렸던 name 필드 처리 로직입니다.
        data = sociallogin.account.extra_data
        first_name_from_social = data.get('given_name', '')
        last_name_from_social = data.get('family_name', '')
        
        combined_name = f"{last_name_from_social}{first_name_from_social}".strip()

        if not user.name: # user.name이 비어있을 때만 업데이트 (이미 회원가입으로 이름이 채워졌다면 유지)
            user.name = combined_name
            # user.first_name = first_name_from_social # AbstractUser의 필드도 필요하면 저장
            # user.last_name = last_name_from_social   # AbstractUser의 필드도 필요하면 저장
            user.save(update_fields=['name']) # 변경된 필드만 저장

        return user
    def respond_social_login_success(self, request, sociallogin):
        user = sociallogin.user
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return render(request, 'login/login_success.html', {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })