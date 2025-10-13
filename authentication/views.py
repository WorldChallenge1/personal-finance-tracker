import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import redirect, render

from core.models import Account, Options

logger = logging.getLogger(__name__)


def register_user(
    username: str, first_name: str, last_name: str, password: str, email: str
) -> User:
    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
        email=email,
    )
    user.save()
    account = Account(user=user)
    account.save()
    options = Options(user=user)
    options.save()
    return user


# Create your views here.
def register_view(request: WSGIRequest) -> HttpResponse:
    if request.method == "POST":
        # Handle registration logic here
        username = request.POST.get("username", "")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        email = request.POST.get("email", "")

        required_fields = [username, first_name, last_name, password1, password2, email]

        if password1 != password2:
            return render(
                request,
                "register.html",
                {"messages": [{"message": "Passwords do not match", "tags": "danger"}]},
            )

        if any(not field for field in required_fields):
            return render(
                request,
                "register.html",
                {
                    "messages": [
                        {
                            "message": "All fields are required.",
                            "tags": "danger",
                        }
                    ]
                },
            )

        try:
            user = register_user(username, first_name, last_name, password1, email)
            login(request, user)
            return redirect("landing")
        except Exception as e:
            logger.error("Error creating user: %s", str(e))
            return render(
                request,
                "register.html",
                {
                    "messages": [
                        {
                            "message": "An error occurred while creating the user. Please try again later.",
                            "tags": "danger",
                        }
                    ]
                },
            )

    return render(request, "register.html")


def login_view(request: WSGIRequest) -> HttpResponse:
    if request.method == "POST":
        # Handle login logic here
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        username = username.strip()
        # password = password.strip() Idk about this, are leading and trailing spaces allowed in passwords?

        if any(not field for field in [username, password]):
            return render(
                request,
                "login.html",
                {
                    "messages": [
                        {
                            "message": "All fields are required.",
                            "tags": "danger",
                        }
                    ]
                },
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(
                request,
                "login.html",
                {
                    "messages": [
                        {
                            "message": "Invalid username or password.",
                            "tags": "danger",
                        }
                    ]
                },
            )

        login(request, user)
        return redirect("landing")
    return render(request, "login.html")


def logout_view(request: WSGIRequest) -> HttpResponse:
    logout(request)
    return redirect("login")
