"""Create and validate the deterministic MNIST train/validation manifest."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime

import numpy as np
from pymongo import MongoClient
from sklearn.model_selection import StratifiedShuffleSplit

from postal_ocr.mnist_import import DATASET_VERSION

MANIFEST_ID = "mnist_train_val_v1"
RANDOM_STATE = 42
VALIDATION_SIZE = 10_000


def indexes_sha256(indexes: np.ndarray) -> str:
    return hashlib.sha256(",".join(map(str, indexes.tolist())).encode("ascii")).hexdigest()


def build_manifest(db) -> dict:
    rows = list(
        db.mnist_train.find(
            {"dataset_version": DATASET_VERSION}, {"source_index": 1, "label": 1}
        ).sort("source_index", 1)
    )
    if len(rows) != 60_000:
        raise RuntimeError(f"mnist_train contient {len(rows)} documents ; 60000 attendus")
    indexes = np.array([row["source_index"] for row in rows], dtype=np.int32)
    labels = np.array([row["label"] for row in rows], dtype=np.int8)
    if not np.array_equal(indexes, np.arange(60_000, dtype=np.int32)):
        raise RuntimeError("Les source_index MNIST train ne sont pas continus de 0 à 59999")
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=VALIDATION_SIZE, random_state=RANDOM_STATE)
    train_positions, validation_positions = next(splitter.split(indexes, labels))
    train_indexes = np.sort(indexes[train_positions])
    validation_indexes = np.sort(indexes[validation_positions])
    return {
        "_id": MANIFEST_ID,
        "schema_version": 1,
        "dataset_version": DATASET_VERSION,
        "source_collection": "mnist_train",
        "method": "StratifiedShuffleSplit",
        "random_state": RANDOM_STATE,
        "train_source_indexes": train_indexes.tolist(),
        "validation_source_indexes": validation_indexes.tolist(),
        "train_count": int(train_indexes.size),
        "validation_count": int(validation_indexes.size),
        "train_indexes_sha256": indexes_sha256(train_indexes),
        "validation_indexes_sha256": indexes_sha256(validation_indexes),
        "created_at": datetime.now(UTC),
    }


def immutable_view(manifest: dict) -> dict:
    fields = (
        "schema_version", "dataset_version", "source_collection", "method", "random_state",
        "train_source_indexes", "validation_source_indexes", "train_count", "validation_count",
        "train_indexes_sha256", "validation_indexes_sha256",
    )
    return {field: manifest[field] for field in fields}


def main() -> int:
    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://mongo:27017"), serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        db = client[os.environ.get("MONGODB_DATABASE", "postal_ocr")]
        candidate = build_manifest(db)
        collection = db.dataset_manifests
        existing = collection.find_one({"_id": MANIFEST_ID})
        if existing is None:
            collection.insert_one(candidate)
            print(f"Manifeste créé : {MANIFEST_ID}")
        elif immutable_view(existing) != immutable_view(candidate):
            raise RuntimeError("Le manifeste existant diffère : aucun écrasement automatique")
        else:
            print(f"Manifeste déjà identique : {MANIFEST_ID}")
        print(
            f"train={candidate['train_count']} validation={candidate['validation_count']} "
            f"seed={RANDOM_STATE} validation_sha256={candidate['validation_indexes_sha256']}"
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
