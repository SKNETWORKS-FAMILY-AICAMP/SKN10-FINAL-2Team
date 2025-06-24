from django.urls import path
from . import views
from .views import ChatWithNutiAPIView

app_name = 'chatbot'

urlpatterns = [
    path('ChatWithNuti/', ChatWithNutiAPIView.as_view(), name='chat'),
    path('chat-rooms/', views.get_chat_rooms, name='get_chat_rooms'),
    path('chat-rooms/<int:room_id>/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('chat-rooms/<int:room_id>/update/', views.update_chat_room, name='update_chat_room'),
    path('chat-rooms/<int:room_id>/delete/', views.delete_chat_room, name='delete_chat_room'),
]
