from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import SignupSerializer, FindEmailSerializer, SetNewPasswordWithTokenSerializer, PasswordResetRequestSerializer,LoginSerializer
from django.contrib.auth import get_user_model, authenticate, login
from allauth.account.utils import send_email_confirmation
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
# Create your views here.
def login(request):
    return render(request, 'login/login.html')

User = get_user_model()
class SignupAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [] # AllowAny (회원가입은 인증 없이 가능해야 함)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save() # create() 메서드가 호출됨

        #  이메일 인증 메일 발송
        try:
            send_email_confirmation(request, user)
        except Exception as e:
            # 이메일 전송 실패 시 로그를 남기거나 사용자에게 알림
            print(f"Failed to send email confirmation: {e}")
            # 이메일 전송 실패는 회원가입 실패로 이어지지 않도록 할 수 있음
            # 또는 HTTP 500 에러를 반환하여 사용자에게 알릴 수도 있음
            return Response({
                "message": "회원가입은 완료되었으나, 인증 메일 발송에 실패했습니다. 관리자에게 문의하세요.",
                "user_id": user.id,
                "user_email": user.email,
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "회원가입이 성공적으로 완료되었습니다.",
            "user_id": user.id,
            "user_email": user.email,
        }, status=status.HTTP_201_CREATED)
    


class LoginAPIView(generics.GenericAPIView):
    # We use AllowAny because unauthenticated users need to access this.
    permission_classes = [AllowAny] 
    
    # You might want a separate serializer for login (e.g., just email and password)
    # For simplicity, we can use a basic serializer or manually validate
    serializer_class = LoginSerializer # Or create a dedicated LoginSerializer if needed

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {"detail": "이메일과 비밀번호를 모두 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate user using Django's built-in authenticate function
        # This will use your AUTHENTICATION_BACKENDS from settings.py
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "이메일 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED # Unauthorized status
            )

        # Check if the user is verified
        if not user.is_verified:
            return Response(
                {"detail": "이메일 인증이 필요합니다. 이메일을 확인해주세요."},
                status=status.HTTP_403_FORBIDDEN # Forbidden status
            )
        login(request, user)
        # If authentication successful and user is verified, generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': '로그인 성공!',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.id,
            'user_email': user.email,
        }, status=status.HTTP_200_OK)
    

class FindEmailAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny] # 인증되지 않은 사용자도 접근 가능해야 함
    serializer_class = FindEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Serializer.validate()에서 발생한 ValidationError 처리
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 유효성 검사를 통과했다면 serializer.validated_data에 user 객체가 들어있음
        user = serializer.validated_data['user']
        
        return Response({
            "message": "이메일 주소를 찾았습니다.",
            "email": user.email, # 찾은 이메일 주소 반환
        }, status=status.HTTP_200_OK)
    
class PasswordResetRequestAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer 

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        
        # 토큰 생성
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # 현재 사이트 도메인 가져오기
        current_site = get_current_site(request)
        domain = "127.0.0.1:8000"
        reset_url = "/login/"
        protocol = 'http'

        context = {
            'email': user.email,
            'domain': domain,
            'site_name': current_site.name,
            'uid': uid,
            'token': token,
            'protocol': protocol,
            'reset_link': f"{protocol}://{domain}{reset_url}?action=reset_password&uidb64={uid}&token={token}",
            'user': user, # 필요하다면 사용자 정보도 함께 전달
        }
        text_content = render_to_string('email/password_reset_email.txt', context)
        html_content = render_to_string('email/password_reset_email.html', context)

        email_subject = '비밀번호 재설정 요청'
        to_email = user.email

        email_message = EmailMultiAlternatives(
            email_subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL, # settings.py에 DEFAULT_FROM_EMAIL 설정 필요
            [to_email]
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=False)
        return Response({
            "message": f"비밀번호 재설정 이메일을 {user.email}로 발송했습니다. 이메일을 확인해주세요.",
            "user_email": user.email,
        }, status=status.HTTP_200_OK)


class SetNewPasswordAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny] # 인증되지 않은 사용자도 접근 가능해야 함
    serializer_class = SetNewPasswordWithTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        # 비밀번호 업데이트
        user.set_password(new_password) # Django의 set_password는 비밀번호를 해싱하고 저장합니다.
        user.save()

        return Response({
            "message": "비밀번호가 성공적으로 재설정되었습니다.",
        }, status=status.HTTP_200_OK)


from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout_view(request):
    """
    사용자를 로그아웃시키고 홈(/)으로 리디렉션
    """
    logout(request)  # 세션 삭제
    response = redirect('/')  # 홈 또는 원하는 경로로 리디렉션

    # (선택) localStorage에 저장된 토큰을 삭제하도록 JS 포함된 로그아웃 완료 페이지를 리턴해도 됨
    return response

def login_success_view(request):
    return render(request, 'login/login_success.html')