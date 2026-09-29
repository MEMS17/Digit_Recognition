"""Fine-tune the frozen MNIST candidate on synthetic postal digits without using test."""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps
from sklearn.metrics import accuracy_score, classification_report, f1_score

from postal_ocr.postal_code_inference import MODEL_PATH, file_sha256, normalize_digit
from postal_ocr.segment_postal_code import segment_image

SEED = 42
OUTPUT_DIRECTORY = Path("models/postal_digit_synthetic_v1")


def set_seeds() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    tf.keras.utils.set_random_seed(SEED)


def load_split(manifest_path: Path, images_root: Path, split: str) -> tuple[np.ndarray, np.ndarray]:
    records = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    selected = [
        record for record in records
        if record["split"] == split and record["annotation_status"] == "verified" and record["label_status"] == "labeled"
    ]
    if not selected:
        raise RuntimeError(f"Aucune image labeled/verified dans le split {split}")
    images: list[np.ndarray] = []
    labels: list[int] = []
    for record in selected:
        boxes = record.get("digit_bboxes")
        if not isinstance(boxes, list) or len(boxes) != 5:
            raise RuntimeError(f"digit_bboxes absent ou invalide pour {record['id']}")
        image_path = images_root / record["image_path"]
        segmentation = segment_image(image_path)
        with Image.open(image_path) as source:
            grayscale = np.asarray(ImageOps.exif_transpose(source).convert("L"))
        for digit, box in zip(record["postal_code"], boxes):
            images.append(normalize_digit(grayscale, box, segmentation["threshold"]))
            labels.append(int(digit))
    return np.stack(images), np.asarray(labels, dtype=np.uint8)


def metrics(model: tf.keras.Model, images: np.ndarray, labels: np.ndarray) -> dict:
    predictions = np.argmax(model.predict(images.reshape(-1, 28, 28, 1), verbose=0), axis=1)
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "f1_macro": float(f1_score(labels, predictions, average="macro")),
        "classification_report": classification_report(labels, predictions, output_dict=True, zero_division=0),
    }


def build_adapted_model() -> tf.keras.Model:
    base = tf.keras.models.load_model(MODEL_PATH)
    inputs = tf.keras.Input(shape=(28, 28, 1))
    augmented = tf.keras.Sequential(
        [
            tf.keras.layers.RandomRotation(0.06, fill_mode="constant"),
            tf.keras.layers.RandomTranslation(0.06, 0.06, fill_mode="constant"),
        ],
        name="postal_augmentation",
    )(inputs)
    outputs = base(augmented)
    model = tf.keras.Model(inputs, outputs, name="postal_digit_cnn")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description="Adapte le CNN MNIST aux chiffres postaux synthétiques train/validation.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.epochs < 1:
        raise ValueError("--epochs doit être positif")
    if OUTPUT_DIRECTORY.exists() and any(OUTPUT_DIRECTORY.iterdir()) and not args.force:
        raise FileExistsError(f"{OUTPUT_DIRECTORY} existe déjà ; utilisez --force après archivage")
    set_seeds()
    train_images, train_labels = load_split(args.manifest, args.images_root, "train")
    validation_images, validation_labels = load_split(args.manifest, args.images_root, "validation")
    baseline = tf.keras.models.load_model(MODEL_PATH)
    baseline_metrics = metrics(baseline, validation_images, validation_labels)
    model = build_adapted_model()
    history = model.fit(
        train_images.reshape(-1, 28, 28, 1),
        train_labels,
        validation_data=(validation_images.reshape(-1, 28, 28, 1), validation_labels),
        batch_size=64,
        epochs=args.epochs,
        verbose=2,
        callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=5, restore_best_weights=True)],
    )
    adapted_metrics = metrics(model, validation_images, validation_labels)
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    model.save(OUTPUT_DIRECTORY / "postal_digit_cnn.keras")
    result = {
        "experiment_id": "postal_digit_synthetic_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "test_set_used": False,
        "random_state": SEED,
        "source_model": {"artifact": str(MODEL_PATH), "sha256": file_sha256(MODEL_PATH)},
        "train_count": int(train_images.shape[0]),
        "validation_count": int(validation_images.shape[0]),
        "preprocessing": "ground-truth digit bbox -> postal-crop-component-v1 normalization 28x28",
        "baseline_validation": baseline_metrics,
        "adapted_validation": adapted_metrics,
        "parameters": {"learning_rate": 1e-4, "batch_size": 64, "epochs_max": args.epochs, "early_stopping_patience": 5, "rotation": 0.06, "translation": 0.06},
        "history": {name: [float(value) for value in values] for name, values in history.history.items()},
        "selected_candidate": "postal_digit_cnn.keras" if adapted_metrics["accuracy"] >= baseline_metrics["accuracy"] else "mnist_tuning_v1/cnn_tuned.keras",
    }
    (OUTPUT_DIRECTORY / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"CNN MNIST validation : accuracy={baseline_metrics['accuracy']:.4f}, f1_macro={baseline_metrics['f1_macro']:.4f}")
    print(f"CNN adapté validation : accuracy={adapted_metrics['accuracy']:.4f}, f1_macro={adapted_metrics['f1_macro']:.4f}")
    print(f"Candidat retenu : {result['selected_candidate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
