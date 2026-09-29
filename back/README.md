# Back — API Django

Responsable : membre 1 (back et IA).

Le dossier contient uniquement le socle API. Le code d'entraînement et
d'inférence appartient à `../ia/`. Aucun modèle, import MNIST, endpoint de
prédiction ou traitement d'enveloppe n'est implémenté à cette étape.

Depuis la racine du dépôt, utiliser Docker Compose conformément au README
principal. Le serveur Django de développement écoute sur `0.0.0.0:8000`.
Il devra être remplacé par un serveur de production pour le déploiement.

## Contrat disponible

`GET /api/health/` retourne HTTP 200 :

```json
{"status": "ok", "service": "back"}
```

Ce contrôle vérifie uniquement que l'API répond. Il ne valide ni MongoDB ni
le service IA. Les autres méthodes retournent HTTP 405.

## Configuration

Les variables sont injectées par Docker Compose ; Django ne lit pas de fichier
`.env` directement.

| Variable | Utilisation |
| --- | --- |
| `DJANGO_SECRET_KEY` | Obligatoire, fournie par l'environnement |
| `DJANGO_DEBUG` | `true` uniquement en développement, défaut `false` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes séparés par des virgules |
| `MONGODB_URI` | URI locale ou `mongodb+srv://…` pour Atlas |
| `MONGODB_DATABASE` | Base applicative, défaut `postal_ocr` |

La persistance sera réalisée avec PyMongo. Aucun accès MongoDB n'est exécuté
au démarrage ; aucun modèle SQL ni migration Django n'est requis.
Ne jamais versionner les identifiants Atlas.

## Vérifications

```sh
docker compose run --rm back python manage.py check
```
