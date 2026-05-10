from django.urls import path

from igonews import views

urlpatterns = [
    path("", views.article_list, name="igonews_list"),
    path("<int:pk>/", views.article_detail, name="igonews_detail"),
]
