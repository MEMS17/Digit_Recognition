"""Generate a reproducible, non-personal synthetic corpus for postal-code crops."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

IMAGE_SIZE = (640, 180)
DATASET_VERSION = "postal-synthetic-v1"
ANNOTATION_VERSION = "postal-annotation-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def postal_code(rng: random.Random) -> str:
    return "".join(str(rng.randrange(10)) for _ in range(5))


def create_background(rng: random.Random) -> Image.Image:
    width, height = IMAGE_SIZE
    base = np.full((height, width, 3), rng.randrange(232, 251), dtype=np.int16)
    noise = np.random.default_rng(rng.randrange(2**32)).normal(0, rng.uniform(1.0, 4.0), base.shape)
    pixels = np.clip(base + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(pixels, "RGB")
    draw = ImageDraw.Draw(image)
    for _ in range(rng.randrange(2, 7)):
        y = rng.randrange(height)
        shade = rng.randrange(210, 238)
        draw.line((0, y, width, y), fill=(shade, shade, shade), width=1)
    return image


def draw_code(image: Image.Image, code: str, rng: random.Random) -> dict[str, int]:
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=rng.randrange(42, 60))
    x = rng.randrange(70, 150)
    y = rng.randrange(55, 90)
    left, top, right, bottom = draw.textbbox((x, y), code, font=font, stroke_width=1)
    ink = rng.randrange(0, 70)
    draw.text((x, y), code, font=font, fill=(ink, ink, ink), stroke_width=1, stroke_fill=(ink, ink, ink))
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def draw_negative(image: Image.Image, status: str, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)
    if status == "absent":
        draw.line((70, 85, 560, 85), fill=(180, 180, 180), width=2)
    elif status == "illegible":
        draw.text((100, 65), "? ? ? ? ?", font=font, fill=(80, 80, 80))
        for _ in range(16):
            x, y = rng.randrange(80, 520), rng.randrange(55, 125)
            draw.line((x, y, x + rng.randrange(-20, 21), y + rng.randrange(-15, 16)), fill=(20, 20, 20), width=2)
    else:
        draw.text((100, 65), "12345   67890", font=font, fill=(50, 50, 50))


def render_record(index: int, split: str, rng: random.Random, image_path: Path) -> dict:
    image = create_background(rng)
    status_roll = rng.random()
    if status_roll < 0.82:
        label_status = "labeled"
        code = postal_code(rng)
        bbox = draw_code(image, code, rng)
    elif status_roll < 0.88:
        label_status, code, bbox = "absent", None, None
        draw_negative(image, label_status, rng)
    elif status_roll < 0.94:
        label_status, code, bbox = "illegible", None, None
        draw_negative(image, label_status, rng)
    else:
        label_status, code, bbox = "ambiguous", None, None
        draw_negative(image, label_status, rng)
    if rng.random() < 0.35:
        image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.15, 0.65)))
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(image_path, format="PNG", optimize=True)
    return {
        "id": f"{DATASET_VERSION}:{index:06d}",
        "image_path": image_path.relative_to(image_path.parents[2]).as_posix(),
        "image_sha256": sha256(image_path),
        "width": IMAGE_SIZE[0],
        "height": IMAGE_SIZE[1],
        "input_kind": "crop",
        "split": split,
        "source_kind": "synthetic",
        "usage_rights": "project-generated",
        "source_envelope_id": f"{DATASET_VERSION}:{split}:source:{index:06d}",
        "writer_id": f"{DATASET_VERSION}:{split}:writer-{index % 12:02d}",
        "layout_family": f"{DATASET_VERSION}:{split}:crop-layout-{index % 4:02d}",
        "annotation_version": ANNOTATION_VERSION,
        "annotation_status": "verified",
        "label_status": label_status,
        "postal_code": code,
        "postal_bbox": bbox,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère des zones postales synthétiques sans données personnelles.")
    parser.add_argument("--output-root", type=Path, default=Path("data/postal"))
    parser.add_argument("--train-count", type=int, default=240)
    parser.add_argument("--validation-count", type=int, default=60)
    parser.add_argument("--test-count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    counts = {"train": args.train_count, "validation": args.validation_count, "test": args.test_count}
    if any(count < 1 for count in counts.values()):
        raise ValueError("Chaque split doit contenir au moins une image")
    images_directory = args.output_root / "images" / DATASET_VERSION
    manifest_path = args.output_root / "manifests" / f"{DATASET_VERSION}.jsonl"
    if (images_directory.exists() or manifest_path.exists()) and not args.force:
        raise FileExistsError(f"{DATASET_VERSION} existe déjà sous {args.output_root}; utilisez --force pour le régénérer")
    if args.force:
        shutil.rmtree(images_directory, ignore_errors=True)
        manifest_path.unlink(missing_ok=True)
    rng = random.Random(args.seed)
    records: list[dict] = []
    index = 0
    for split, count in counts.items():
        for _ in range(count):
            image_path = images_directory / split / f"{index:06d}.png"
            records.append(render_record(index, split, rng, image_path))
            index += 1
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n", encoding="utf-8")
    print(f"Corpus synthétique créé : {len(records)} images")
    print(f"Manifeste : {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
