from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from GameHub import settings
from game.views import game_news, game_detail

urlpatterns = [
    path("", game_news),
    path("gamedetail/<int:game_id>/", game_detail),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
