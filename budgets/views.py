import logging

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from budgets.models import Budget
from categories.models import Category
from core.utils import get_current_month_date_range

logger = logging.getLogger(__name__)


class BudgetData:
    def __init__(self, name, icon, color, spent, amount):
        self.name = name
        self.icon = icon
        self.color = color
        self.spent = spent if spent is not None else 0
        self.amount = amount

    @property
    def percentage_used(self):
        """Calculate the percentage of budget used."""
        if self.amount == 0:
            return 0
        return min(round((self.spent / self.amount) * 100), 100)

    @property
    def remaining(self):
        """Calculate remaining budget amount."""
        return self.amount - self.spent

    @property
    def is_over_budget(self):
        """Check if spending exceeds budget."""
        return self.spent > self.amount

    @property
    def status_color(self):
        """Return appropriate color based on budget usage."""
        if self.is_over_budget:
            return "danger"
        elif self.percentage_used >= 80:
            return "warning"
        elif self.percentage_used >= 60:
            return "success"
        else:
            return "primary"

    def __str__(self) -> str:
        return f"BudgetData(name={self.name}, spent={self.spent}, amount={self.amount}, percentage_used={self.percentage_used}, remaining={self.remaining}, is_over_budget={self.is_over_budget}, status_color={self.status_color})"


def get_butgets_data(user: AbstractBaseUser | AnonymousUser) -> list[BudgetData]:
    """Fetches and returns budget data for the given user.

    Args:
        user (AbstractBaseUser | AnonymousUser): The user whose budget data is to be fetched.

    Returns:
        list[BudgetData]: A list containing all budgets for a specific user, including names, amounts, and spent amounts.
    """
    start_date, end_date = get_current_month_date_range()
    budgets = (
        Budget.objects.filter(user=user)
        .select_related("category")
        .annotate(
            name=F("category__name"),
            icon=F("category__icon"),
            color=F("category__color"),
            spent=Sum(
                "category__transactions__amount",
                filter=Q(
                    category__transactions__date__gte=start_date,
                    category__transactions__date__lte=end_date,
                ),
            ),
        )
        .values("name", "color", "icon", "amount", "spent")
    )

    return [BudgetData(**budget) for budget in budgets]


def get_budget_alerts(budgets: list[BudgetData]) -> list[dict]:
    """Generate budget alerts based on spending patterns.

    Args:
        budgets (list[BudgetData]): List of budget data objects

    Returns:
        list[dict]: List of alert dictionaries with type, name, and message
    """
    alerts = []

    for budget in budgets:
        if budget.is_over_budget:
            alerts.append(
                {
                    "type": "danger",
                    "icon": "exclamation-circle",
                    "name": budget.name,
                    "message": f"is {budget.percentage_used}% over budget",
                }
            )
        elif budget.percentage_used >= 80:
            alerts.append(
                {
                    "type": "warning",
                    "icon": "exclamation-triangle",
                    "name": budget.name,
                    "message": f"is at {budget.percentage_used}% of budget",
                }
            )
        else:
            alerts.append(
                {
                    "type": "info",
                    "icon": "info-circle",
                    "name": budget.name,
                    "message": "is within budget",
                }
            )

    return alerts[:4]  # Limit to 4 alerts


# Create your views here.
def budgets_view(request: WSGIRequest) -> HttpResponse:
    categories = Category.objects.filter(user=request.user, type="expense")
    budgets = get_butgets_data(request.user)
    total_budget = sum([budget.amount for budget in budgets])
    total_spent = sum([budget.spent for budget in budgets])
    over_budget = total_spent - total_budget
    total_budgets = len(budgets)
    budget_alerts = get_budget_alerts(budgets)

    context: dict = {
        "categories": categories,
        "budgets": budgets,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "over_budget": over_budget,
        "total_budgets": total_budgets,
        "budget_alerts": budget_alerts,
    }

    if request.method == "POST":
        category_id = request.POST.get("category", "")
        amount = request.POST.get("amount", "")
        period = request.POST.get("period", "")
        description = request.POST.get("description", "")
        _ = request.POST.get("notifications", "") == "on"

        period = "monthly"  # TODO: implement other periods

        required_fields = [category_id, amount, period]

        if any(not field for field in required_fields):
            context["messages"] = [
                {
                    "message": "All fields except description and notifications are required.",
                    "tags": "danger",
                }
            ]
            return render(
                request,
                "budgets.html",
                context,
            )

        # create and save the budget object
        try:
            category = get_object_or_404(Category, id=category_id)
            budget = Budget(
                amount=amount,
                period=period,
                description=description,
                category=category,
                user=request.user,
            )
            budget.save()
            context["messages"] = [
                {
                    "message": "Budget created successfully!",
                    "tags": "success",
                }
            ]
        except Exception as e:
            logger.error("Error creating budget:", e)
            context["messages"] = [
                {
                    "message": f"Error creating budget: {e}",
                    "tags": "danger",
                }
            ]
            return render(
                request,
                "budgets.html",
                context,
            )

    return render(
        request,
        "budgets.html",
        context,
    )
