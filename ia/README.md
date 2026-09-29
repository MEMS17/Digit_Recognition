# IA — reconnaissance des codes postaux

Responsable : toi (avec l'agent IA). Ce dossier est indépendant du front et du back.

Cette initialisation fournit uniquement un environnement Python 3.12 et les dossiers
de travail. Aucun jeu de données, entraînement, poids de modèle ou prédiction simulée
n'est fourni. Les fonctionnalités seront réalisées après validation de l'initialisation.

## Structure

- `src/postal_ocr/` : futurs modules d'import, prétraitement, entraînement et évaluation.
- `notebooks/` : exploration et comparaison documentée des expériences.
- `data/` : fichiers de travail locaux, jamais la source directe d'entraînement.
- `models/` : artefacts entraînés et métadonnées de version, absents à ce stade.
- `requirements.txt` : dépendances directes figées ; un verrouillage transitif pourra
  être ajouté une fois l'environnement Docker validé.

## Utilisation Docker

Depuis la racine du projet, démarrer le service IA prévu dans Compose :

```sh
docker compose up -d --build ia
docker compose exec ia python -c "import postal_ocr; print('Environnement IA disponible')"
```

Le conteneur reste en attente, sans lancer d'entraînement ni télécharger de données.
Son répertoire de travail est `/app` et `PYTHONPATH=/app/src` rend le package importable.
Compose peut monter `./ia:/app` pour travailler sur les sources sans reconstruire
l'image. Une modification des dépendances nécessite une reconstruction.

JupyterLab est installé pour les futures explorations. Son démarrage et son exposition
réseau doivent être explicites ; aucun serveur Jupyter ne démarre automatiquement.

## Importer MNIST dans MongoDB

Le script importe les CSV MNIST au format `label,pixel_1,...,pixel_784` dans les
collections `mnist_train` et `mnist_test`. Les sources sont téléchargées dans
`ia/data/raw/`, dossier ignoré par Git. Il utilise un miroir GitHub des CSV
compressés : l'hôte d'origine cité par le sujet renvoie actuellement une erreur 403
aux téléchargements automatisés depuis Docker.

```sh
docker compose exec ia python -m postal_ocr.mnist_import --download
```

Il valide chaque ligne, les 60 000 / 10 000 effectifs attendus, les labels et les
dimensions 28 × 28. Les identifiants sont déterministes et les documents existants
identiques sont ignorés : relancer la commande ne crée pas de doublon. Un document
différent sous le même identifiant provoque un arrêt explicite sans écrasement.

La commande n'entraîne aucun modèle. Elle doit être suivie de l'exploration dans le
notebook et de la création du manifeste entraînement/validation.

## Exploration et séparation entraînement/validation

Le notebook `notebooks/01_exploration_mnist.ipynb` lit uniquement MongoDB et produit
les visualisations demandées : un chiffre, les chiffres 0 à 9, les neuf premiers 7 et
le représentant moyen de chaque chiffre. Pour le réexécuter dans Docker :

```sh
docker compose exec ia jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=180 notebooks/01_exploration_mnist.ipynb
```

La séparation est créée par une commande indépendante : 50 000 images train et
10 000 validation, stratifiées par label, avec la graine 42. Le manifeste et ses
empreintes sont conservés dans la collection MongoDB `dataset_manifests` et ne sont
jamais réécrits si leur contenu diffère.

```sh
docker compose exec ia python -m postal_ocr.mnist_split
```

## Comparer les trois modèles

Le script ci-dessous charge les 50 000/10 000 exemples définis par le manifeste depuis
MongoDB, entraîne un SVM RBF, une Random Forest et un CNN CPU, puis mesure accuracy,
F1 macro, matrice de confusion, durée d'entraînement et latence unitaire sur la
validation. Il ne consulte jamais `mnist_test`.

```sh
docker compose up --build -d ia
docker compose exec ia python -m postal_ocr.train_mnist_models
```

Les artefacts et résultats JSON sont écrits dans `ia/models/mnist_baseline_v1/`,
ignoré par Git. Le test final, l'optimisation des hyperparamètres et la sélection du
modèle restent des étapes distinctes. Les résultats de baseline validés sont résumés
dans `../docs/MODEL_RESULTS.md`.

## Optimiser les candidats

La commande suivante utilise `GridSearchCV` à trois folds sur un sous-échantillon
stratifié de 10 000 images du train pour choisir les paramètres SVM. Le meilleur SVM
est ensuite réentraîné sur les 50 000 images du train et mesuré sur la validation
externe. Trois configurations CNN sont comparées sur la même validation. Le jeu test
reste entièrement hors de cette étape.

```sh
docker compose exec ia python -m postal_ocr.tune_mnist_models
```

Les résultats et les artefacts sont conservés localement dans
`ia/models/mnist_tuning_v1/`. Ils ne remplacent pas les baselines.

## Évaluer le modèle gelé sur le test final

Après le gel du candidat CNN, cette commande charge uniquement
`mnist_test` et l'artefact retenu. Elle produit accuracy, F1 macro, métriques par
classe, matrice de confusion, latence CPU et vingt-cinq premières erreurs. Le
résultat est refusé si un résultat final local existe déjà, afin d'éviter de
réutiliser le test sans décision explicite.

```sh
docker compose exec ia python -m postal_ocr.evaluate_mnist_final
```

Le détail reste dans `ia/models/mnist_final_evaluation_v1/results.json`, ignoré par
Git. Le résumé validé est reporté dans `../docs/MODEL_RESULTS.md`.

## Préparer le corpus de codes postaux

Le contrat de collecte et d'annotation est décrit dans
[`../docs/POSTAL_DATASET.md`](../docs/POSTAL_DATASET.md). Les courriers et leurs
manifestes ne sont pas versionnés. Avant toute utilisation, valider le manifeste :

```sh
docker compose exec ia python -m postal_ocr.validate_postal_manifest \
  --manifest data/postal/manifests/postal-v1.jsonl \
  --images-root data/postal/images \
  --check-images
```

Le contrôle vérifie notamment les codes à cinq chiffres, les images, les rectangles
et l'absence de fuite entre les splits train, validation et test.

Un corpus local, fictif et reproductible de zones postales peut être généré pour le
développement de la segmentation :

```sh
docker compose exec ia python -m postal_ocr.generate_synthetic_postal_dataset
```

Ses images et son manifeste restent dans `data/postal/`, hors Git. Il ne remplace
pas le corpus de courriers autorisés nécessaire à l'évaluation du projet.

## Segmenter les cinq chiffres d'une zone recadrée

La première segmentation détecte les composantes sombres et retourne cinq rectangles
ordonnés de gauche à droite, ou un motif stable de révision (`no_digit_detected` ou
`invalid_digit_count`). Elle ne reconnaît pas encore les chiffres.

```sh
docker compose exec ia python -m postal_ocr.segment_postal_code \
  data/postal/images/postal-synthetic-v1/test/000300.png

docker compose exec ia python -m postal_ocr.evaluate_postal_segmentation \
  --manifest data/postal/manifests/postal-synthetic-v1.jsonl \
  --images-root data/postal/images
```

L'évaluation utilise uniquement le split test synthétique et mesure la détection de
cinq chiffres, l'IoU des rectangles et les fausses segmentations des cas négatifs.

## Contrat avec les autres dossiers

Le back recevra les images et orchestrera les requêtes. L'IA produira ultérieurement
un artefact versionné et un contrat d'inférence documenté. Aucun import direct du
code Django ou React ne doit être ajouté ici. Le choix du chargement de l'artefact
ou d'un service d'inférence séparé sera documenté avant l'intégration.

La connexion MongoDB utilisera la variable `MONGODB_URI` fournie par l'environnement,
sans identifiants enregistrés dans le dépôt. La base utilisera `MONGODB_DATABASE`.

## Étapes futures

1. Importer MNIST dans MongoDB avec des collections distinctes d'entraînement et de
   test. Charger ensuite les données d'entraînement **depuis MongoDB**.
2. Réserver une validation dans l'entraînement, conserver le test hors des réglages,
   puis comparer au moins trois modèles et leurs hyperparamètres.
3. Versionner les paramètres de prétraitement avec le modèle ; appliquer exactement
   la même transformation aux images reçues par l'application.
4. Évaluer les dessins réels et les erreurs, en séparant les prédictions enregistrées
   des étiquettes humaines vérifiées.
5. Constituer un jeu annoté de codes postaux complets ; développer la segmentation
   d'une zone contenant cinq chiffres et mesurer la justesse du code entier.
6. Ajouter la localisation de la zone postale sur des photos d'enveloppes fictives,
   puis évaluer toute la chaîne sur des images jamais utilisées pour les réglages.
7. Définir des critères de lecture incertaine et une correction humaine ; un code
   présent dans un référentiel ne prouve pas à lui seul que la lecture est correcte.

MNIST ne constitue pas un jeu d'évaluation de localisation sur enveloppes. La lecture
complète nécessitera des annotations et un protocole d'évaluation supplémentaires.
Les images de courrier et les artefacts volumineux restent hors Git.
