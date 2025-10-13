"""
URL configuration for financetracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from authentication.views import login_view, logout_view, register_view
from budgets.views import budgets_view
from categories.views import categories_view
from landingpage.views import landing_view

urlpatterns = [
    path("", landing_view, name="landing"),
    path("admin/", admin.site.urls),
    path("auth/register/", register_view, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/logout/", logout_view, name="logout"),
    path("dashboard/", include("dashboard.urls")),
    path("transactions/", include("transactions.urls")),
    path("categories/", categories_view, name="categories"),
    path("budgets/", budgets_view, name="budgets"),
    path("goals/", include("goals.urls")),
    path("core/", include("core.urls")),
]
