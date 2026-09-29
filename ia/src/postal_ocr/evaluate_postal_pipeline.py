"""Evaluate the frozen crop segmentation and recognition pipeline on one held-out split."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from postal_ocr.postal_code_inference import file_sha256, load_model, predict_postal_code

ADAPTED_MODEL_PATH = Path("models/postal_digit_synthetic_v1/postal_digit_cnn.keras")
OUTPUT_PATH = Path("models/postal_pipeline_synthetic_adapted_v1/results.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Évalue la chaîne postale complète sur un split de manifeste.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--model-path", type=Path, default=ADAPTED_MODEL_PATH)
    parser.add_argument("--model-version", default="postal-digit-synthetic-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if OUTPUT_PATH.exists() and not args.force:
        raise FileExistsError(f"{OUTPUT_PATH} existe déjà ; ne réévaluez pas sans décision explicite")
    records = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines()]
    selected = [record for record in records if record["split"] == args.split and record["annotation_status"] == "verified"]
    positives = [record for record in selected if record["label_status"] == "labeled"]
    negatives = [record for record in selected if record["label_status"] != "labeled"]
    if not positives:
        raise RuntimeError("Le split évalué ne contient aucun code postal annoté")
    model = load_model(args.model_path)
    positive_results = []
    for record in positives:
        prediction = predict_postal_code(args.images_root / record["image_path"], model, args.model_version)
        predicted_digits = prediction["value"] if prediction["value"] is not None else ""
        positive_results.append({
            "id": record["id"],
            "expected": record["postal_code"],
            "predicted": prediction["value"],
            "status": prediction["status"],
            "correct_digits": sum(expected == actual for expected, actual in zip(record["postal_code"], predicted_digits)),
        })
    negative_results = [predict_postal_code(args.images_root / record["image_path"], model, args.model_version) for record in negatives]
    result = {
        "experiment_id": "postal_pipeline_synthetic_adapted_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "split": args.split,
        "model": {"artifact": str(args.model_path), "sha256": file_sha256(args.model_path)},
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "metrics": {
            "digit_accuracy": sum(item["correct_digits"] for item in positive_results) / (5 * len(positives)),
            "exact_postal_code_accuracy": sum(item["expected"] == item["predicted"] for item in positive_results) / len(positives),
            "unreadable_positive_rate": sum(item["status"] == "unreadable" for item in positive_results) / len(positives),
            "negative_proposed_value_rate": sum(item["value"] is not None for item in negative_results) / len(negatives) if negatives else None,
            "automatic_acceptance_rate": 0.0,
        },
        "positive_errors": [item for item in positive_results if item["expected"] != item["predicted"]],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
