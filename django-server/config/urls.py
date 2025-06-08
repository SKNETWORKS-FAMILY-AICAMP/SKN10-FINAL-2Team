from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('mypage/', include('Mypage.urls')),
    path('account/', include('Account.urls')),
    path('favorite/', RedirectView.as_view(url='/mypage/favorite/', permanent=True)),
    path('', RedirectView.as_view(url='/mypage/', permanent=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 