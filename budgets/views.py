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
    def __init__(self, id, name, icon, color, spent, amount, description=""):
        self.id = id
        self.name = name
        self.icon = icon
        self.color = color
        self.spent = spent if spent is not None else 0
        self.amount = amount
        self.description = description

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


def get_budgets_data(user: AbstractBaseUser | AnonymousUser) -> list[BudgetData]:
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
        .values("id", "name", "color", "icon", "amount", "spent", "description")
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

    context: dict = {
        "categories": categories,
    }

    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "delete":
            # Handle delete budget
            budget_id = request.POST.get("budget_id")
            try:
                budget = get_object_or_404(Budget, id=budget_id, user=request.user)
                budget.delete()
                context["messages"] = [
                    {
                        "message": "Budget deleted successfully.",
                        "tags": "success",
                    }
                ]
            except Budget.DoesNotExist:
                context["messages"] = [
                    {
                        "message": "Budget not found or you don't have permission to delete it.",
                        "tags": "danger",
                    }
                ]
            except Exception as e:
                logger.error(f"Error deleting budget: {e}")
                context["messages"] = [
                    {
                        "message": "An error occurred while deleting the budget.",
                        "tags": "danger",
                    }
                ]

        elif action == "edit":
            # Handle edit budget
            budget_id = request.POST.get("budget_id")
            category_id = request.POST.get("category", "")
            amount = request.POST.get("amount", "")
            description = request.POST.get("description", "")

            if not category_id or not amount:
                context["messages"] = [
                    {
                        "message": "Category and amount are required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    budget = get_object_or_404(Budget, id=budget_id, user=request.user)
                    category = get_object_or_404(
                        Category, id=category_id, user=request.user
                    )

                    # Update budget
                    budget.category = category
                    budget.amount = amount
                    budget.description = description
                    budget.save()

                    context["messages"] = [
                        {
                            "message": "Budget updated successfully.",
                            "tags": "success",
                        }
                    ]
                except (Budget.DoesNotExist, Category.DoesNotExist) as e:
                    logger.error(f"Error: Budget or Category does not exist. {e}")
                    context["messages"] = [
                        {
                            "message": "Budget or category not found or you don't have permission to edit.",
                            "tags": "danger",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error updating budget: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while updating the budget.",
                            "tags": "danger",
                        }
                    ]

        else:  # Default to add budget
            category_id = request.POST.get("category", "")
            amount = request.POST.get("amount", "")
            period = request.POST.get("period", "")
            description = request.POST.get("description", "")

            period = "monthly"  # TODO: implement other periods

            required_fields = [category_id, amount, period]

            if any(not field for field in required_fields):
                context["messages"] = [
                    {
                        "message": "All fields except description are required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    category = get_object_or_404(
                        Category, id=category_id, user=request.user
                    )
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
                except Category.DoesNotExist:
                    logger.error("Error: Category does not exist.")
                    context["messages"] = [
                        {
                            "message": "Selected category does not exist.",
                            "tags": "danger",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error creating budget: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while creating the budget.",
                            "tags": "danger",
                        }
                    ]

    # Get budgets data
    budgets = get_budgets_data(request.user)
    total_budget = sum([budget.amount for budget in budgets])
    total_spent = sum([budget.spent for budget in budgets])
    over_budget = total_spent - total_budget
    total_budgets = len(budgets)
    budget_alerts = get_budget_alerts(budgets)

    context.update(
        {
            "budgets": budgets,
            "total_budget": total_budget,
            "total_spent": total_spent,
            "over_budget": over_budget,
            "total_budgets": total_budgets,
            "budget_alerts": budget_alerts,
        }
    )

    return render(
        request,
        "budgets.html",
        context,
    )
