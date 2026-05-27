from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf.urls.static import static
from GameHub import settings
from users.views import reg, user_login

urlpatterns = [
    path("register", reg, name="register"),
    path("login", user_login, name="login"),
    path("logout", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
