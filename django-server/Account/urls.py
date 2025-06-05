
from django.urls import path
from .views import login, SignupAPIView,LoginAPIView,FindEmailAPIView
urlpatterns = [
    path('',login),
    path('signup/', SignupAPIView.as_view(), name='signup_api'),
    path('login/', LoginAPIView.as_view(), name='login_api'),
    path('find-email/', FindEmailAPIView.as_view(), name='find_email_api'),
]
