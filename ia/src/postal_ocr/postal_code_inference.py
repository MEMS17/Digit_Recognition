"""Run the frozen MNIST CNN on five digit regions extracted from a postal crop."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps

from postal_ocr.segment_postal_code import segment_image

MODEL_PATH = Path("models/mnist_tuning_v1/cnn_tuned.keras")
MODEL_VERSION = "mnist-cnn-a-v1"
PREPROCESSING_VERSION = "postal-crop-component-v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_digit(grayscale: np.ndarray, box: dict, threshold: int) -> np.ndarray:
    """Convert one dark component into a MNIST-like 28x28 white-on-black image."""
    padding = 3
    y_start = max(0, box["y"] - padding)
    y_end = min(grayscale.shape[0], box["y"] + box["height"] + padding)
    x_start = max(0, box["x"] - padding)
    x_end = min(grayscale.shape[1], box["x"] + box["width"] + padding)
    crop = grayscale[y_start:y_end, x_start:x_end]
    foreground = np.where(crop < threshold, 255 - crop, 0).astype(np.uint8)
    active_rows, active_columns = np.where(foreground > 0)
    if not len(active_rows) or not len(active_columns):
        raise ValueError("La composante segmentée ne contient aucun pixel sombre")
    foreground = foreground[active_rows.min():active_rows.max() + 1, active_columns.min():active_columns.max() + 1]
    height, width = foreground.shape
    scale = 20 / max(height, width)
    resized_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = Image.fromarray(foreground).resize(resized_size, Image.Resampling.LANCZOS)
    canvas = np.zeros((28, 28), dtype=np.uint8)
    offset_x = (28 - resized_size[0]) // 2
    offset_y = (28 - resized_size[1]) // 2
    canvas[offset_y:offset_y + resized_size[1], offset_x:offset_x + resized_size[0]] = np.asarray(resized)
    return canvas.astype(np.float32) / 255.0


def postal_bbox(boxes: list[dict]) -> dict[str, int]:
    left = min(box["x"] for box in boxes)
    top = min(box["y"] for box in boxes)
    right = max(box["x"] + box["width"] for box in boxes)
    bottom = max(box["y"] + box["height"] for box in boxes)
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def rectangle(box: dict) -> dict[str, int]:
    return {key: int(box[key]) for key in ("x", "y", "width", "height")}


def load_model(model_path: Path = MODEL_PATH) -> tf.keras.Model:
    if not model_path.is_file():
        raise FileNotFoundError(f"Artefact CNN introuvable : {model_path}")
    return tf.keras.models.load_model(model_path)


def predict_postal_code(image_path: Path, model: tf.keras.Model) -> dict:
    segmentation = segment_image(image_path)
    common = {
        "task": "postal_code",
        "image": segmentation["image"],
        "model_version": MODEL_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "reference_check": {"status": "not_checked", "version": None},
    }
    if segmentation["status"] != "segmented":
        return {
            **common,
            "value": None,
            "status": "unreadable",
            "score": None,
            "bbox": None,
            "reasons": [segmentation["reason"]],
            "digits": [],
        }
    with Image.open(image_path) as source:
        grayscale = np.asarray(ImageOps.exif_transpose(source).convert("L"))
    normalized = np.stack([normalize_digit(grayscale, box, segmentation["threshold"]) for box in segmentation["boxes"]])
    probabilities = model.predict(normalized.reshape(-1, 28, 28, 1), verbose=0)
    labels = np.argmax(probabilities, axis=1)
    scores = np.max(probabilities, axis=1)
    digits = [
        {"value": str(label), "score": float(score), "bbox": rectangle(postal_box)}
        for label, score, postal_box in zip(labels, scores, segmentation["boxes"])
    ]
    return {
        **common,
        "value": "".join(digit["value"] for digit in digits),
        "status": "needs_review",
        "score": float(np.min(scores)),
        "bbox": postal_bbox(segmentation["boxes"]),
        "reasons": ["acceptance_policy_unvalidated"],
        "digits": digits,
    }
