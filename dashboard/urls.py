from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path(
        "category-pie-chart-data/",
        views.category_pie_chart_data,
        name="category_pie_chart_data",
    ),
    path(
        "spending-trend-chart-data/",
        views.spending_trend_chart_data,
        name="spending_trend_chart_data",
    ),
]
