from datetime import date, timedelta
from decimal import Decimal

from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from budgets.views import get_butgets_data
from core.constants import COLOR_MAP
from core.models import Account
from core.utils import get_current_month_date_range
from goals.views import get_goals_data
from transactions.models import Transaction
from transactions.views import TransactionData


def get_monthly_income_and_expenses(
    account, start_date: date, end_date: date
) -> tuple[Decimal, Decimal]:
    """Calculates total income and expenses for the given account within the specified date range."""
    transactions = Transaction.objects.filter(
        account=account, date__range=(start_date, end_date)
    )
    total_income = transactions.filter(type="income").aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal(0)
    total_expenses = transactions.filter(type="expense").aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal(0)
    return (
        total_income,
        total_expenses,
    )


def get_recent_transactions(account, limit=5):
    """Fetches the most recent transactions for the given account."""
    transactions = (
        Transaction.objects.filter(account=account)
        .select_related("category")
        .values(
            "date",
            "description",
            "type",
            "amount",
            "category__name",
            "category__icon",
            "category__color",
        )
        .order_by("-date")[:limit]
    )
    return [
        TransactionData(
            date=tx["date"],
            description=tx["description"],
            type=tx["type"],
            amount=tx["amount"],
            category_name=tx["category__name"],
            category_icon=tx["category__icon"],
            category_color=tx["category__color"],
        )
        for tx in transactions
    ]


def get_last_n_months(n=6) -> list[tuple[date, date, str]]:
    """Returns a list of (start_date, end_date, month_name) tuples for the last n months."""
    today = date.today()
    months = []

    for i in range(n - 1, -1, -1):
        # Calculate the month
        month = today.month - i
        year = today.year

        # Handle year rollover
        while month <= 0:
            month += 12
            year -= 1

        first_day = date(year, month, 1)

        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        month_name = first_day.strftime("%B")
        months.append((first_day, last_day, month_name))

    return months


# Create your views here.


def dashboard_view(request: WSGIRequest) -> HttpResponse:
    account = Account.objects.get(user=request.user)
    total_income, total_expenses = get_monthly_income_and_expenses(
        account, *get_current_month_date_range()
    )
    recent_transactions = get_recent_transactions(account)
    budgets = get_butgets_data(request.user)
    budgets.sort(key=lambda x: x.percentage_used, reverse=True)
    budgets = budgets[:3]
    goals = get_goals_data(request.user)
    goals.sort(key=lambda x: x.percentage_achieved, reverse=True)
    goals = goals[:3]
    context = {
        "total_balance": account.balance,
        "this_month_income": total_income,
        "this_month_expenses": total_expenses,
        "recent_transactions": recent_transactions,
        "last_updated": date.today().strftime("%B %d, %Y"),
        "budgets": budgets,
        "goals": goals,
    }

    return render(
        request,
        "dashboard.html",
        context,
    )


@require_http_methods(["GET"])
def category_pie_chart_data(request: WSGIRequest) -> JsonResponse:
    account = Account.objects.get(user=request.user)
    start_date, end_date = get_current_month_date_range()
    expenses_by_category = (
        Transaction.objects.filter(
            account=account, type="expense", date__range=(start_date, end_date)
        )
        .values("category__name", "category__color")
        .annotate(total=models.Sum("amount"))
        .order_by("-total")
    )
    data = {
        "labels": [item["category__name"] for item in expenses_by_category],
        "datasets": [
            {
                "data": [float(item["total"]) for item in expenses_by_category],
                "backgroundColor": [
                    COLOR_MAP[item["category__color"]] or "#000000"
                    for item in expenses_by_category
                ],
            }
        ],
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
def spending_trend_chart_data(request: WSGIRequest) -> JsonResponse:
    account = Account.objects.get(user=request.user)
    months = get_last_n_months(6)

    labels = []
    income_data = []
    expense_data = []

    for start_date, end_date, month_name in months:
        labels.append(month_name)

        # Get income and expenses for this month
        total_income, total_expenses = get_monthly_income_and_expenses(
            account, start_date, end_date
        )

        income_data.append(float(total_income))
        expense_data.append(float(total_expenses))

    data = {
        "labels": labels,
        "datasets": [
            {
                "label": "Expenses",
                "data": expense_data,
                "borderColor": "#e74c3c",
                "backgroundColor": "rgba(231, 76, 60, 0.1)",
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Income",
                "data": income_data,
                "borderColor": "#27ae60",
                "backgroundColor": "rgba(39, 174, 96, 0.1)",
                "tension": 0.4,
                "fill": True,
            },
        ],
    }

    return JsonResponse(data)
