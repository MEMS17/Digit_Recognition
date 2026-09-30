# Service IA et entraînement

Les commandes suivantes se lancent depuis la racine, après démarrage de Docker Compose.
La préparation MNIST est décrite dans le README principal.

## Corpus postal et adaptation

```sh
docker compose exec ia python -m postal_ocr.generate_synthetic_postal_dataset
docker compose exec ia python -m postal_ocr.validate_postal_manifest --manifest data/postal/manifests/postal-synthetic-v1.jsonl --images-root data/postal/images --check-images
docker compose exec ia python -m postal_ocr.evaluate_postal_segmentation --manifest data/postal/manifests/postal-synthetic-v1.jsonl --images-root data/postal/images
docker compose exec ia python -m postal_ocr.train_postal_digit_model --manifest data/postal/manifests/postal-synthetic-v1.jsonl --images-root data/postal/images
docker compose exec ia python -m postal_ocr.evaluate_postal_pipeline --manifest data/postal/manifests/postal-synthetic-v1.jsonl --images-root data/postal/images
```

L'adaptation exige le CNN MNIST sélectionné sous `ia/models/mnist_tuning_v1/cnn_tuned.keras`.
Le modèle adapté est écrit sous `ia/models/postal_digit_synthetic_v1/postal_digit_cnn.keras`.
Les commandes d'évaluation finale protègent les résultats existants contre un remplacement involontaire.

## Exploration et artefacts

Le notebook `notebooks/01_exploration_mnist.ipynb` explore les images lues depuis MongoDB.
Les images et manifestes locaux sont sous `data/`, les modèles et rapports sous `models/`.
Ces données restent hors Git.

`requirements.txt` contient l'environnement d'exploration et d'entraînement.
`requirements.production.txt` contient les dépendances du service d'inférence.

FastAPI charge les modèles à la première requête ; il ne lance pas d'entraînement.
Les résultats et leurs limites sont regroupés dans [Résultats IA](../docs/MODEL_RESULTS.md).
