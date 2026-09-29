"""Tune SVM and CNN from MongoDB while preserving MNIST test untouched."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf
from sklearn.model_selection import GridSearchCV, StratifiedKFold, StratifiedShuffleSplit
from sklearn.svm import SVC

from postal_ocr.mnist_split import MANIFEST_ID
from postal_ocr.train_mnist_models import SEED, evaluate, load_partitions, set_seeds
from pymongo import MongoClient
import os

OUTPUT_DIRECTORY = Path("models/mnist_tuning_v1")
SVM_SUBSET_SIZE = 10_000


def build_cnn(learning_rate: float, dropout: float) -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(28, 28, 1)),
            tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(dropout),
            tf.keras.layers.Dense(10, activation="softmax"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def tune_svm(train_images: np.ndarray, train_labels: np.ndarray, validation_images: np.ndarray, validation_labels: np.ndarray) -> dict:
    subset_positions, _ = next(
        StratifiedShuffleSplit(n_splits=1, train_size=SVM_SUBSET_SIZE, random_state=SEED).split(train_images, train_labels)
    )
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    search = GridSearchCV(
        estimator=SVC(kernel="rbf", cache_size=1000, random_state=SEED),
        param_grid={"C": [3.0, 10.0], "gamma": ["scale", 0.001]},
        scoring="accuracy",
        cv=cv,
        n_jobs=1,
        refit=False,
        return_train_score=False,
    )
    print("GridSearchCV SVM sur 10 000 images train, validation externe inchangée...")
    search_start = time.perf_counter()
    search.fit(train_images[subset_positions], train_labels[subset_positions])
    best_parameters = search.best_params_
    model = SVC(kernel="rbf", cache_size=1000, random_state=SEED, **best_parameters)
    refit_start = time.perf_counter()
    model.fit(train_images, train_labels)
    metrics, matrix = evaluate("svm_tuned", model, validation_images, validation_labels, time.perf_counter() - refit_start)
    metrics["parameters"] = best_parameters
    metrics["confusion_matrix"] = matrix
    metrics["grid_search"] = {
        "subset_size": SVM_SUBSET_SIZE,
        "cv_folds": 3,
        "search_seconds": time.perf_counter() - search_start,
        "best_cv_accuracy": float(search.best_score_),
        "candidates": [
            {"parameters": params, "mean_cv_accuracy": float(score), "rank": int(rank)}
            for params, score, rank in zip(
                search.cv_results_["params"], search.cv_results_["mean_test_score"], search.cv_results_["rank_test_score"]
            )
        ],
    }
    return {"metrics": metrics, "model": model}


def tune_cnn(train_images: np.ndarray, train_labels: np.ndarray, validation_images: np.ndarray, validation_labels: np.ndarray, epochs: int) -> tuple[list[dict], tf.keras.Model]:
    configurations = [
        {"learning_rate": 0.001, "dropout": 0.25},
        {"learning_rate": 0.0005, "dropout": 0.15},
        {"learning_rate": 0.0005, "dropout": 0.35},
    ]
    outcomes: list[dict] = []
    best_model: tf.keras.Model | None = None
    best_accuracy = -1.0
    for configuration in configurations:
        tf.keras.backend.clear_session()
        set_seeds()
        print(f"CNN : {configuration}")
        model = build_cnn(**configuration)
        started = time.perf_counter()
        history = model.fit(
            train_images.reshape(-1, 28, 28, 1), train_labels,
            validation_data=(validation_images.reshape(-1, 28, 28, 1), validation_labels),
            epochs=epochs,
            batch_size=128,
            verbose=2,
            callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=2, restore_best_weights=True)],
        )
        metrics, matrix = evaluate("cnn_tuned", model, validation_images, validation_labels, time.perf_counter() - started, cnn=True)
        metrics["parameters"] = {**configuration, "epochs_max": epochs, "batch_size": 128, "early_stopping_patience": 2}
        metrics["history"] = {key: [float(value) for value in values] for key, values in history.history.items()}
        metrics["confusion_matrix"] = matrix
        outcomes.append(metrics)
        if metrics["accuracy"] > best_accuracy:
            best_accuracy = metrics["accuracy"]
            best_model = model
    if best_model is None:
        raise RuntimeError("Aucun CNN n'a été entraîné")
    return outcomes, best_model


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimise SVM et CNN sans utiliser mnist_test.")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.epochs < 1:
        raise ValueError("--epochs doit être positif")
    if OUTPUT_DIRECTORY.exists() and any(OUTPUT_DIRECTORY.iterdir()) and not args.force:
        raise FileExistsError(f"{OUTPUT_DIRECTORY} existe déjà ; utilisez --force après archivage")
    set_seeds()
    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://mongo:27017"), serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        train_images, train_labels, validation_images, validation_labels = load_partitions(client[os.environ.get("MONGODB_DATABASE", "postal_ocr")])
    finally:
        client.close()
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    svm = tune_svm(train_images, train_labels, validation_images, validation_labels)
    joblib.dump(svm["model"], OUTPUT_DIRECTORY / "svm_tuned.joblib")
    cnn_outcomes, cnn_model = tune_cnn(train_images, train_labels, validation_images, validation_labels, args.epochs)
    cnn_model.save(OUTPUT_DIRECTORY / "cnn_tuned.keras")

    selected_cnn = max(cnn_outcomes, key=lambda result: result["accuracy"])
    candidates = [svm["metrics"], *cnn_outcomes]
    selected = max(candidates, key=lambda result: result["accuracy"])
    result = {
        "experiment_id": "mnist_tuning_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "split_manifest": MANIFEST_ID,
        "random_state": SEED,
        "train_count": int(train_images.shape[0]),
        "validation_count": int(validation_images.shape[0]),
        "test_set_used": False,
        "models": [svm["metrics"], *cnn_outcomes],
        "selected_candidate": {
            "name": selected["name"],
            "accuracy": selected["accuracy"],
            "parameters": selected["parameters"],
            "artifact": "cnn_tuned.keras" if selected["name"] == "cnn_tuned" else "svm_tuned.joblib",
        },
        "best_cnn_validation_accuracy": selected_cnn["accuracy"],
    }
    (OUTPUT_DIRECTORY / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Candidat retenu sur validation : {result['selected_candidate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
