import logging

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render

from categories.models import Category, get_total_categories_by_type
from core.constants import CATEGORIES_ICON_OPTIONS, COLOR_OPTIONS
from core.models import Account
from transactions.models import get_total_transactions

logger = logging.getLogger(__name__)


class CategoryData:
    def __init__(
        self, id, name, description, type, icon, color, total_transactions, total_amount
    ):
        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.icon = icon
        self.color = color
        self.total_transactions = total_transactions
        self.total_amount = total_amount if total_amount is not None else 0

    def __str__(self) -> str:
        return f"CategoryData(name={self.name}, type={self.type}, total_transactions={self.total_transactions}, total_amount={self.total_amount})"


def get_categories_data(
    user: AbstractBaseUser | AnonymousUser, category_type: str
) -> list[CategoryData]:
    """Fetches and returns category data for the given user and category type.

    Args:
        user (AbstractBaseUser | AnonymousUser): The user whose category data is to be fetched.

    Returns:
        list[CategoryData]: A list containing all categories for a specific user, including names, descriptions, types, icons, and colors, as well as total transactions for that category and total amount spent in that category.
    """
    categories = (
        Category.objects.filter(user=user, type=category_type)
        .annotate(
            total_transactions=Count("transactions"),
            total_amount=Sum("transactions__amount"),
        )
        .values(
            "id",
            "name",
            "description",
            "type",
            "icon",
            "color",
            "total_transactions",
            "total_amount",
        )
    )

    return [CategoryData(**cat) for cat in categories]


# Create your views here.
def categories_view(request: WSGIRequest) -> HttpResponse:
    account = Account.objects.get(user=request.user)
    total_expense_categories = get_total_categories_by_type(request.user, "expense")
    total_income_categories = get_total_categories_by_type(request.user, "income")
    total_categories = total_expense_categories + total_income_categories
    total_transactions = get_total_transactions(account)
    expense_categories_data = get_categories_data(request.user, "expense")
    income_categories_data = get_categories_data(request.user, "income")

    context: dict = {
        "total_categories": total_categories,
        "total_expense_categories": total_expense_categories,
        "total_income_categories": total_income_categories,
        "total_transactions": total_transactions,
        "expense_categories_data": expense_categories_data,
        "income_categories_data": income_categories_data,
        "color_options": COLOR_OPTIONS,
        "icon_options": CATEGORIES_ICON_OPTIONS,
    }

    if request.method == "POST":
        category_name = request.POST.get("category_name", "")
        category_type = request.POST.get("category_type", "")
        category_icon = request.POST.get("category_icon", "")
        category_color = request.POST.get("category_color", "")
        category_description = request.POST.get("category_description", "")
        _ = request.POST.get("category_active") == "on"

        required_fields = [category_name, category_type]

        if any(not field for field in required_fields):
            context["messages"] = [
                {"message": "Category name and type are required.", "tags": "danger"}
            ]
            return render(
                request,
                "categories.html",
                context,
            )

        # Create and save the new category
        category = Category(
            name=category_name,
            type=category_type,
            icon=category_icon,
            color=category_color,
            description=category_description,
            user=request.user,
        )

        try:
            category.save()
            context["messages"] = [
                {"message": "Category created successfully.", "tags": "success"}
            ]
            return render(
                request,
                "categories.html",
                context,
            )
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            context["messages"] = [
                {
                    "message": "An error occurred while creating the category. Please try again later.",
                    "tags": "danger",
                }
            ]
            return render(
                request,
                "categories.html",
                context,
            )

    return render(request, "categories.html", context)
