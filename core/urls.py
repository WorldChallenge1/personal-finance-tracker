from django.urls import path

from . import views

urlpatterns = [
    path("change-theme/", views.change_theme, name="change_theme"),
]
