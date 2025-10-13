from django.urls import path

from . import views

urlpatterns = [
    path("", views.goals_view, name="goals"),
    path("add-money/<int:goal_id>/", views.add_money_to_goal, name="add_money_to_goal"),
    path(
        "quick-add/<int:goal_id>/<int:amount>/",
        views.quick_add_money,
        name="quick_add_money",
    ),
]
