# Jeu de données postal — contrat de collecte et d'annotation

Ce document définit le corpus utilisé à partir du jalon `crop`. Il complète le
périmètre fonctionnel décrit dans [POSTAL_SCOPE.md](POSTAL_SCOPE.md). Les images et
manifestes réels restent hors Git dans `ia/data/postal/`.

## Arborescence locale

```text
ia/data/postal/
├── images/                 # JPEG ou PNG autorisés, jamais versionnés
└── manifests/
    └── postal-v1.jsonl     # une ligne JSON par image, jamais versionnée
```

Chaque `image_path` est relatif à `ia/data/postal/images/`. Un fichier ne peut pas
sortir de ce dossier par `..` ou par un chemin absolu. Les fichiers doivent être
des PNG ou JPEG décodables. Les droits d'utilisation et la provenance sont des
métadonnées obligatoires : aucun courrier réel ou adresse personnelle ne doit être
ajouté sans autorisation documentée.

## Ligne de manifeste

Une ligne JSON décrit une image complète. Les coordonnées sont des pixels entiers,
dans l'image après application de l'orientation EXIF, origine en haut à gauche.

```json
{
  "id": "postal-v1:000001",
  "image_path": "crop/000001.png",
  "image_sha256": "64-caracteres-hexadecimaux-minuscules",
  "width": 640,
  "height": 180,
  "input_kind": "crop",
  "split": "train",
  "source_kind": "synthetic",
  "usage_rights": "project-authorized",
  "source_envelope_id": "envelope-group-001",
  "writer_id": "writer-014",
  "layout_family": "printed-address-block-a",
  "annotation_version": "postal-annotation-v1",
  "annotation_status": "verified",
  "label_status": "labeled",
  "postal_code": "01234",
  "postal_bbox": {"x": 42, "y": 64, "width": 250, "height": 56}
}
```

Champs obligatoires : `id`, `image_path`, `image_sha256`, `width`, `height`,
`input_kind`, `split`, `source_kind`, `usage_rights`, `source_envelope_id`,
`writer_id`, `layout_family`, `annotation_version`, `annotation_status`,
`label_status`, `postal_code`, `postal_bbox`.

Valeurs admises :

- `input_kind` : `crop` ou `envelope` ;
- `split` : `train`, `validation` ou `test` ;
- `source_kind` : `synthetic` ou `authorized` ;
- `annotation_status` : `verified` ou `pending_review` ;
- `label_status` : `labeled`, `absent`, `illegible` ou `ambiguous`.

Un statut `labeled` exige un `postal_code` correspondant exactement à
`^[0-9]{5}$` et un rectangle. Les zéros initiaux sont conservés. Les trois autres
statuts exigent `postal_code: null` et `postal_bbox: null`. `verified` désigne une
annotation contrôlée par une seconde personne ou une procédure documentée ; seules
ces lignes peuvent servir à l'entraînement ou à l'évaluation officielle.

## Règles de séparation

Les splits sont attribués avant toute augmentation. Toutes les lignes portant le
même `source_envelope_id`, `writer_id` ou `layout_family` doivent appartenir au
même split. Cette contrainte évite que des recadrages, une même écriture ou une
même mise en page apparaissent simultanément en entraînement et en test. Les
augmentations conservent la même valeur `source_envelope_id` que l'original.

Le test est réservé avant les choix de prétraitement, de modèle, de seuil et de
segmentation. Les cas `absent`, `illegible` et `ambiguous` sont conservés dans le
test afin de mesurer les faux résultats automatiques et le besoin de révision.

## Contrôle avant utilisation

Exécuter cette commande avant de créer un split, un entraînement ou une évaluation :

```sh
docker compose exec ia python -m postal_ocr.validate_postal_manifest \
  --manifest data/postal/manifests/postal-v1.jsonl \
  --images-root data/postal/images \
  --check-images
```

Sans `--check-images`, le validateur contrôle uniquement la structure JSONL et les
règles de regroupement. Avec l'option, il vérifie aussi l'empreinte SHA-256, les
dimensions après orientation EXIF et les bornes des rectangles. Une erreur bloque
la commande avec le numéro de ligne concerné.

Avant le premier entraînement, publier dans le rapport du projet le nombre de lignes
par split, par statut d'étiquette, par provenance et par famille de mise en page.
Ce comptage décrit la couverture réelle du corpus ; il ne remplace pas une mesure
sur le test tenu à l'écart.

## Corpus synthétique initial

Le script `postal_ocr.generate_synthetic_postal_dataset` fournit un corpus local de
zones `crop` entièrement fictives. Il génère des codes à cinq chiffres, des variations
de fond, de taille, de flou et des cas `absent`, `illegible` et `ambiguous`. Il ne
contient ni adresse, ni nom, ni courrier réel et ses annotations sont déterministes.

```sh
docker compose exec ia python -m postal_ocr.generate_synthetic_postal_dataset
docker compose exec ia python -m postal_ocr.validate_postal_manifest \
  --manifest data/postal/manifests/postal-synthetic-v1.jsonl \
  --images-root data/postal/images \
  --check-images
```

La génération par défaut produit 240 images train, 60 validation et 60 test. Le
corpus est un support de développement pour la segmentation, pas une mesure de
performance sur des courriers. Une évaluation représentative exigera le corpus
fictif ou autorisé décrit plus haut, avec davantage de scripteurs et de dispositions.

La première génération locale validée le 29 septembre 2026 contient :

| Split | Codes annotés | Absents | Illisibles | Ambigus | Total |
|---|---:|---:|---:|---:|---:|
| Train | 205 | 11 | 12 | 12 | 240 |
| Validation | 50 | 2 | 3 | 5 | 60 |
| Test | 45 | 6 | 4 | 5 | 60 |
| Total | 300 | 19 | 19 | 22 | 360 |

Ces effectifs sont produits avec la graine `42`. Ils attestent uniquement de la
validité du flux de données synthétique ; aucune métrique de reconnaissance postale
ne doit être déduite de ce corpus avant l'entraînement et l'évaluation dédiés.
