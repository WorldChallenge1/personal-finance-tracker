import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.constants import COLOR_OPTIONS, GOALS_ICON_OPTIONS
from goals.models import Goal, GoalHistory

logger = logging.getLogger(__name__)


class GoalData:
    def __init__(
        self,
        id,
        name,
        description,
        target_amount,
        current_amount,
        target_date: date,
        icon,
        color,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.target_amount = target_amount
        self.current_amount = current_amount
        self.target_date = target_date
        self.icon = icon
        self.color = color

    @property
    def percentage_achieved(self):
        if self.target_amount == 0:
            return 0
        return min(round((self.current_amount / self.target_amount) * 100), 100)

    @property
    def time_left(self):
        today = date.today()
        days_left = (self.target_date - today).days
        return days_left

    def __str__(self):
        return f"GoalData(name={self.name}, target_amount={self.target_amount}, current_amount={self.current_amount}, target_date={self.target_date}, icon={self.icon}, color={self.color}, percentage_achieved={self.percentage_achieved}, time_left={self.time_left})"


def get_goals_data(user: AbstractBaseUser | AnonymousUser) -> list[GoalData]:
    """Fetches and returns goal data for the given user.

    Args:
        user (AbstractBaseUser | AnonymousUser): The user whose goal data is to be fetched.

    Returns:
        list[GoalData]: A list containing all goals for a specific user, including names, descriptions, target amounts, current amounts, target dates, icons, and colors.
    """
    goals = Goal.objects.filter(user=user).values(
        "id",
        "name",
        "description",
        "target_amount",
        "current_amount",
        "target_date",
        "icon",
        "color",
    )

    return [GoalData(**goal) for goal in goals]


def get_goals_chart_data(user: AbstractBaseUser | AnonymousUser) -> dict:
    """Fetches goal history data for chart visualization.

    Args:
        user: The user whose goal history is to be fetched.

    Returns:
        dict: Contains labels (months) and datasets (goal progress over time).
    """
    # Get current date and calculate 12 months back
    now = datetime.now()
    twelve_months_ago = now - relativedelta(months=11)

    # Generate month labels
    months = []
    month_dates = []
    for i in range(12):
        month_date = twelve_months_ago + relativedelta(months=i)
        months.append(month_date.strftime("%b"))
        month_dates.append(month_date)

    # Get all goals for the user
    goals = Goal.objects.filter(user=user)

    datasets = []
    colors = {
        "primary": "#3498db",
        "success": "#27ae60",
        "danger": "#e74c3c",
        "warning": "#f39c12",
        "info": "#17a2b8",
        "secondary": "#6c757d",
    }

    for goal in goals:
        # Get history for this goal
        history = GoalHistory.objects.filter(
            goal=goal, date__gte=twelve_months_ago
        ).order_by("date")

        # Create a dict to store amounts by month
        monthly_amounts = defaultdict(float)

        # Process history entries
        for entry in history:
            month_key = entry.date.strftime("%Y-%m")
            # Keep only the latest amount for each month
            if entry.amount > monthly_amounts[month_key]:
                monthly_amounts[month_key] = float(entry.amount)

        # Build data array with cumulative approach
        data = []
        last_amount = 0

        for month_date in month_dates:
            month_key = month_date.strftime("%Y-%m")
            if month_key in monthly_amounts:
                last_amount = monthly_amounts[month_key]
            data.append(last_amount)

        # Get color for the goal
        color_code = colors.get(goal.color, colors["primary"])

        datasets.append(
            {
                "label": goal.name,
                "data": data,
                "borderColor": color_code,
                "backgroundColor": f"rgba{tuple(list(int(color_code.lstrip('#')[i : i + 2], 16) for i in (0, 2, 4)) + [0.1])}",
                "tension": 0.4,
            }
        )

    return {"labels": months, "datasets": datasets}


# Create your views here.
def goals_view(request: WSGIRequest) -> HttpResponse:
    context: dict = {
        "color_options": COLOR_OPTIONS,
        "icon_options": GOALS_ICON_OPTIONS,
    }

    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "delete":
            # Handle delete goal
            goal_id = request.POST.get("goal_id")
            try:
                goal = get_object_or_404(Goal, id=goal_id, user=request.user)
                goal.delete()
                context["messages"] = [
                    {
                        "message": "Goal deleted successfully.",
                        "tags": "success",
                    }
                ]
            except Goal.DoesNotExist:
                context["messages"] = [
                    {
                        "message": "Goal not found or you don't have permission to delete it.",
                        "tags": "danger",
                    }
                ]
            except Exception as e:
                logger.error(f"Error deleting goal: {e}")
                context["messages"] = [
                    {
                        "message": "An error occurred while deleting the goal.",
                        "tags": "danger",
                    }
                ]

        elif action == "edit":
            # Handle edit goal
            goal_id = request.POST.get("goal_id")
            goal_name = request.POST.get("goal_name", "")
            goal_description = request.POST.get("goal_description", "")
            goal_amount = request.POST.get("goal_amount", "")
            goal_current_amount = request.POST.get("goal_current_amount", "")
            goal_target_date = request.POST.get("goal_target_date", "")
            goal_icon = request.POST.get("goal_icon", "")
            goal_color = request.POST.get("goal_color", "")

            required_fields = [goal_name, goal_amount, goal_target_date]

            if any(not field for field in required_fields):
                context["messages"] = [
                    {
                        "message": "Goal name, target amount, and target date are required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    goal = get_object_or_404(Goal, id=goal_id, user=request.user)

                    # Update goal
                    goal.name = goal_name
                    goal.description = goal_description
                    goal.target_amount = goal_amount
                    if goal_current_amount:
                        goal.current_amount = goal_current_amount
                    goal.target_date = goal_target_date
                    goal.icon = goal_icon
                    goal.color = goal_color
                    goal.save()

                    context["messages"] = [
                        {
                            "message": "Goal updated successfully.",
                            "tags": "success",
                        }
                    ]
                except Goal.DoesNotExist:
                    context["messages"] = [
                        {
                            "message": "Goal not found or you don't have permission to edit it.",
                            "tags": "danger",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error updating goal: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while updating the goal.",
                            "tags": "danger",
                        }
                    ]

        else:  # Default to add goal
            goal_name = request.POST.get("goal_name", "")
            goal_description = request.POST.get("goal_description", "")
            goal_amount = request.POST.get("goal_amount", "")
            goal_current_amount = request.POST.get("goal_current_amount", "0")
            goal_target_date = request.POST.get("goal_target_date", "")
            goal_icon = request.POST.get("goal_icon", "")
            goal_color = request.POST.get("goal_color", "")

            required_fields = [goal_name, goal_amount, goal_target_date]

            if any(not field for field in required_fields):
                context["messages"] = [
                    {
                        "message": "Please fill in all required fields.",
                        "tags": "danger",
                    }
                ]
            else:
                if goal_current_amount == "":
                    goal_current_amount = 0

                # Create and save the new goal
                goal = Goal(
                    name=goal_name,
                    description=goal_description,
                    target_amount=goal_amount,
                    current_amount=goal_current_amount,
                    target_date=goal_target_date,
                    icon=goal_icon,
                    color=goal_color,
                    user=request.user,
                )

                try:
                    goal.save()
                    context["messages"] = [
                        {
                            "message": "Goal created successfully.",
                            "tags": "success",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error creating goal: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while creating the goal.",
                            "tags": "danger",
                        }
                    ]

    # Get goals data
    goals_data = get_goals_data(request.user)
    total_goals_amount = sum([goal.target_amount for goal in goals_data])
    total_saved = sum([goal.current_amount for goal in goals_data])
    average_progress = (
        sum([goal.percentage_achieved for goal in goals_data]) / len(goals_data)
        if len(goals_data) > 0
        else 0
    )
    total_goals = len(goals_data)
    chart_data = get_goals_chart_data(request.user)

    context.update(
        {
            "goals_data": goals_data,
            "total_goals_amount": total_goals_amount,
            "total_saved": total_saved,
            "average_progress": average_progress,
            "total_goals": total_goals,
            "chart_data": chart_data,
        }
    )

    return render(
        request,
        "goals.html",
        context,
    )


@require_http_methods(["POST"])
def add_money_to_goal(request: WSGIRequest, goal_id: int) -> HttpResponse:
    """Add money to a specific goal.

    Args:
        request: The HTTP request object.
        goal_id: The ID of the goal to add money to.

    Returns:
        HttpResponse: Redirect back to goals page with success/error message.
    """
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)

    try:
        amount_to_add = request.POST.get("amount")

        if not amount_to_add:
            return JsonResponse(
                {"success": False, "message": "Amount is required."}, status=400
            )

        amount_to_add = Decimal(amount_to_add)

        if amount_to_add <= 0:
            return JsonResponse(
                {"success": False, "message": "Amount must be greater than zero."},
                status=400,
            )

        # Update the goal's current amount
        goal.current_amount += amount_to_add

        # Check if goal is achieved
        if goal.current_amount >= goal.target_amount and not goal.achieved:
            goal.achieved = True
            goal.achieved_at = datetime.now()

        goal.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully added ${amount_to_add} to {goal.name}!",
                "new_amount": float(goal.current_amount),
                "target_amount": float(goal.target_amount),
                "percentage": min(
                    round((goal.current_amount / goal.target_amount) * 100), 100
                ),
                "achieved": goal.achieved,
            }
        )

    except ValueError:
        return JsonResponse(
            {"success": False, "message": "Invalid amount format."}, status=400
        )
    except Exception as e:
        logger.error(f"Error adding money to goal {goal_id}: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": "An error occurred while adding money to the goal.",
            },
            status=500,
        )


@require_http_methods(["POST"])
def quick_add_money(request: WSGIRequest, goal_id: int, amount: int) -> HttpResponse:
    """Quick add a predefined amount to a goal.

    Args:
        request: The HTTP request object.
        goal_id: The ID of the goal.
        amount: The predefined amount to add.

    Returns:
        HttpResponse: Redirect back to goals page.
    """
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)

    try:
        amount_decimal = Decimal(str(amount))

        if amount_decimal <= 0:
            return redirect("goals")

        goal.current_amount += amount_decimal

        # Check if goal is achieved
        if goal.current_amount >= goal.target_amount and not goal.achieved:
            goal.achieved = True
            goal.achieved_at = datetime.now()

        goal.save()

    except Exception as e:
        logger.error(f"Error quick adding money to goal {goal_id}: {e}")

    return redirect("goals")
