"""Validate the local JSONL manifest used for postal-code experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps

CODE_PATTERN = re.compile(r"^[0-9]{5}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SPLITS = {"train", "validation", "test"}
INPUT_KINDS = {"crop", "envelope"}
SOURCE_KINDS = {"synthetic", "authorized"}
ANNOTATION_STATUSES = {"verified", "pending_review"}
LABEL_STATUSES = {"labeled", "absent", "illegible", "ambiguous"}
REQUIRED_FIELDS = {
    "id", "image_path", "image_sha256", "width", "height", "input_kind", "split",
    "source_kind", "usage_rights", "source_envelope_id", "writer_id", "layout_family",
    "annotation_version", "annotation_status", "label_status", "postal_code", "postal_bbox",
}


def fail(line_number: int, message: str) -> ValueError:
    return ValueError(f"Ligne {line_number} : {message}")


def safe_image_path(value: object, line_number: int) -> PurePosixPath:
    if not isinstance(value, str):
        raise fail(line_number, "image_path doit être une chaîne")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise fail(line_number, "image_path doit être un chemin relatif PNG ou JPEG sous images-root")
    return path


def validate_bbox(value: object, width: int, height: int, line_number: int) -> None:
    if not isinstance(value, dict) or set(value) != {"x", "y", "width", "height"}:
        raise fail(line_number, "postal_bbox doit contenir exactement x, y, width et height")
    if not all(isinstance(value[key], int) and not isinstance(value[key], bool) for key in value):
        raise fail(line_number, "les coordonnées postal_bbox doivent être des entiers")
    x, y, box_width, box_height = value["x"], value["y"], value["width"], value["height"]
    if x < 0 or y < 0 or box_width <= 0 or box_height <= 0 or x + box_width > width or y + box_height > height:
        raise fail(line_number, "postal_bbox est hors des bornes de l'image")


def require_string(record: dict, field: str, line_number: int) -> str:
    value = record[field]
    if not isinstance(value, str) or not value.strip():
        raise fail(line_number, f"{field} doit être une chaîne non vide")
    return value


def validate_record(record: object, line_number: int) -> PurePosixPath:
    if not isinstance(record, dict):
        raise fail(line_number, "chaque ligne doit être un objet JSON")
    missing = REQUIRED_FIELDS - record.keys()
    if missing:
        raise fail(line_number, f"champs obligatoires absents : {', '.join(sorted(missing))}")
    for field in ("id", "usage_rights", "source_envelope_id", "writer_id", "layout_family", "annotation_version"):
        require_string(record, field, line_number)
    path = safe_image_path(record["image_path"], line_number)
    if not isinstance(record["image_sha256"], str) or not SHA256_PATTERN.fullmatch(record["image_sha256"]):
        raise fail(line_number, "image_sha256 doit être un SHA-256 hexadécimal en minuscules")
    if not all(isinstance(record[field], int) and not isinstance(record[field], bool) and record[field] > 0 for field in ("width", "height")):
        raise fail(line_number, "width et height doivent être des entiers positifs")
    for field, allowed in (("input_kind", INPUT_KINDS), ("split", SPLITS), ("source_kind", SOURCE_KINDS), ("annotation_status", ANNOTATION_STATUSES), ("label_status", LABEL_STATUSES)):
        if record[field] not in allowed:
            raise fail(line_number, f"{field} doit valoir l'une de ces valeurs : {', '.join(sorted(allowed))}")
    if record["label_status"] == "labeled":
        if not isinstance(record["postal_code"], str) or not CODE_PATTERN.fullmatch(record["postal_code"]):
            raise fail(line_number, "postal_code doit contenir exactement cinq chiffres pour une ligne labeled")
        validate_bbox(record["postal_bbox"], record["width"], record["height"], line_number)
    elif record["postal_code"] is not None or record["postal_bbox"] is not None:
        raise fail(line_number, "postal_code et postal_bbox doivent être null hors d'une ligne labeled")
    return path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_image(record: dict, path: Path, line_number: int) -> None:
    if not path.is_file():
        raise fail(line_number, f"image introuvable : {path}")
    if file_sha256(path) != record["image_sha256"]:
        raise fail(line_number, "l'empreinte SHA-256 de l'image ne correspond pas")
    try:
        with Image.open(path) as image:
            oriented = ImageOps.exif_transpose(image)
            dimensions = oriented.size
            image_format = image.format
    except OSError as error:
        raise fail(line_number, f"image illisible : {error}") from error
    if image_format not in {"JPEG", "PNG"}:
        raise fail(line_number, "le contenu décodé doit être JPEG ou PNG")
    if dimensions != (record["width"], record["height"]):
        raise fail(line_number, f"dimensions orientées attendues {(record['width'], record['height'])}, obtenues {dimensions}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valide un manifeste JSONL de courriers postaux.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--check-images", action="store_true")
    args = parser.parse_args()
    if not args.manifest.is_file():
        raise FileNotFoundError(f"Manifeste introuvable : {args.manifest}")

    seen_ids: set[str] = set()
    group_splits: dict[tuple[str, str], set[str]] = defaultdict(set)
    counts: Counter[tuple[str, str]] = Counter()
    records: list[tuple[int, dict, PurePosixPath]] = []
    for line_number, raw_line in enumerate(args.manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            raise fail(line_number, "les lignes vides ne sont pas admises")
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise fail(line_number, f"JSON invalide : {error.msg}") from error
        path = validate_record(record, line_number)
        if record["id"] in seen_ids:
            raise fail(line_number, f"id dupliqué : {record['id']}")
        seen_ids.add(record["id"])
        for group_field in ("source_envelope_id", "writer_id", "layout_family"):
            group_splits[(group_field, record[group_field])].add(record["split"])
        counts[(record["split"], record["label_status"])] += 1
        records.append((line_number, record, path))
    if not records:
        raise ValueError("Le manifeste est vide")
    leaking_groups = [f"{field}={value}" for (field, value), splits in group_splits.items() if len(splits) > 1]
    if leaking_groups:
        raise ValueError("Fuite entre splits : " + ", ".join(sorted(leaking_groups)))
    if args.check_images:
        for line_number, record, relative_path in records:
            check_image(record, args.images_root / Path(relative_path), line_number)
    print(f"Manifeste valide : {len(records)} lignes")
    for split in sorted(SPLITS):
        statuses = ", ".join(f"{status}={counts[(split, status)]}" for status in sorted(LABEL_STATUSES))
        print(f"{split}: {statuses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
