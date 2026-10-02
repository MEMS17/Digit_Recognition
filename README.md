# Digit Recognition — Lecture de codes postaux

## Présentation

Projet annuel IA / Big Data consacré à la reconnaissance de chiffres manuscrits et à la lecture de codes postaux de cinq chiffres.
L'application web fonctionne sans authentification et permet de vérifier ou corriger les prédictions.

Le MVP traite une **zone de code postal déjà recadrée**.
La localisation automatique du code postal dans une enveloppe complète n'est pas encore implémentée.

## Démo

- Frontend : https://digit-recognition-zeta-six.vercel.app
- API : https://api-digit.etsgsm.org
- Health : https://api-digit.etsgsm.org/api/health/

## Fonctionnalités

- Dessin et reconnaissance d'un chiffre manuscrit.
- Upload PNG/JPEG d'une zone postale recadrée.
- Segmentation des cinq chiffres et lecture du code postal.
- Affichage du score de confiance et des états de lecture.
- Vérification et correction humaines.
- Persistance des prédictions et corrections dans MongoDB.

## Technologies

| Composant | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Vercel |
| Backend | Django, Gunicorn, PyMongo, MongoDB Atlas |
| IA | Python, TensorFlow/Keras, scikit-learn, MNIST, FastAPI |
| Infrastructure | Docker, Docker Compose, Plesk/Nginx |

## Architecture

```text
Vercel
  ↓ HTTPS
Django / VPS Plesk
  ├── MongoDB Atlas
  ↓ réseau Docker
FastAPI IA
  ↓
Modèles Keras locaux
```

Django expose l'API publique ; FastAPI reste accessible uniquement au backend.

## Résultats principaux

Résultats reproduits le **30 septembre 2026**.

| Modèle MNIST | Accuracy |
|---|---:|
| SVM RBF — validation | 98,26 % |
| Random Forest — validation | 96,80 % |
| CNN baseline — validation | 98,91 % |
| CNN optimisé — validation | 98,99 % |
| CNN optimisé — test final | 99,18 % |

Le F1 macro du CNN sur le test final MNIST est de **99,17 %**.

Sur le dataset postal synthétique :

- Détection des cinq chiffres : **100 %** ; IoU moyen : **0,812**.
- Accuracy chiffre et code postal exact après adaptation : **100 %**.
- Propositions erronées sur les exemples négatifs : **18,18 %**.
- Acceptation automatique : **0 %** ; la lecture postale exige une vérification humaine.

**Les résultats postaux à 100 % concernent uniquement le dataset synthétique et ne garantissent pas ces performances sur des courriers réels.**
Les protocoles et limites sont détaillés dans [Résultats IA](docs/MODEL_RESULTS.md).

## Lancement local

Prérequis : Docker avec Docker Compose, en mode conteneurs Linux.
Depuis la racine du dépôt :

```sh
docker compose up --build -d
docker compose ps
```

- Interface : http://localhost:5173
- API : http://localhost:8000/api/health/

Les modèles ne sont pas inclus dans Git.
L'inférence nécessite les deux fichiers Keras indiqués dans le guide de déploiement, placés localement sous `ia/models/`.

Commandes principales pour préparer MNIST, comparer les modèles et sélectionner le CNN :

```sh
docker compose exec ia python -m postal_ocr.mnist_import --download
docker compose exec ia python -m postal_ocr.mnist_split
docker compose exec ia python -m postal_ocr.train_mnist_models
docker compose exec ia python -m postal_ocr.tune_mnist_models
docker compose exec ia python -m postal_ocr.evaluate_mnist_final
```

Ces commandes s'exécutent explicitement : aucun entraînement ne démarre avec l'application.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Résultats IA](docs/MODEL_RESULTS.md)
- [Déploiement](docs/DEPLOYMENT.md)
- [Présentation animée du projet](presentation/index.html)

Gestion de projet : https://trello.com/b/jjTZnIxU
