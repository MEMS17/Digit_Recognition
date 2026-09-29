import uuid
from datetime import timedelta

import httpx
from bson.binary import Binary
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from pymongo import MongoClient


@require_GET
def health(request):
    """Process liveness only: no MongoDB connection or model loading."""
    return JsonResponse({"status": "ok", "service": "back"})


def _error(status, code, message):
    return JsonResponse({"error": {"code": code, "message": message, "fields": {}}}, status=status)


def _infer(request, route, input_kind=None):
    if set(request.FILES) != {"image"}:
        return _error(400, "invalid_field", "Le champ image est requis et unique.")
    image = request.FILES["image"]
    if image.size > 5 * 1024 * 1024:
        return _error(413, "image_too_large", "L'image dépasse 5 MiB.")
    image_bytes = image.read()
    data = {"input_kind": input_kind} if input_kind else {}
    try:
        response = httpx.post(f"{settings.IA_SERVICE_URL}{route}", files={"image": (image.name, image_bytes, image.content_type)}, data=data, timeout=httpx.Timeout(30, connect=2))
    except httpx.HTTPError:
        return _error(503, "model_unavailable", "Le service IA est indisponible.")
    if response.status_code != 200:
        detail = response.json().get("detail", {}) if response.headers.get("content-type", "").startswith("application/json") else {}
        return _error(response.status_code if response.status_code < 500 else 503, detail.get("code", "model_unavailable"), detail.get("message", "L'inférence a échoué."))
    result = response.json()
    now = timezone.now()
    prediction_id = str(uuid.uuid4())
    document = {"_id": prediction_id, **result, "image_bytes": Binary(image_bytes), "created_at": now, "expires_at": now + timedelta(days=30)}
    try:
        MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)[settings.MONGODB_DATABASE].predictions.insert_one(document)
    except Exception:
        return _error(503, "storage_unavailable", "Le stockage est indisponible.")
    document.pop("image_bytes", None)
    document["prediction_id"] = document.pop("_id")
    document.pop("expires_at", None)
    return JsonResponse(document, status=201)


@require_POST
def predict_digit(request):
    return _infer(request, "/internal/v1/infer/digit/")


@require_POST
def predict_postal_code(request):
    input_kind = request.POST.get("input_kind")
    if input_kind not in {"crop", "envelope"}:
        return _error(400, "invalid_field", "input_kind doit valoir crop ou envelope.")
    return _infer(request, "/internal/v1/infer/postal-code/", input_kind)
