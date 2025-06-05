from django.urls import path
from .views import ChatWithNutiAPIView
from . import views

urlpatterns = [
    path('ChatNuti/', views.chat_view, name='chat_view'),
    path('ChatWithNuti/', ChatWithNutiAPIView.as_view(), name='chat_with_nuti'),
    path('chat-rooms/', views.get_chat_rooms, name='get_chat_rooms'),
    path('chat-rooms/<int:room_id>/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('chat-rooms/<int:room_id>/update/', views.update_chat_room, name='update_chat_room'),
    path('chat-rooms/<int:room_id>/delete/', views.delete_chat_room, name='delete_chat_room'),
]
