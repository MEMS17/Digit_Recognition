# Résultats IA

Résultats reproduits le **30 septembre 2026**.
Les mesures MNIST et postales portent sur des jeux distincts et ne sont pas interchangeables.

## Dataset MNIST

MNIST contient des images de chiffres manuscrits 28 × 28 :
60 000 images train et 10 000 images test.

| Partition | Effectif | Utilisation |
|---|---:|---|
| Entraînement | 50 000 | Apprentissage |
| Validation | 10 000 | Comparaison et sélection |
| Test final | 10 000 | Évaluation après sélection |

Le split train/validation est stratifié, avec graine 42.
Les pixels sont lus depuis MongoDB et normalisés par division par 255.
Le test n'a été utilisé qu'après sélection du modèle.

## Baselines sur validation

| Modèle | Accuracy |
|---|---:|
| SVM RBF | 98,26 % |
| Random Forest | 96,80 % |
| CNN baseline | 98,91 % |

Le CNN est retenu pour la suite : il obtient le meilleur résultat parmi ces baselines.

## Optimisation du CNN

| Paramètre | Valeur retenue |
|---|---|
| learning_rate | 0.001 |
| dropout | 0.25 |
| batch_size | 128 |
| epochs maximum | 10 |
| early stopping patience | 2 |

Accuracy de validation du CNN optimisé : **98,99 %**.

## Test final MNIST

| Mesure | Résultat |
|---|---:|
| Accuracy | **99,18 %** |
| F1 macro | **99,17 %** |

Ces scores mesurent la reconnaissance de chiffres MNIST,
pas la lecture de photographies d'enveloppes.

## Adaptation postale

Le dataset `postal-synthetic-v1` contient **360 images** :
240 train, 60 validation et 60 test.
Il combine des codes de cinq chiffres, des variations de fond, taille et flou,
ainsi que des exemples négatifs.
Le test comporte 49 zones positives et 11 cas négatifs.

La segmentation isole les composantes sombres et les trie de gauche à droite.
Les chiffres sont centrés et normalisés en 28 × 28 avant classification.
Les annotations de référence servent à l'entraînement et à l'évaluation ;
la lecture utilise les rectangles calculés par la segmentation.

### Segmentation sur le test synthétique

| Mesure | Résultat |
|---|---:|
| five_digit_detection_rate | 100 % |
| mean_digit_iou | 0,8119 |
| all_digits_iou ≥ 0.5 | 100 % |
| negative_false_segmentation_rate | 18,18 % (2 / 11) |

L'IoU mesure le recouvrement entre rectangle prédit et rectangle de référence.

### Reconnaissance avant et après adaptation

| Modèle sur validation postale synthétique | Accuracy | F1 macro |
|---|---:|---:|
| CNN MNIST avant adaptation | 81,22 % | 73,48 % |
| CNN après adaptation postale | 100 % | 100 % |

Le CNN postal est adapté à partir du CNN MNIST, avec entraînement et sélection
sur les partitions train et validation postales.
Le test postal n'intervient pas dans le réglage.

### Pipeline adapté sur le test synthétique

| Mesure | Résultat |
|---|---:|
| digit_accuracy | 100 % |
| exact_postal_code_accuracy | 100 % (49 / 49) |
| unreadable_positive_rate | 0 % |
| negative_proposed_value_rate | 18,18 % (2 / 11) |
| automatic_acceptance_rate | 0 % |

Le code est exact seulement si les cinq chiffres sont corrects.
Une proposition complète conserve l'état `needs_review`.
Le score du code est le minimum des scores de ses chiffres.

## Limites

Les performances postales sont mesurées sur des données synthétiques issues du même générateur.
Elles ne prouvent pas 100 % de performance sur du courrier réel.
La diversité des écritures, fonds et conditions photographiques reste limitée.

Deux cas négatifs sur onze produisent encore une proposition.
L'adaptation améliore la classification mais ne supprime pas ces erreurs de segmentation.
La vérification humaine reste nécessaire ; les scores ne sont pas calibrés.

Les modèles et rapports détaillés restent hors Git sous `ia/models/` :
`mnist_baseline_v1`, `mnist_tuning_v1`, `mnist_final_evaluation_v1`,
`postal_segmentation_synthetic_v1`, `postal_digit_synthetic_v1`
et `postal_pipeline_synthetic_adapted_v1`.
