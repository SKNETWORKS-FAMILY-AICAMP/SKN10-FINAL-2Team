from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('Account.urls')),
    path('chatbot/', include('Chatbot.urls')),
    path('mypage/', include('Mypage.urls')),
    path('product/', include('Product.urls')),
    path('survey/', include('Survey.urls')),
] 