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
