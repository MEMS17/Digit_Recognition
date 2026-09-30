# Backend Django

Django orchestre l'inférence et stocke les résultats avec PyMongo.
Les routes publiques sont décrites dans [API](../docs/API.md).

Depuis la racine du dépôt :

```sh
docker compose run --rm --no-deps back python manage.py check
docker compose logs -f back
```

Les variables sont injectées par Docker Compose : Django ne lit pas directement un fichier `.env`.
`IA_SERVICE_URL` définit l'adresse privée de FastAPI.
`MONGODB_URI` et `MONGODB_DATABASE` définissent la connexion MongoDB.
Aucune migration SQL n'est nécessaire.

Gunicorn sert Django en production ; les variables HTTPS et CORS sont décrites dans
[Déploiement](../docs/DEPLOYMENT.md).
