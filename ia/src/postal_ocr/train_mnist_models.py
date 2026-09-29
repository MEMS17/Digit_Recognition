"""Train three MNIST baselines from MongoDB and evaluate only on validation."""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import sklearn
import tensorflow as tf
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.svm import SVC

from postal_ocr.mnist_import import DATASET_VERSION
from postal_ocr.mnist_split import MANIFEST_ID

SEED = 42
OUTPUT_DIRECTORY = Path("models/mnist_baseline_v1")


def set_seeds() -> None:
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    random.seed(SEED)
    np.random.seed(SEED)
    tf.keras.utils.set_random_seed(SEED)


def load_partitions(db) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    manifest = db.dataset_manifests.find_one({"_id": MANIFEST_ID})
    if manifest is None:
        raise RuntimeError(f"Manifeste absent : {MANIFEST_ID}. Exécutez mnist_split avant l'entraînement.")
    train_indexes = set(manifest["train_source_indexes"])
    validation_indexes = set(manifest["validation_source_indexes"])
    if len(train_indexes) != 50_000 or len(validation_indexes) != 10_000 or train_indexes & validation_indexes:
        raise RuntimeError("Manifeste train/validation invalide")

    rows = list(
        db.mnist_train.find(
            {"dataset_version": DATASET_VERSION}, {"source_index": 1, "label": 1, "pixels": 1}
        ).sort("source_index", 1)
    )
    if len(rows) != 60_000:
        raise RuntimeError(f"mnist_train contient {len(rows)} documents ; 60000 attendus")
    images = np.stack([np.frombuffer(row["pixels"], dtype=np.uint8) for row in rows])
    labels = np.array([row["label"] for row in rows], dtype=np.uint8)
    indexes = np.array([row["source_index"] for row in rows], dtype=np.int32)
    train_mask = np.array([index in train_indexes for index in indexes])
    validation_mask = np.array([index in validation_indexes for index in indexes])
    if not np.all(train_mask | validation_mask):
        raise RuntimeError("Le manifeste ne couvre pas l'ensemble de mnist_train")
    return (
        images[train_mask].astype(np.float32) / 255.0,
        labels[train_mask],
        images[validation_mask].astype(np.float32) / 255.0,
        labels[validation_mask],
    )


def prediction_latency_ms(model, images: np.ndarray, cnn: bool = False) -> dict[str, float]:
    samples = images[:100]
    durations = []
    for sample in samples:
        shaped = sample.reshape(1, 28, 28, 1) if cnn else sample.reshape(1, -1)
        start = time.perf_counter()
        model.predict(shaped, verbose=0) if cnn else model.predict(shaped)
        durations.append((time.perf_counter() - start) * 1000)
    return {"p50": float(np.percentile(durations, 50)), "p95": float(np.percentile(durations, 95))}


def evaluate(name: str, model, validation_images, validation_labels, train_seconds: float, cnn: bool = False) -> tuple[dict, np.ndarray]:
    input_data = validation_images.reshape(-1, 28, 28, 1) if cnn else validation_images
    predictions = model.predict(input_data, verbose=0) if cnn else model.predict(input_data)
    if cnn:
        predictions = np.argmax(predictions, axis=1)
    metrics = {
        "name": name,
        "accuracy": float(accuracy_score(validation_labels, predictions)),
        "f1_macro": float(f1_score(validation_labels, predictions, average="macro")),
        "train_seconds": train_seconds,
        "single_prediction_latency_ms": prediction_latency_ms(model, validation_images, cnn),
        "classification_report": classification_report(validation_labels, predictions, output_dict=True, zero_division=0),
    }
    return metrics, confusion_matrix(validation_labels, predictions).tolist()


def build_cnn() -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(28, 28, 1)),
            tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.25),
            tf.keras.layers.Dense(10, activation="softmax"),
        ]
    )
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description="Entraîne SVM, Random Forest et CNN sur MNIST depuis MongoDB.")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--force", action="store_true", help="Autorise l'écrasement des artefacts baseline locaux.")
    args = parser.parse_args()
    if args.epochs < 1:
        raise ValueError("--epochs doit être positif")
    if OUTPUT_DIRECTORY.exists() and any(OUTPUT_DIRECTORY.iterdir()) and not args.force:
        raise FileExistsError(f"{OUTPUT_DIRECTORY} existe déjà ; utilisez --force après avoir archivé les résultats")

    set_seeds()
    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://mongo:27017"), serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        train_images, train_labels, validation_images, validation_labels = load_partitions(client[os.environ.get("MONGODB_DATABASE", "postal_ocr")])
    finally:
        client.close()
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    results = {
        "experiment_id": "mnist_baseline_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_version": DATASET_VERSION,
        "split_manifest": MANIFEST_ID,
        "random_state": SEED,
        "train_count": int(train_images.shape[0]),
        "validation_count": int(validation_images.shape[0]),
        "preprocessing": "pixels uint8 MongoDB -> float32 / 255.0; aucune augmentation",
        "runtime": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "tensorflow": tf.__version__},
        "models": [],
        "test_set_used": False,
    }

    experiments = [
        ("svm_rbf", SVC(C=10.0, gamma="scale", kernel="rbf", cache_size=1000, random_state=SEED), {"C": 10.0, "gamma": "scale", "kernel": "rbf"}),
        ("random_forest", RandomForestClassifier(n_estimators=200, max_features="sqrt", n_jobs=-1, random_state=SEED), {"n_estimators": 200, "max_features": "sqrt"}),
    ]
    for name, model, parameters in experiments:
        print(f"Entraînement {name}...")
        started = time.perf_counter()
        model.fit(train_images, train_labels)
        metrics, matrix = evaluate(name, model, validation_images, validation_labels, time.perf_counter() - started)
        metrics["parameters"] = parameters
        metrics["confusion_matrix"] = matrix
        results["models"].append(metrics)
        joblib.dump(model, OUTPUT_DIRECTORY / f"{name}.joblib")
        print(f"{name}: accuracy={metrics['accuracy']:.4f}, f1_macro={metrics['f1_macro']:.4f}")

    print("Entraînement cnn...")
    cnn = build_cnn()
    started = time.perf_counter()
    history = cnn.fit(
        train_images.reshape(-1, 28, 28, 1), train_labels,
        validation_data=(validation_images.reshape(-1, 28, 28, 1), validation_labels),
        epochs=args.epochs,
        batch_size=128,
        verbose=2,
        callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=2, restore_best_weights=True)],
    )
    metrics, matrix = evaluate("cnn", cnn, validation_images, validation_labels, time.perf_counter() - started, cnn=True)
    metrics["parameters"] = {"epochs_max": args.epochs, "batch_size": 128, "early_stopping_patience": 2, "architecture": "Conv32-MaxPool-Conv64-MaxPool-Dense128-Dropout0.25"}
    metrics["history"] = {key: [float(value) for value in values] for key, values in history.history.items()}
    metrics["confusion_matrix"] = matrix
    results["models"].append(metrics)
    cnn.save(OUTPUT_DIRECTORY / "cnn.keras")
    print(f"cnn: accuracy={metrics['accuracy']:.4f}, f1_macro={metrics['f1_macro']:.4f}")

    (OUTPUT_DIRECTORY / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Résultats écrits dans {OUTPUT_DIRECTORY / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
