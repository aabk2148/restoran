from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from adisyon_modulu.views.auth_views import ElakiLoginView, kvkk_durum_kontrol

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', ElakiLoginView.as_view(), name='login'),
    path('accounts/kvkk-durum/', kvkk_durum_kontrol, name='kvkk_durum_kontrol'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('adisyon_modulu.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
