# Déploiement

Le frontend est hébergé sur Vercel.
Django et FastAPI IA s'exécutent sur un VPS Plesk avec Docker.
MongoDB Atlas conserve les données ; les modèles Keras sont des fichiers locaux du VPS.

```text
Vercel
  ↓ HTTPS : api-digit.etsgsm.org
Cloudflare
  ↓
Plesk/Nginx
  ↓ HTTP : 127.0.0.1:8086
Django
  ├── MongoDB Atlas
  ↓ réseau Docker
FastAPI IA :8001
  ↓
Modèles Keras locaux, en lecture seule
```

## Installation

Installer Docker Engine et Docker Compose sur le VPS.
Faire pointer le domaine backend via Cloudflare vers le VPS.
Configurer le certificat HTTPS dans Plesk et utiliser Cloudflare en mode Full (strict).
TLS est géré en dehors des conteneurs.

Placer les deux modèles avec les droits de lecture nécessaires :

```text
/srv/digit-recognition/models/mnist_tuning_v1/cnn_tuned.keras
/srv/digit-recognition/models/postal_digit_synthetic_v1/postal_digit_cnn.keras
```

Ils sont montés en lecture seule dans `/app/models`.
Ils ne sont ni inclus dans Git ni copiés dans l'image.
Aucun entraînement ne démarre avec les services.

## Variables VPS

Copier `deploy/production.env.example` vers `.env.production`, ignoré par Git.
Renseigner les valeurs réelles uniquement sur le VPS :

| Variable | Valeur |
|---|---|
| `DJANGO_SECRET_KEY` | Secret long et aléatoire |
| `DJANGO_ALLOWED_HOSTS` | `api-digit.etsgsm.org,127.0.0.1` |
| `MONGODB_URI` | URI privée MongoDB Atlas |
| `MONGODB_DATABASE` | `postal_ocr` |
| `CORS_ALLOWED_ORIGINS` | `https://digit-recognition-zeta-six.vercel.app` |
| `MODEL_DIR_HOST` | `/srv/digit-recognition/models` |

Autoriser l'adresse de sortie du VPS dans Atlas et fournir un compte limité à la base utilisée.
`127.0.0.1` permet les contrôles de santé locaux.
Le compose impose `DJANGO_DEBUG=false` et `IA_SERVICE_URL=http://ia:8001`.
Les origines CORS sont explicites, sans joker.

## Commandes Docker Compose

Depuis la racine du dépôt sur le VPS :

```sh
docker compose --env-file .env.production -f compose.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml up -d
docker compose --env-file .env.production -f compose.production.yaml ps
docker compose --env-file .env.production -f compose.production.yaml logs -f
```

Le compose production contient uniquement `back` et `ia`.
Django est publié sur `127.0.0.1:8086:8000`.
Le port IA `8001` reste interne ; le frontend n'est pas hébergé sur le VPS.
Après modification des variables, relancer `up -d` pour recréer les services concernés.

## Configuration Plesk / Nginx

Dans les directives Nginx supplémentaires du domaine backend :

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8086;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_http_version 1.1;
    proxy_read_timeout 60s;
    client_max_body_size 6m;
}
```

Utiliser `location /api/` : Plesk génère déjà `location /`.
Plesk gère le certificat et la redirection HTTP vers HTTPS.
Django reconnaît HTTPS via `SECURE_PROXY_SSL_HEADER`.
L'en-tête `Host` est transmis directement ; `USE_X_FORWARDED_HOST` n'est pas nécessaire.

## Configuration Vercel

- Root Directory : `front`.
- Framework Preset : `Vite`.
- Conserver `front/vercel.json` pour le fallback SPA.

Variables utilisées au build :

```text
VITE_API_BASE_URL=https://api-digit.etsgsm.org/api
VITE_USE_MOCKS=false
```

Redéployer le front après toute modification de ces variables.

## Vérification

```sh
curl -f http://127.0.0.1:8086/api/health/
curl -f http://127.0.0.1:8086/api/health/ready/
curl -f https://api-digit.etsgsm.org/api/health/
curl -f https://api-digit.etsgsm.org/api/health/ready/
```

La première route vérifie Django ; la seconde vérifie aussi que l'IA est joignable.
Elles ne testent ni Atlas ni le chargement des modèles.
Une prédiction suivie d'une correction depuis le frontend complète la vérification fonctionnelle.
