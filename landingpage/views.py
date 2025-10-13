from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render


# Create your views here.
def landing_view(request: WSGIRequest) -> HttpResponse:
    return render(
        request,
        "landing.html",
    )
