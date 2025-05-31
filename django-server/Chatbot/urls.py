from django.urls import path
from .views import ChatWithNutiAPIView

urlpatterns = [
    path('ChatWithNuti/', ChatWithNutiAPIView.as_view(), name='Chatbot-ChatWithNuti'),
]
