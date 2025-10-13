from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class Goal(models.Model):
    """Model representing a financial goal.
    Each goal is associated with a user.
    Attributes:
        name (str): The name of the goal.
        description (str): A brief description of the goal.
        target_amount (Decimal): The target amount to be saved for the goal.
        current_amount (Decimal): The current amount saved towards the goal.
        start_date (Date): The date when the goal was created.
        target_date (Date): The target date to achieve the goal.
        icon (str): An optional icon representing the goal.
        color (str): An optional color code for the goal.
        achieved (bool): A flag indicating whether the goal has been achieved.
        updated_at (DateTime): The date and time when the goal was last updated.
        achieved_at (DateTime): The date and time when the goal was achieved.
        user (User): The user to whom this goal belongs.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    start_date = models.DateField(auto_now_add=True)
    target_date = models.DateField(null=False)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=10, blank=True, null=True)
    achieved = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    achieved_at = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="goals",
    )

    def save(self, *args, **kwargs):
        # create history entry when goal is saved (created or updated)
        super().save(*args, **kwargs)
        GoalHistory.objects.create(goal=self, amount=self.current_amount)


class GoalHistory(models.Model):
    """Model representing the history of a goal.
    Each history entry is associated with a goal.
    Attributes:
        goal (ForeignKey): The goal associated with the history entry.
        amount (Decimal): The amount saved towards the goal.
        date (DateTime): The date and time when the history entry was created.
    """

    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="history")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
