from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from core.models import Options


# Create your views here.
@require_http_methods(["POST"])
def change_theme(request: WSGIRequest) -> HttpResponse:
    theme = request.POST.get("theme", "light")
    options = Options.objects.get(user=request.user)
    options.theme = theme
    options.save()
    return HttpResponse(status=200)
