"""Validated, resumable import of MNIST CSV files into MongoDB.

The script deliberately stores 784 pixels as BSON Binary instead of an array of
784 integers: it is compact, deterministic and easy to reconstruct as uint8.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from bson.binary import Binary
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid

DATASET_VERSION = "mnist-csv-pjreddie-v1"
EXPECTED_ROWS = {"train": 60_000, "test": 10_000}
EXPECTED_COLLECTIONS = {"train": "mnist_train", "test": "mnist_test"}
DEFAULT_URLS = {
    # CSV mirror of the pjreddie distribution. The original host currently
    # rejects automated HTTPS downloads with 403 from the Docker network.
    "train": "https://raw.githubusercontent.com/phoebetronic/mnist/main/mnist_train.csv.zip",
    "test": "https://raw.githubusercontent.com/phoebetronic/mnist/main/mnist_test.csv.zip",
}
PIXEL_COUNT = 28 * 28


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_if_missing(url: str, destination: Path) -> None:
    """Download atomically, preserving a verified existing local source."""
    if destination.exists():
        print(f"Source locale conservée : {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
        temporary = Path(temp.name)
    try:
        print(f"Téléchargement : {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "Digit-Recognition-MNIST-Importer/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        if zipfile.is_zipfile(temporary):
            with zipfile.ZipFile(temporary) as archive:
                names = [name for name in archive.namelist() if Path(name).name == destination.name]
                if len(names) != 1:
                    raise ValueError(f"Archive invalide : {destination.name} introuvable de manière unique")
                with archive.open(names[0]) as source, destination.open("wb") as target:
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk)
            temporary.unlink()
        else:
            temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def rows_from_csv(path: Path, split: str) -> Iterator[tuple[int, int, bytes]]:
    """Yield (source index, label, 784 uint8 pixels), rejecting malformed rows."""
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        for index, row in enumerate(reader):
            if len(row) != PIXEL_COUNT + 1:
                raise ValueError(f"{split}, ligne {index + 1}: {len(row)} colonnes, 785 attendues")
            try:
                values = [int(value) for value in row]
            except ValueError as error:
                raise ValueError(f"{split}, ligne {index + 1}: valeur non entière") from error
            label, pixels = values[0], values[1:]
            if label not in range(10):
                raise ValueError(f"{split}, ligne {index + 1}: label hors [0,9]")
            if any(pixel < 0 or pixel > 255 for pixel in pixels):
                raise ValueError(f"{split}, ligne {index + 1}: pixel hors [0,255]")
            yield index, label, bytes(pixels)


def ensure_collection(db, name: str) -> Collection:
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "schema_version", "dataset_version", "source_index", "label", "pixels",
                "width", "height", "pixel_sha256", "source_sha256", "imported_at",
            ],
            "properties": {
                "schema_version": {"bsonType": "int", "enum": [1]},
                "dataset_version": {"bsonType": "string"},
                "source_index": {"bsonType": "int", "minimum": 0},
                "label": {"bsonType": "int", "minimum": 0, "maximum": 9},
                "pixels": {"bsonType": "binData"},
                "width": {"bsonType": "int", "enum": [28]},
                "height": {"bsonType": "int", "enum": [28]},
                "pixel_sha256": {"bsonType": "string"},
                "source_sha256": {"bsonType": "string"},
                "imported_at": {"bsonType": "date"},
            },
        }
    }
    try:
        db.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")
    except CollectionInvalid:
        # Existing collections must be explicitly upgraded by an administrator;
        # silently weakening an existing validator would hide schema mistakes.
        pass
    collection = db[name]
    collection.create_index(
        [("dataset_version", ASCENDING), ("source_index", ASCENDING)],
        unique=True,
        name="dataset_source_index_unique",
    )
    collection.create_index(
        [("dataset_version", ASCENDING), ("label", ASCENDING)],
        name="dataset_label",
    )
    return collection


def build_document(split: str, index: int, label: int, pixels: bytes, source_sha: str, now: datetime) -> dict:
    return {
        "_id": f"{DATASET_VERSION}:{split}:{index:06d}",
        "schema_version": 1,
        "dataset_version": DATASET_VERSION,
        "source_index": index,
        "label": label,
        "pixels": Binary(pixels),
        "width": 28,
        "height": 28,
        "pixel_sha256": hashlib.sha256(pixels).hexdigest(),
        "source_sha256": source_sha,
        "imported_at": now,
    }


def insert_batch(collection: Collection, documents: list[dict]) -> tuple[int, int]:
    existing = {
        doc["_id"]: doc
        for doc in collection.find(
            {"_id": {"$in": [document["_id"] for document in documents]}},
            {"_id": 1, "label": 1, "pixels": 1, "pixel_sha256": 1, "source_sha256": 1,
             "dataset_version": 1, "source_index": 1, "width": 1, "height": 1},
        )
    }
    pending: list[dict] = []
    skipped = 0
    comparison_fields = ("label", "pixels", "pixel_sha256", "source_sha256", "dataset_version", "source_index", "width", "height")
    for document in documents:
        found = existing.get(document["_id"])
        if found is None:
            pending.append(document)
        elif any(
            (bytes(found[field]) if field == "pixels" else found.get(field)) !=
            (bytes(document[field]) if field == "pixels" else document[field])
            for field in comparison_fields
        ):
            raise RuntimeError(f"Conflit pour {document['_id']}: document existant différent, aucun écrasement")
        else:
            skipped += 1
    if pending:
        collection.insert_many(pending, ordered=True)
    return len(pending), skipped


def import_split(db, split: str, source: Path, batch_size: int) -> None:
    source_sha = sha256_file(source)
    collection = ensure_collection(db, EXPECTED_COLLECTIONS[split])
    inserted = skipped = 0
    labels: Counter[int] = Counter()
    batch: list[dict] = []
    now = datetime.now(UTC)
    for index, label, pixels in rows_from_csv(source, split):
        labels[label] += 1
        batch.append(build_document(split, index, label, pixels, source_sha, now))
        if len(batch) == batch_size:
            new, old = insert_batch(collection, batch)
            inserted += new
            skipped += old
            batch.clear()
    if batch:
        new, old = insert_batch(collection, batch)
        inserted += new
        skipped += old

    count = sum(labels.values())
    if count != EXPECTED_ROWS[split]:
        raise RuntimeError(f"{split}: {count} lignes lues, {EXPECTED_ROWS[split]} attendues")
    if set(labels) != set(range(10)):
        raise RuntimeError(f"{split}: labels présents {sorted(labels)}, 0 à 9 attendus")
    stored = collection.count_documents({"dataset_version": DATASET_VERSION})
    if stored != EXPECTED_ROWS[split]:
        raise RuntimeError(f"{split}: {stored} documents MongoDB, {EXPECTED_ROWS[split]} attendus")
    print(f"{split}: {count} lignes, {inserted} insérées, {skipped} déjà identiques, labels={dict(sorted(labels.items()))}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importe MNIST CSV dans MongoDB de manière relançable.")
    parser.add_argument("--train", type=Path, default=Path("data/raw/mnist_train.csv"))
    parser.add_argument("--test", type=Path, default=Path("data/raw/mnist_test.csv"))
    parser.add_argument("--download", action="store_true", help="Télécharge les CSV manquants depuis pjreddie.com.")
    parser.add_argument("--batch-size", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size doit être positif")
    for split, path in (("train", args.train), ("test", args.test)):
        if args.download:
            download_if_missing(DEFAULT_URLS[split], path)
        if not path.is_file():
            raise FileNotFoundError(f"Source {split} absente : {path}. Ajoutez --download ou fournissez le fichier.")
    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://mongo:27017"), serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        db = client[os.environ.get("MONGODB_DATABASE", "postal_ocr")]
        import_split(db, "train", args.train, args.batch_size)
        import_split(db, "test", args.test, args.batch_size)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Import MNIST interrompu : {error}", file=sys.stderr)
        raise
