# Segmentation d'une zone postale recadrée

La première implémentation segmente une zone `crop` en composantes sombres. Elle
applique l'orientation EXIF, convertit l'image en niveaux de gris, estime le fond,
isole les pixels sombres puis conserve les composantes dont la taille correspond à
un chiffre. Les rectangles sont triés de gauche à droite.

La sortie est `segmented` uniquement si cinq rectangles sont trouvés. Sinon le
pipeline devra demander une révision avec `no_digit_detected` ou
`invalid_digit_count`. Cette étape ne reconnaît pas encore les chiffres ; elle ne
produit donc aucun code postal seule.

## Évaluation synthétique v1

Le 29 septembre 2026, la segmentation a été évaluée sur le split `test` du corpus
`postal-synthetic-v1`, sans modifier son algorithme pendant cette exécution. Les
images train et validation n'ont pas participé à ce calcul.

| Mesure | Résultat | Interprétation |
|---|---:|---|
| Codes annotés | 49 | Images avec cinq rectangles de référence |
| Cas négatifs | 11 | Absents, illisibles ou ambigus |
| Détection de cinq chiffres | 100 % | 49 / 49 images positives produisent cinq rectangles |
| IoU moyen par chiffre | 0,812 | Recouvrement moyen avec les rectangles synthétiques de référence |
| Cinq IoU ≥ 0,5 | 100 % | 49 / 49 images positives |
| Fausse segmentation négative | 18,2 % | 2 / 11 cas négatifs retournent néanmoins cinq rectangles |

Les métriques détaillées sont enregistrées localement dans
`ia/models/postal_segmentation_synthetic_v1/results.json`, hors Git. Elles valident
le flux technique sur des images générées, pas une capacité de lecture de courriers
réels. La police, les fonds, la netteté et les dispositions restent beaucoup moins
variés qu'en conditions réelles.

## Étape suivante

Chaque rectangle segmenté doit être normalisé en une image 28 × 28 compatible avec
le CNN MNIST, puis classé. Le résultat à cinq chiffres devra conserver les échecs de
segmentation, les scores individuels et les cas de révision. Avant une promesse sur
les courriers, cette chaîne doit être évaluée sur le corpus fictif ou autorisé prévu
dans [POSTAL_DATASET.md](POSTAL_DATASET.md).
