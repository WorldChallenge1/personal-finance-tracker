from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from core.constants import THEMES


# Create your models here.
class Account(models.Model):
    """A model representing a user's financial account.

    Attributes:
        user (OneToOneField): A one-to-one relationship with the Django User model.
        balance (DecimalField): The current balance of the account.
        created_at (DateTimeField): The date and time when the account was created.
        updated_at (DateTimeField): The date and time when the account was last updated.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_balance(self, transaction_type: str, amount: float) -> None:
        """Update the account balance based on the transaction type and amount.

        Args:
            transaction_type (str): The type of transaction ('income' or 'expense').
            amount (float): The amount of the transaction.
        """
        if transaction_type == "income":
            self.balance += Decimal(amount)
        elif transaction_type == "expense":
            self.balance -= Decimal(amount)
        self.save()

    def recalculate_balance(self):
        """Calculate the current balance based on all associated transactions."""
        # Import inside method to avoid circular import
        from transactions.models import get_total_by_type

        income_total = get_total_by_type(self, "income")
        expense_total = get_total_by_type(self, "expense")
        self.balance = income_total - expense_total
        self.save()


class Options(models.Model):
    """A model representing a user's options.

    Attributes:
        user (OneToOneField): A one-to-one relationship with the Django User model.
        theme (CharField): The theme of the user's interface.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="options")
    theme = models.CharField(max_length=10, choices=THEMES, default="light")
