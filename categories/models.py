from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser, User
from django.db import models

from core.constants import TRANSACTION_TYPES


# Create your models here.
class Category(models.Model):
    """Model representing a financial category.
    Each category is associated with a user and can be of type 'expense' or 'income'.

    Attributes:
        name (str): The name of the category.
        description (str): A brief description of the category.
        type (str): The type of the category, either 'expense' or 'income'.
        icon (str): An optional icon representing the category.
        color (str): An optional color code for the category.
        user (User): The user to whom this category belongs.
    """

    name = models.CharField(max_length=100, unique=True, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=10, blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


def get_total_categories(user: AbstractBaseUser | AnonymousUser) -> int:
    """Returns the number of categories associated with a given user.

    Args:
        user (User): The user whose categories are to be counted.

    Returns:
        int: The number of categories associated with the user.
    """
    return Category.objects.filter(user=user).count()


def get_total_categories_by_type(
    user: AbstractBaseUser | AnonymousUser, category_type: str
) -> int:
    """Returns the number of categories of a specific type associated with a given user.

    Args:
        user (User): The user whose categories are to be counted.
        category_type (str): The type of categories to count ('expense' or 'income').

    Returns:
        int: The number of categories of the specified type associated with the user.
    """
    return Category.objects.filter(user=user, type=category_type).count()
