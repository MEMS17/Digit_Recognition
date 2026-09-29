"""Evaluate the component-based postal segmentation on a held-out manifest split."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from postal_ocr.segment_postal_code import segment_image

OUTPUT_PATH = Path("models/postal_segmentation_synthetic_v1/results.json")


def intersection_over_union(first: dict, second: dict) -> float:
    left = max(first["x"], second["x"])
    top = max(first["y"], second["y"])
    right = min(first["x"] + first["width"], second["x"] + second["width"])
    bottom = min(first["y"] + first["height"], second["y"] + second["height"])
    intersection = max(0, right - left) * max(0, bottom - top)
    if not intersection:
        return 0.0
    first_area = first["width"] * first["height"]
    second_area = second["width"] * second["height"]
    return intersection / (first_area + second_area - intersection)


def main() -> int:
    parser = argparse.ArgumentParser(description="Évalue la segmentation sur un split d'un manifeste postal.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if OUTPUT_PATH.exists() and not args.force:
        raise FileExistsError(f"{OUTPUT_PATH} existe déjà ; utilisez --force pour une nouvelle évaluation")
    records = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines()]
    selected = [record for record in records if record["split"] == args.split and record["annotation_status"] == "verified"]
    positives = [record for record in selected if record["label_status"] == "labeled"]
    negatives = [record for record in selected if record["label_status"] != "labeled"]
    if not positives or any("digit_bboxes" not in record for record in positives):
        raise RuntimeError("Le split évalué doit contenir des lignes labeled avec digit_bboxes")
    positive_results = []
    for record in positives:
        result = segment_image(args.images_root / record["image_path"])
        predicted = result["boxes"]
        ious = [intersection_over_union(expected, actual) for expected, actual in zip(record["digit_bboxes"], predicted)] if len(predicted) == 5 else []
        positive_results.append({"id": record["id"], "status": result["status"], "ious": ious})
    negative_results = [segment_image(args.images_root / record["image_path"]) for record in negatives]
    complete = [item for item in positive_results if item["status"] == "segmented"]
    all_ious = [iou for item in complete for iou in item["ious"]]
    result = {
        "experiment_id": "postal_segmentation_synthetic_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "split": args.split,
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "metrics": {
            "five_digit_detection_rate": len(complete) / len(positives),
            "mean_digit_iou_when_five_detected": float(np.mean(all_ious)) if all_ious else None,
            "all_digits_iou_at_least_0_5_rate": sum(all(iou >= 0.5 for iou in item["ious"]) for item in complete) / len(positives),
            "negative_false_segmentation_rate": sum(item["status"] == "segmented" for item in negative_results) / len(negatives) if negatives else None,
        },
        "positive_failures": [item for item in positive_results if item["status"] != "segmented"],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
