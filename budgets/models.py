from django.contrib.auth.models import User
from django.db import models

from categories.models import Category
from core.constants import BUDGET_PERIODS


# Create your models here.
class Budget(models.Model):
    """Model representing a budget.
    Attributes:
        amount (Decimal): The total amount allocated for the budget.
        period (str): The period of the budget (e.g., weekly, monthly, quarterly).
        description (str): A brief description of the budget.
        category (ForeignKey): The category associated with the budget.
        created_at (DateTime): The date and time when the budget was created.
        updated_at (DateTime): The date and time when the budget was last updated.
        user (ForeignKey): The user who owns the budget.
    """

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budgets"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    period = models.CharField(max_length=10, choices=BUDGET_PERIODS)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="budgets",
    )

    def __str__(self):
        return self.category
