from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from GameHub import settings
from users.views import reg

urlpatterns = [
    path("register", reg, name="register"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
