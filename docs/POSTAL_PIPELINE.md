# Lecture complète d'une zone postale recadrée

La chaîne `postal-crop-component-v1` applique la segmentation de cinq composantes,
normalise chaque composante en 28 × 28 (chiffre clair sur fond sombre), puis appelle
le CNN MNIST gelé. Les cinq labels sont assemblés de gauche à droite et le score du
code est le minimum des cinq scores individuels.

Une valeur complète est toujours retournée avec l'état `needs_review` et la raison
`acceptance_policy_unvalidated`. Les scores softmax du CNN ne sont pas calibrés sur
les courriers et aucun seuil d'acceptation n'a été validé. Une segmentation échouée
retourne `unreadable` sans valeur.

## Évaluation synthétique v1

Le 29 septembre 2026, le pipeline a été évalué une fois sur les 60 images du split
`test` de `postal-synthetic-v1`, sans utiliser ce split pour son développement. Le
modèle évalué est `mnist-cnn-a-v1`, empreinte SHA-256
`21f8caaedcfcc9787c314f5a516cb33317d2b821f7b6dde421f51aff860e68ec`.

| Mesure | Résultat |
|---|---:|
| Codes annotés | 49 |
| Cas négatifs | 11 |
| Précision par chiffre | 79,18 % |
| Codes postaux entièrement exacts | 34,69 % (17 / 49) |
| Codes positifs illisibles | 0 % |
| Valeur proposée sur cas négatif | 18,18 % (2 / 11) |
| Acceptation automatique | 0 % |

Le résultat confirme que le CNN MNIST est une bonne preuve de fonctionnement pour
des chiffres isolés, mais qu'il n'est pas suffisamment adapté aux zones postales,
même synthétiques. Le produit ne doit donc pas présenter une lecture comme fiable
ni activer l'acceptation automatique. Le détail des 32 erreurs de codes est conservé
localement dans `ia/models/postal_pipeline_synthetic_v1/results.json`, hors Git.

## Suite nécessaire

La prochaine itération doit entraîner ou adapter un reconnaisseur sur les chiffres
extraits du split train postal, choisir ses transformations et son seuil uniquement
sur validation, puis réserver le test pour une nouvelle évaluation de modèle. Le
corpus de courriers fictifs ou autorisés reste nécessaire avant toute conclusion sur
le périmètre réel.
