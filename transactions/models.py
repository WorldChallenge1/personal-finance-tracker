from decimal import Decimal

from django.db import models
from django.utils import timezone

from categories.models import Category
from core.constants import TRANSACTION_TYPES
from core.models import Account

# Create your models here.


class Transaction(models.Model):
    """Model representing a financial transaction.

    This model is associated with a category and an account.

    Attributes:
        date (DateTimeField): The date and time of the transaction.
        description (CharField): A brief description of the transaction.
        type (CharField): The type of transaction (income or expense).
        amount (DecimalField): The amount of money involved in the transaction.
        category (ForeignKey): The category associated with the transaction.
        account (ForeignKey): The account associated with the transaction.
    """

    date = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="transactions"
    )
    account = models.ForeignKey(
        "core.Account", on_delete=models.CASCADE, related_name="transactions"
    )

    class Meta:
        ordering = ["-date"]

    def save(self, *args, **kwargs) -> None:
        self.account.update_balance(self.type, self.amount)

        super().save(*args, **kwargs)


def get_total_transactions(account: Account) -> int:
    """Returns the number of transactions associated with a given account.

    Args:
        account (Account): The account for which transactions are to be counted.

    Returns:
        int: The number of transactions associated with the account.
    """
    return Transaction.objects.filter(account=account).count()


def get_total_by_type(account: Account, type: str) -> Decimal:
    """Returns the total amount associated with a given account and transaction type.

    Args:
        account (Account): The account for which expenses are to be calculated.
        type (str): The type of transaction (income or expense).

    Returns:
        float: The total amount associated with the account and transaction type.
    """
    total_amount = Transaction.objects.filter(account=account, type=type).aggregate(
        total=models.Sum("amount")
    )["total"]

    if total_amount is None:
        return Decimal(0.0)

    return total_amount
