
from django.urls import path
from .views import login, SignupAPIView,LoginAPIView,FindEmailAPIView,PasswordResetRequestAPIView,SetNewPasswordAPIView
from .views import custom_logout_view,login_success_view

app_name = 'account'
urlpatterns = [
    path('',login),
    path('signup/', SignupAPIView.as_view(), name='signup_api'),
    path('login/', LoginAPIView.as_view(), name='login_api'),
    path('find-email/', FindEmailAPIView.as_view(), name='find_email_api'),
    path('password-reset-request/', PasswordResetRequestAPIView.as_view(), name='password_reset_request_api'),
    path('set-new-password/', SetNewPasswordAPIView.as_view(), name='set_new_password_api'), 
    path('logout/', custom_logout_view, name='custom_logout'),
    path('success/', login_success_view, name='login_success'),
]
