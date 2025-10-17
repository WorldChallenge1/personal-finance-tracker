import csv
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper

from django.core.files.uploadedfile import UploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import EmptyPage, Page, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from categories.models import Category
from core.models import Account
from transactions.models import Transaction

logger = logging.getLogger(__name__)


class TransactionData:
    def __init__(
        self,
        id,
        date,
        description,
        type,
        amount,
        category_name,
        category_icon,
        category_color,
        category_id,
    ):
        self.id = id
        self.date = date
        self.description = description
        self.type = type
        self.amount = amount
        self.category_name = category_name
        self.category_icon = category_icon
        self.category_color = category_color
        self.category_id = category_id

    def __str__(self) -> str:
        return f"TransactionData(id={self.id}, date={self.date}, type={self.type}, amount={self.amount}, category_name={self.category_name}, category_icon={self.category_icon}, category_color={self.category_color}, category_id={self.category_id})"


def get_transactions_data(
    account: Account,
    page_number: int = 1,
    page_size: int = 20,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    category: Category | None = None,
    transaction_type: str | None = None,
) -> tuple[list[TransactionData], Page, float, float]:
    """Fetches and returns transaction data for the given account.

    Args:
        account (Account): The account whose transaction data is to be fetched.
        page_number (int): The page number for pagination (default is 1).
        page_size (int): The number of transactions per page (default is 20).
        start_date (datetime, optional): Filter transactions from this date onwards.
        end_date (datetime, optional): Filter transactions up to this date.
        category (Category, optional): Filter transactions by this category.
        transaction_type (str, optional): Filter transactions by type ('income' or 'expense')

    Returns:
        tuple: A tuple containing a list of TransactionData objects, the Page object for pagination,
               total income amount, and total expenses amount.
    """
    transactions = (
        Transaction.objects.filter(account=account)
        .select_related("category")
        .values(
            "id",
            "date",
            "description",
            "type",
            "amount",
            "category__name",
            "category__icon",
            "category__color",
            "category_id",
        )
    )

    # Apply filters if provided
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if category:
        transactions = transactions.filter(category=category)
    if transaction_type and transaction_type in ["income", "expense"]:
        transactions = transactions.filter(type=transaction_type)

    transactions = transactions.order_by("-date")

    total_income = sum(tx["amount"] for tx in transactions.filter(type="income"))
    total_expenses = sum(tx["amount"] for tx in transactions.filter(type="expense"))

    # Create paginator
    paginator = Paginator(transactions, page_size)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        page_obj = paginator.page(paginator.num_pages)

    transaction_data = [
        TransactionData(
            id=tx["id"],
            date=tx["date"],
            description=tx["description"],
            type=tx["type"],
            amount=tx["amount"],
            category_name=tx["category__name"],
            category_icon=tx["category__icon"],
            category_color=tx["category__color"],
            category_id=tx["category_id"],
        )
        for tx in page_obj
    ]

    return transaction_data, page_obj, total_income, total_expenses


# Create your views here.
def transactions_view(request: WSGIRequest) -> HttpResponse:
    categories = Category.objects.filter(user=request.user)
    account = Account.objects.get(user=request.user)

    # Get filter parameters from request
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    category_id = request.GET.get("category")
    transaction_type = request.GET.get("type")

    # Convert date strings to date objects
    start_date_obj = None
    end_date_obj = None

    if start_date:
        try:
            start_date_obj = timezone.make_aware(
                datetime.combine(
                    datetime.strptime(start_date, "%Y-%m-%d").date(),
                    datetime.min.time(),
                )
            )
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = timezone.make_aware(
                datetime.combine(
                    datetime.strptime(end_date, "%Y-%m-%d").date(), datetime.max.time()
                )
            )
        except ValueError:
            pass

    # Validate category exists and belongs to user
    if category_id:
        try:
            category_id = int(category_id)
            if not categories.filter(id=category_id).exists():
                category_id = None
        except (ValueError, TypeError):
            category_id = None

    category = categories.filter(id=category_id).first() if category_id else None

    # Get page number from request
    page_number = request.GET.get("page", 1)

    context: dict = {}

    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "delete":
            # Handle delete transaction
            transaction_id = request.POST.get("transaction_id")
            try:
                transaction = get_object_or_404(
                    Transaction, id=transaction_id, account=account
                )
                transaction.delete()

                # Recalculate account balance
                account.recalculate_balance()

                context["messages"] = [
                    {
                        "message": "Transaction deleted successfully.",
                        "tags": "success",
                    }
                ]
            except Transaction.DoesNotExist:
                context["messages"] = [
                    {
                        "message": "Transaction not found or you don't have permission to delete it.",
                        "tags": "danger",
                    }
                ]
            except Exception as e:
                logger.error(f"Error deleting transaction: {e}")
                context["messages"] = [
                    {
                        "message": "An error occurred while deleting the transaction.",
                        "tags": "danger",
                    }
                ]

        elif action == "edit":
            # Handle edit transaction
            transaction_id = request.POST.get("transaction_id")
            transaction_amount = request.POST.get("transaction_amount", "")
            transaction_description = request.POST.get("transaction_description", "")
            transaction_category = request.POST.get("transaction_category", "")
            transaction_date = request.POST.get("transaction_date", "")

            required_fields = [
                transaction_amount,
                transaction_category,
                transaction_date,
                transaction_id,
            ]

            if any(not field for field in required_fields):
                context["messages"] = [
                    {
                        "message": "All fields are required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    transaction = get_object_or_404(
                        Transaction, id=transaction_id, account=account
                    )
                    category = get_object_or_404(Category, id=transaction_category)

                    # Update transaction
                    transaction.type = category.type
                    transaction.amount = transaction_amount
                    transaction.description = transaction_description
                    transaction.category = category
                    transaction.date = transaction_date
                    transaction.save()

                    # Recalculate account balance
                    account.recalculate_balance()

                    context["messages"] = [
                        {
                            "message": "Transaction updated successfully.",
                            "tags": "success",
                        }
                    ]
                except (Category.DoesNotExist, Transaction.DoesNotExist) as e:
                    logger.error(f"Error: Category or Transaction does not exist. {e}")
                    context["messages"] = [
                        {
                            "message": "Selected category or transaction does not exist.",
                            "tags": "danger",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error updating transaction: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while updating the transaction.",
                            "tags": "danger",
                        }
                    ]

        else:  # Default to add transaction
            transaction_amount = request.POST.get("transaction_amount", "")
            transaction_description = request.POST.get("transaction_description", "")
            transaction_category = request.POST.get("transaction_category", "")
            transaction_date = request.POST.get("transaction_date", "")

            required_fields = [
                transaction_amount,
                transaction_category,
                transaction_date,
            ]

            if any(not field for field in required_fields):
                context["messages"] = [
                    {
                        "message": "All fields are required.",
                        "tags": "danger",
                    }
                ]
            else:
                try:
                    category = get_object_or_404(Category, id=transaction_category)

                    # create and save the new transaction
                    transaction = Transaction(
                        type=category.type,
                        amount=transaction_amount,
                        description=transaction_description,
                        category=category,
                        date=transaction_date,
                        account=account,
                    )

                    transaction.save()

                    # Recalculate account balance
                    account.recalculate_balance()

                    context["messages"] = [
                        {
                            "message": "Transaction added successfully.",
                            "tags": "success",
                        }
                    ]
                except Category.DoesNotExist as e:
                    logger.error("Error: Category does not exist.", e)
                    context["messages"] = [
                        {
                            "message": "Selected category does not exist.",
                            "tags": "danger",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error saving transaction: {e}")
                    context["messages"] = [
                        {
                            "message": "An error occurred while adding the transaction.",
                            "tags": "danger",
                        }
                    ]

    # Get paginated transactions
    transactions, page_obj, total_income, total_expenses = get_transactions_data(
        account,
        int(page_number),
        page_size=25,
        start_date=start_date_obj,
        end_date=end_date_obj,
        category=category,
        transaction_type=transaction_type,
    )
    net_income = total_income - total_expenses

    context["current_date"] = timezone.now().date().isoformat()
    context["categories"] = categories
    context["total_expenses"] = total_expenses
    context["total_income"] = total_income
    context["net_income"] = net_income
    context["transactions"] = transactions
    context["page_obj"] = page_obj
    context["current_filters"] = {
        "start_date": start_date,
        "end_date": end_date,
        "category": category_id,
        "type": transaction_type,
    }

    return render(request, "transactions.html", context)


@require_http_methods(["POST"])
def import_transactions_csv(request: WSGIRequest) -> JsonResponse:
    """Import transactions from CSV file"""

    if "csv_file" not in request.FILES:
        return JsonResponse({"success": False, "message": "No file was uploaded."})

    csv_file = request.FILES["csv_file"]

    if not isinstance(csv_file, UploadedFile):
        return JsonResponse({"success": False, "message": "Invalid file upload."})

    # Validate file type
    if not csv_file.name or not csv_file.name.endswith(".csv"):
        return JsonResponse({"success": False, "message": "Please upload a CSV file."})

    # Validate file size (limit to 5MB)
    if not csv_file.size or csv_file.size > 5 * 1024 * 1024:
        return JsonResponse(
            {
                "success": False,
                "message": "File size too large. Please upload a file smaller than 5MB.",
            }
        )

    try:
        account = Account.objects.get(user=request.user)
        user_categories = Category.objects.filter(user=request.user)

        # Create a mapping of category IDs for quick lookup
        category_map = {str(cat.id): cat for cat in user_categories}  # type: ignore

        # Parse CSV file
        with csv_file.open("r") as f:
            file_data = TextIOWrapper(f, encoding="utf-8")
            csv_reader = csv.DictReader(file_data)

            # Validate CSV headers
            required_headers = ["date", "description", "type", "amount", "category_id"]

            if not csv_reader.fieldnames or not all(
                header in csv_reader.fieldnames for header in required_headers
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"CSV must contain these headers: {', '.join(required_headers)}",
                    }
                )

            transactions_to_create = []
            errors = []
            row_number = 1

            for row in csv_reader:
                row_number += 1
                try:
                    # Validate and clean data
                    date_str = row["date"].strip()
                    description = row["description"].strip()
                    transaction_type = row["type"].strip().lower()
                    amount_str = row["amount"].strip()
                    category_id = row["category_id"].strip()

                    # Validate required fields
                    if not all([date_str, transaction_type, amount_str, category_id]):
                        errors.append(f"Row {row_number}: Missing required fields")
                        continue

                    # Validate transaction type
                    if transaction_type not in ["income", "expense"]:
                        errors.append(
                            f"Row {row_number}: Type must be 'income' or 'expense'"
                        )
                        continue

                    # Validate amount
                    try:
                        amount = Decimal(amount_str)

                        if amount <= 0:
                            errors.append(
                                f"Row {row_number}: Amount must be greater than 0"
                            )
                            continue

                    except (InvalidOperation, ValueError):
                        errors.append(f"Row {row_number}: Invalid amount format")
                        continue

                    # Validate category exists and belongs to user
                    if category_id not in category_map:
                        errors.append(
                            f"Row {row_number}: Category ID {category_id} not found or doesn't belong to user"
                        )
                        continue

                    category = category_map[category_id]

                    # Validate that category type matches transaction type
                    if category.type != transaction_type:
                        errors.append(
                            f"Row {row_number}: Category type '{category.type}' doesn't match transaction type '{transaction_type}'"
                        )
                        continue

                    # Parse date
                    try:
                        date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]

                        parsed_date = None

                        for date_format in date_formats:
                            try:
                                parsed_date = datetime.strptime(
                                    date_str, date_format
                                ).date()
                                parsed_date = timezone.make_aware(
                                    datetime.combine(parsed_date, datetime.min.time())
                                )
                                break

                            except ValueError:
                                continue

                        if parsed_date is None:
                            errors.append(
                                f"Row {row_number}: Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY"
                            )

                            continue

                    except ValueError:
                        errors.append(f"Row {row_number}: Invalid date format")
                        continue

                    # Create transaction object (don't save yet)
                    transaction = Transaction(
                        type=transaction_type,
                        amount=amount,
                        description=description or "Imported transaction",
                        category=category,
                        date=parsed_date,
                        account=account,
                    )

                    transactions_to_create.append(transaction)

                except Exception as e:
                    logger.error(f"Error processing row {row_number}: {e}")
                    errors.append(f"Row {row_number}: Unexpected error - {str(e)}")

        # If there are errors, return them without saving anything
        if errors:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Errors found in CSV file:",
                    "errors": errors[:10],  # Limit to first 10 errors
                }
            )

        # If no errors, save all transactions
        if transactions_to_create:
            Transaction.objects.bulk_create(transactions_to_create)

            # Update account balance
            account.recalculate_balance()
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Successfully imported {len(transactions_to_create)} transactions.",
                }
            )

        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "No valid transactions found in the CSV file.",
                }
            )

    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": "An error occurred while processing the file. Please try again.",
            }
        )


@require_http_methods(["GET"])
def export_transactions_csv(request: WSGIRequest) -> HttpResponse:
    """Export transactions to CSV file"""

    try:
        account = Account.objects.get(user=request.user)

        # Get filter parameters from request
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        category_id = request.GET.get("category")
        transaction_type = request.GET.get("type")

        # Convert date strings to date objects
        start_date_obj = None
        end_date_obj = None

        if start_date:
            try:
                start_date_obj = timezone.make_aware(
                    datetime.combine(
                        datetime.strptime(start_date, "%Y-%m-%d").date(),
                        datetime.min.time(),
                    )
                )
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = timezone.make_aware(
                    datetime.combine(
                        datetime.strptime(end_date, "%Y-%m-%d").date(),
                        datetime.max.time(),
                    )
                )
            except ValueError:
                pass

        # Fetch all transactions for the user's account with applied filters
        transactions = (
            Transaction.objects.filter(account=account)
            .select_related("category")
            .values("date", "description", "type", "amount", "category__id")
        )

        if start_date_obj:
            transactions = transactions.filter(date__gte=start_date_obj)
        if end_date_obj:
            transactions = transactions.filter(date__lte=end_date_obj)
        if category_id:
            try:
                category_id = int(category_id)
                transactions = transactions.filter(category__id=category_id)
            except (ValueError, TypeError):
                pass
        if transaction_type and transaction_type in ["income", "expense"]:
            transactions = transactions.filter(type=transaction_type)

        transactions = transactions.order_by("-date")

        # Create the HttpResponse object with CSV headers
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="transactions_export.csv"'
        )

        writer = csv.writer(response)
        # Write CSV header
        writer.writerow(["date", "description", "type", "amount", "category_id"])

        for tx in transactions:
            writer.writerow(
                [
                    tx["date"].strftime("%Y-%m-%d %H:%M:%S"),
                    tx["description"],
                    tx["type"],
                    f"{tx['amount']:.2f}",
                    tx["category__id"],
                ]
            )

        return response

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return HttpResponse(
            "An error occurred while exporting transactions. Please try again.",
            status=500,
        )
