"""Segment five digit candidates from a postal-code crop with connected components."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage


def segment_image(path: Path) -> dict:
    """Return sorted digit rectangles or a stable failure reason for one image."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("L")
    grayscale = np.asarray(image)
    background = float(np.percentile(grayscale, 90))
    threshold = int(min(160, max(80, background - 55)))
    mask = grayscale < threshold
    labels, component_count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    boxes: list[dict[str, int]] = []
    for label_index, slices in enumerate(ndimage.find_objects(labels), start=1):
        if slices is None:
            continue
        y_slice, x_slice = slices
        x, y = x_slice.start, y_slice.start
        width, height = x_slice.stop - x, y_slice.stop - y
        area = int(np.count_nonzero(labels[slices] == label_index))
        if width >= 5 and height >= 15 and area >= 50:
            boxes.append({"x": int(x), "y": int(y), "width": int(width), "height": int(height), "area": area})
    boxes.sort(key=lambda box: box["x"])
    result = {
        "image": {"width": image.width, "height": image.height},
        "threshold": threshold,
        "raw_component_count": int(component_count),
        "boxes": boxes,
    }
    if len(boxes) == 5:
        result["status"] = "segmented"
        result["reason"] = None
    elif not boxes:
        result["status"] = "needs_review"
        result["reason"] = "no_digit_detected"
    else:
        result["status"] = "needs_review"
        result["reason"] = "invalid_digit_count"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Segmente les chiffres d'une zone postale PNG ou JPEG.")
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    if not args.image.is_file():
        raise FileNotFoundError(f"Image introuvable : {args.image}")
    print(json.dumps(segment_image(args.image), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
