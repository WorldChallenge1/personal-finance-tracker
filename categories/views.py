import logging

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

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
        category_type (str): The type of category ('income' or 'expense').

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
    context: dict = {}
    account = Account.objects.get(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "delete":
            # Handle delete category
            category_id = request.POST.get("category_id")
            try:
                category = get_object_or_404(
                    Category, id=category_id, user=request.user
                )
                category.delete()
                account.recalculate_balance()
                context["messages"] = [
                    {
                        "message": "Category deleted successfully.",
                        "tags": "success",
                    }
                ]
            except Category.DoesNotExist:
                context["messages"] = [
                    {
                        "message": "Category not found or you don't have permission to delete it.",
                        "tags": "danger",
                    }
                ]
            except Exception as e:
                logger.error(f"Error deleting category: {e}")
                context["messages"] = [
                    {
                        "message": "An error occurred while deleting the category.",
                        "tags": "danger",
                    }
                ]

        elif action == "edit":
            # Handle edit category
            category_id = request.POST.get("category_id")
            category_name = request.POST.get("category_name", "")
            category_icon = request.POST.get("category_icon", "")
            category_color = request.POST.get("category_color", "")
            category_description = request.POST.get("category_description", "")

            if not category_name:
                context["messages"] = [
                    {
                        "message": "Category name is required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    category = get_object_or_404(
                        Category, id=category_id, user=request.user
                    )

                    # Update category
                    category.name = category_name
                    category.icon = category_icon
                    category.color = category_color
                    category.description = category_description
                    category.save()

                    context["messages"] = [
                        {
                            "message": "Category updated successfully.",
                            "tags": "success",
                        }
                    ]
                except Category.DoesNotExist:
                    context["messages"] = [
                        {
                            "message": "Category not found or you don't have permission to edit it.",
                            "tags": "danger",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error updating category: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while updating the category.",
                            "tags": "danger",
                        }
                    ]

        else:  # Default to add category
            category_name = request.POST.get("category_name", "")
            category_type = request.POST.get("category_type", "")
            category_icon = request.POST.get("category_icon", "")
            category_color = request.POST.get("category_color", "")
            category_description = request.POST.get("category_description", "")

            required_fields = [category_name, category_type]

            if any(not field for field in required_fields):
                context["messages"] = [
                    {
                        "message": "Category name and type are required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    # Create and save the new category
                    category = Category(
                        name=category_name,
                        type=category_type,
                        icon=category_icon,
                        color=category_color,
                        description=category_description,
                        user=request.user,
                    )
                    category.save()
                    context["messages"] = [
                        {"message": "Category created successfully.", "tags": "success"}
                    ]
                except Exception as e:
                    logger.error(f"Error creating category: {str(e)}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while creating the category. Please try again later.",
                            "tags": "danger",
                        }
                    ]

    total_expense_categories = get_total_categories_by_type(request.user, "expense")
    total_income_categories = get_total_categories_by_type(request.user, "income")
    total_categories = total_expense_categories + total_income_categories
    total_transactions = get_total_transactions(account)
    expense_categories_data = get_categories_data(request.user, "expense")
    income_categories_data = get_categories_data(request.user, "income")

    context.update(
        {
            "expense_categories_data": expense_categories_data,
            "income_categories_data": income_categories_data,
            "total_categories": total_categories,
            "total_expense_categories": total_expense_categories,
            "total_income_categories": total_income_categories,
            "total_transactions": total_transactions,
            "color_options": COLOR_OPTIONS,
            "icon_options": CATEGORIES_ICON_OPTIONS,
        }
    )

    return render(request, "categories.html", context)
