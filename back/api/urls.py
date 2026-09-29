from django.urls import path

from .views import health, predict_digit, predict_postal_code

urlpatterns = [
    path("health/", health, name="health"),
    path("v1/predictions/digit/", predict_digit, name="predict-digit"),
    path("v1/predictions/postal-code/", predict_postal_code, name="predict-postal-code"),
]
