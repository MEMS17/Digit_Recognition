"""Command-line entry point for crop-based postal-code inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from postal_ocr.postal_code_inference import load_model, predict_postal_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Lit cinq chiffres segmentés dans une zone postale recadrée.")
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    if not args.image.is_file():
        raise FileNotFoundError(f"Image introuvable : {args.image}")
    print(json.dumps(predict_postal_code(args.image, load_model()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
