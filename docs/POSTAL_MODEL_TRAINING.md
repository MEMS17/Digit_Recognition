# Adaptation du modèle aux chiffres postaux synthétiques

Le CNN MNIST gelé a été fine-tuné sur les chiffres extraits des zones annotées de
`postal-synthetic-v1`. Les rectangles de référence du corpus servent uniquement à
extraire les chiffres pour cet entraînement ; la chaîne d'inférence conserve ses
propres rectangles issus de la segmentation.

## Protocole

- Train : 192 zones positives, soit **960 chiffres**.
- Validation : 49 zones positives, soit **245 chiffres**.
- Test : **non chargé**.
- Point de départ : `mnist_tuning_v1/cnn_tuned.keras`, empreinte
  `21f8caaedcfcc9787c314f5a516cb33317d2b821f7b6dde421f51aff860e68ec`.
- Adaptation : Adam `1e-4`, batch 64, maximum 30 époques, arrêt anticipé après
  cinq époques sans amélioration de l'accuracy validation, rotations et translations
  aléatoires de 6 % pendant l'entraînement.

## Résultats validation

| Candidat | Accuracy | F1 macro |
|---|---:|---:|
| CNN MNIST gelé | 80,00 % | 74,80 % |
| CNN adapté | **100,00 %** | **100,00 %** |

Le CNN adapté est le candidat retenu sur validation. Son artefact et l'historique
sont conservés localement dans `ia/models/postal_digit_synthetic_v1/`, hors Git.

Cette perfection sur validation ne prouve pas une généralisation réelle : train et
validation proviennent du même générateur, avec une police et des variations limitées.
Le candidat n'est donc pas encore intégré au service de lecture ni autorisé à
accepter automatiquement un code. L'étape suivante est son évaluation unique sur le
split test synthétique, suivie d'une comparaison honnête avec le CNN MNIST.
