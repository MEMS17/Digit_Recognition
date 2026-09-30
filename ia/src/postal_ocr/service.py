"""Private FastAPI inference service used by the Django backend over Docker."""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
from huggingface_hub import hf_hub_download

from postal_ocr.postal_code_inference import (
    MODEL_PATH as MNIST_MODEL_PATH,
    MODEL_VERSION as MNIST_MODEL_VERSION,
    PREPROCESSING_VERSION,
    load_model,
    normalize_digit,
    predict_postal_code,
)

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_EDGE = 12_000
MAX_IMAGE_PIXELS = 12_000_000
MODEL_ROOT = Path(os.environ.get("MODEL_ROOT", "models"))
MNIST_MODEL_PATH = Path(os.environ.get("MNIST_MODEL_PATH", str(MNIST_MODEL_PATH)))
POSTAL_MODEL_PATH = Path(os.environ.get("POSTAL_MODEL_PATH", "models/postal_digit_synthetic_v1/postal_digit_cnn.keras"))
MNIST_MODEL_FILENAME = os.environ.get("MNIST_MODEL_FILENAME", "mnist/cnn_tuned.keras")
POSTAL_MODEL_FILENAME = os.environ.get("POSTAL_MODEL_FILENAME", "postal/postal_digit_cnn.keras")
POSTAL_MODEL_VERSION = os.environ.get("POSTAL_MODEL_VERSION", "postal-digit-synthetic-v1")

app = FastAPI(title="Postal OCR internal inference", docs_url=None, redoc_url=None, openapi_url=None)


class Models:
    def __init__(self) -> None:
        self.digit: tf.keras.Model | None = None
        self.postal: tf.keras.Model | None = None

    def digit_model(self) -> tf.keras.Model:
        if self.digit is None:
            self.digit = load_model(self._resolve_model(MNIST_MODEL_PATH, MNIST_MODEL_FILENAME))
        return self.digit

    def postal_model(self) -> tf.keras.Model:
        if self.postal is None:
            self.postal = load_model(self._resolve_model(POSTAL_MODEL_PATH, POSTAL_MODEL_FILENAME))
        return self.postal

    @staticmethod
    def _resolve_model(local_path: Path, hub_filename: str) -> Path:
        if local_path.is_file():
            return local_path
        repository = os.getenv("HF_MODEL_REPO")
        if not repository:
            return local_path
        return Path(
            hf_hub_download(
                repo_id=repository,
                filename=hub_filename,
                local_dir=str(MODEL_ROOT),
                token=os.getenv("HF_TOKEN") or None,
            )
        )


models = Models()


@app.get("/health")
async def health() -> dict[str, str]:
    """Internal liveness endpoint; it does not load TensorFlow models."""
    return {"status": "ok", "service": "ia"}


def error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


async def oriented_png(upload: UploadFile) -> tuple[bytes, dict[str, int]]:
    payload = await upload.read()
    if not payload:
        raise error(422, "invalid_image", "L'image est vide.")
    if len(payload) > MAX_FILE_BYTES:
        raise error(413, "image_too_large", "L'image dépasse 5 MiB.")
    try:
        with Image.open(io.BytesIO(payload)) as source:
            image_format = source.format
            if image_format not in {"PNG", "JPEG"}:
                raise error(415, "unsupported_media_type", "Seuls PNG et JPEG sont acceptés.")
            if getattr(source, "n_frames", 1) != 1:
                raise error(415, "unsupported_media_type", "Les images animées ne sont pas acceptées.")
            image = ImageOps.exif_transpose(source).convert("RGBA")
    except HTTPException:
        raise
    except (OSError, ValueError) as exc:
        raise error(422, "invalid_image", "L'image ne peut pas être décodée.") from exc
    width, height = image.size
    if not width or not height or width > MAX_IMAGE_EDGE or height > MAX_IMAGE_EDGE or width * height > MAX_IMAGE_PIXELS:
        raise error(413, "image_too_large", "Les dimensions de l'image dépassent la limite autorisée.")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    output = io.BytesIO()
    background.convert("RGB").save(output, format="PNG")
    return output.getvalue(), {"width": width, "height": height}


def temporary_image(payload: bytes) -> Path:
    temporary = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        temporary.write(payload)
        return Path(temporary.name)
    finally:
        temporary.close()


def infer_digit(path: Path, dimensions: dict[str, int]) -> dict:
    with Image.open(path) as source:
        grayscale = np.asarray(source.convert("L"))
    threshold = int(min(160, max(80, float(np.percentile(grayscale, 90)) - 55)))
    foreground = np.argwhere(grayscale < threshold)
    if foreground.size == 0:
        return {
            "task": "digit", "value": None, "status": "unreadable", "score": None,
            "bbox": {"x": 0, "y": 0, **dimensions}, "image": dimensions,
            "model_version": MNIST_MODEL_VERSION, "preprocessing_version": "digit-component-v1",
            "reasons": ["no_digit_detected"], "reference_check": {"status": "not_applicable", "version": None},
        }
    y_min, x_min = foreground.min(axis=0)
    y_max, x_max = foreground.max(axis=0)
    digit = normalize_digit(
        grayscale,
        {"x": int(x_min), "y": int(y_min), "width": int(x_max - x_min + 1), "height": int(y_max - y_min + 1)},
        threshold,
    )
    probabilities = models.digit_model().predict(digit.reshape(1, 28, 28, 1), verbose=0)[0]
    label = int(np.argmax(probabilities))
    return {
        "task": "digit", "value": str(label), "status": "recognized", "score": float(probabilities[label]),
        "bbox": {"x": 0, "y": 0, **dimensions}, "image": dimensions,
        "model_version": MNIST_MODEL_VERSION, "preprocessing_version": "digit-component-v1",
        "reasons": [], "reference_check": {"status": "not_applicable", "version": None},
    }


@app.post("/internal/v1/infer/digit/")
async def infer_digit_route(image: UploadFile = File(...)) -> dict:
    payload, dimensions = await oriented_png(image)
    path = temporary_image(payload)
    try:
        return infer_digit(path, dimensions)
    except FileNotFoundError as exc:
        raise error(503, "model_unavailable", "Le modèle de chiffre est indisponible.") from exc
    finally:
        path.unlink(missing_ok=True)


@app.post("/internal/v1/infer/postal-code/")
async def infer_postal_route(image: UploadFile = File(...), input_kind: str = Form(...)) -> dict:
    if input_kind == "envelope":
        raise error(503, "capability_unavailable", "La localisation d'enveloppe n'est pas disponible.")
    if input_kind != "crop":
        raise error(400, "invalid_field", "input_kind doit valoir crop ou envelope.")
    payload, dimensions = await oriented_png(image)
    path = temporary_image(payload)
    try:
        result = predict_postal_code(path, models.postal_model(), POSTAL_MODEL_VERSION)
        result["bbox"] = {"x": 0, "y": 0, **dimensions} if result["value"] is not None else None
        result.pop("digits", None)
        return result
    except FileNotFoundError as exc:
        raise error(503, "model_unavailable", "Le modèle postal est indisponible.") from exc
    finally:
        path.unlink(missing_ok=True)
