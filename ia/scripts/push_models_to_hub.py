"""Upload the two serving artefacts to a Hugging Face model repository.

The script is intentionally separate from training and only runs when invoked.
Authenticate beforehand with ``hf auth login`` or provide ``HF_TOKEN``.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTEFACTS = (
    (ROOT / "models/mnist_tuning_v1/cnn_tuned.keras", "mnist/cnn_tuned.keras"),
    (ROOT / "models/postal_digit_synthetic_v1/postal_digit_cnn.keras", "postal/postal_digit_cnn.keras"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publie les modèles de service sur Hugging Face Hub.")
    parser.add_argument("--repo", required=True, help="Dépôt modèle, par exemple utilisateur/digit-recognition-models")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise SystemExit("Installez huggingface_hub avant la publication : python -m pip install huggingface_hub") from exc

    missing = [str(path) for path, _ in ARTEFACTS if not path.is_file()]
    if missing:
        raise SystemExit("Artefact(s) introuvable(s) : " + ", ".join(missing))

    api = HfApi()
    api.create_repo(repo_id=args.repo, repo_type="model", exist_ok=True)
    for path, destination in ARTEFACTS:
        api.upload_file(path_or_fileobj=str(path), path_in_repo=destination, repo_id=args.repo, repo_type="model")
        print(f"Publié : {path} -> {destination}")


if __name__ == "__main__":
    main()
