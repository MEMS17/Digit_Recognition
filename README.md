# Digit Recognition — lecture de codes postaux

Projet annuel : reconnaissance de chiffres manuscrits, puis lecture de codes postaux sur des courriers. Le dépôt contient une chaîne V1 : front React, API Django, service FastAPI IA et modèles expérimentés documentés. Le MVP lit une **zone postale déjà recadrée** ; la localisation automatique sur une enveloppe entière n'est pas encore disponible.

## Organisation

```text
front/       React + TypeScript : interface — collaborateur
back/        Django : API et persistance — toi + Codex
ia/          Python : données, entraînement et OCR — toi + Codex
docs/        Architecture et cartes Trello
compose.yaml Environnement Docker de développement
```

- [Architecture et périmètre](docs/ARCHITECTURE.md)
- [Contrat API pour le front et le back](docs/API.md)
- [Schéma MongoDB et règles d'import](docs/MONGODB.md)
- [Protocole d'évaluation IA](docs/EVALUATION.md)
- [Périmètre des courriers et scénarios d'acceptation](docs/POSTAL_SCOPE.md)
- [40 cartes Trello triées par priorité et assignées](docs/TRELLO.md)
- [Front](front/README.md), [Back](back/README.md), [IA](ia/README.md)

## Démarrage local

Prérequis : Docker Desktop démarré en mode conteneurs Linux, avec Docker Compose. Exécuter les commandes depuis ce dossier.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Ne recopier `.env.example` que lors de la première installation pour préserver les réglages existants. Les valeurs de secours permettent aussi un démarrage local sans `.env`.

- Interface : http://localhost:5173 (mocks activables par `VITE_USE_MOCKS=true`)
- Santé API : http://localhost:8000/api/health/
- Santé via proxy front : http://localhost:5173/api/health/

```powershell
docker compose logs -f
docker compose exec back python manage.py check
docker compose exec front npm run build
docker compose exec ia python -c "import postal_ocr, sklearn, pymongo"
docker compose stop
```

`docker compose down` retire les conteneurs et le réseau, mais conserve les volumes. Le volume MongoDB conserve les données. Ne pas utiliser `down -v` si ces données doivent être gardées.

Les sources sont montées pour le développement. Après une modification de dépendances, reconstruire les images. Pour synchroniser le volume de dépendances front avec le lockfile : `docker compose exec front npm ci`.

## Configuration

Les variables sont décrites dans `.env.example`. Le navigateur passe par `/api`, sans URL interne Docker. Le proxy Vite cible `http://back:8000`.

MongoDB local n'est exposé que sur le réseau Docker. Pour Atlas, renseigner `MONGODB_URI` et autoriser l'accès réseau dans Atlas. L'import MNIST local se lance avec `docker compose exec ia python -m postal_ocr.mnist_import --download` ; il conserve les CSV et les données dans des emplacements ignorés par Git. Aucun secret ni jeu de données ne doit être commité.

## Collaboration et livraison

Toi avec Codex : back et IA. Collaborateur : front et déploiement. Les agents travaillent dans des dossiers exclusifs, le coordinateur gère les fichiers communs. Les interfaces sont convenues avant les développements qui en dépendent. Aucun commit ni push automatique.

Ce Compose est un environnement de développement. La production recommandée est décrite dans [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) : Vercel pour le front, VPS Plesk pour Django et l'IA interne, fichiers modèles locaux sur le VPS et Atlas pour les données. La configuration Hugging Face est conservée comme alternative non utilisée.
