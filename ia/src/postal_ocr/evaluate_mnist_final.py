"""Evaluate the frozen MNIST CNN once on the held-out test collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import tensorflow as tf
from pymongo import MongoClient
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from postal_ocr.mnist_import import DATASET_VERSION
from postal_ocr.train_mnist_models import prediction_latency_ms

MODEL_PATH = Path("models/mnist_tuning_v1/cnn_tuned.keras")
OUTPUT_DIRECTORY = Path("models/mnist_final_evaluation_v1")
RESULT_PATH = OUTPUT_DIRECTORY / "results.json"
EXPECTED_TEST_COUNT = 10_000


def load_test_set(db) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = list(
        db.mnist_test.find(
            {"dataset_version": DATASET_VERSION}, {"source_index": 1, "label": 1, "pixels": 1}
        ).sort("source_index", 1)
    )
    if len(rows) != EXPECTED_TEST_COUNT:
        raise RuntimeError(f"mnist_test contient {len(rows)} documents ; {EXPECTED_TEST_COUNT} attendus")
    indexes = np.array([row["source_index"] for row in rows], dtype=np.int32)
    if len(np.unique(indexes)) != EXPECTED_TEST_COUNT:
        raise RuntimeError("mnist_test contient des source_index dupliqués")
    images = np.stack([np.frombuffer(row["pixels"], dtype=np.uint8) for row in rows])
    if images.shape != (EXPECTED_TEST_COUNT, 784):
        raise RuntimeError(f"Dimensions de mnist_test invalides : {images.shape}")
    labels = np.array([row["label"] for row in rows], dtype=np.uint8)
    if np.any((labels < 0) | (labels > 9)):
        raise RuntimeError("mnist_test contient un label hors de l'intervalle [0, 9]")
    return images.astype(np.float32) / 255.0, labels, indexes


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Évalue une fois le CNN MNIST gelé sur mnist_test.")
    parser.add_argument("--force", action="store_true", help="Autorise le remplacement du résultat final local.")
    args = parser.parse_args()
    if RESULT_PATH.exists() and not args.force:
        raise FileExistsError(f"{RESULT_PATH} existe déjà ; ne relancez pas le test final sans décision explicite")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Artefact CNN gelé introuvable : {MODEL_PATH}")

    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://mongo:27017"), serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        images, labels, indexes = load_test_set(client[os.environ.get("MONGODB_DATABASE", "postal_ocr")])
    finally:
        client.close()

    model = tf.keras.models.load_model(MODEL_PATH)
    started = time.perf_counter()
    probabilities = model.predict(images.reshape(-1, 28, 28, 1), verbose=0)
    prediction_seconds = time.perf_counter() - started
    predictions = np.argmax(probabilities, axis=1).astype(np.uint8)
    error_positions = np.flatnonzero(predictions != labels)
    examples = [
        {
            "source_index": int(indexes[position]),
            "expected": int(labels[position]),
            "predicted": int(predictions[position]),
            "confidence": float(probabilities[position, predictions[position]]),
        }
        for position in error_positions[:25]
    ]
    result = {
        "experiment_id": "mnist_final_evaluation_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "purpose": "final held-out test evaluation after candidate freeze",
        "test_set_used": True,
        "test_count": int(images.shape[0]),
        "model": {
            "name": "cnn_a",
            "artifact": str(MODEL_PATH),
            "sha256": sha256(MODEL_PATH),
            "parameters": {"learning_rate": 0.001, "dropout": 0.25, "batch_size": 128},
        },
        "preprocessing": "pixels uint8 MongoDB -> float32 / 255.0; reshape 28x28x1; aucune augmentation",
        "metrics": {
            "accuracy": float(accuracy_score(labels, predictions)),
            "f1_macro": float(f1_score(labels, predictions, average="macro")),
            "prediction_seconds_for_test_set": prediction_seconds,
            "single_prediction_latency_ms": prediction_latency_ms(model, images, cnn=True),
            "classification_report": classification_report(labels, predictions, output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
        },
        "error_count": int(error_positions.size),
        "error_examples_first_25_by_source_index": examples,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"CNN final : accuracy={result['metrics']['accuracy']:.4f}, f1_macro={result['metrics']['f1_macro']:.4f}")
    print(f"Résultats écrits dans {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
