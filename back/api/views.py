from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """Process liveness only: no MongoDB connection or model loading."""
    return JsonResponse({"status": "ok", "service": "back"})
