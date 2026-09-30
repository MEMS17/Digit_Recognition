# Déploiement production : Vercel + VPS Plesk + Atlas

L'architecture recommandée sert le front React/Vite depuis Vercel. Le VPS Plesk exécute uniquement Django/Gunicorn et le service FastAPI IA dans Docker ; Plesk/Nginx termine HTTPS et relaie les requêtes API vers Django. MongoDB est fourni par Atlas et les modèles `.keras` restent des fichiers locaux hors Git sur le VPS.

```text
Vercel (React/Vite) --HTTPS--> Plesk/Nginx --HTTP local--> Django :8086
                                                    |
                                                    | réseau Docker
                                                    v
                                             FastAPI IA :8001
                                                    |
                                                    v
                                             MongoDB Atlas
```

FastAPI n'est jamais publié sur Internet. Le navigateur appelle uniquement `https://<backend-public>/api`; Django joint l'IA via `IA_SERVICE_URL=http://ia:8001`.

## Préparer le VPS

Installer Docker Engine et Docker Compose Plugin sur le VPS. Créer les artefacts modèles en dehors du dépôt avec la structure exacte suivante :

```text
/srv/digit-recognition/models/
├── mnist_tuning_v1/cnn_tuned.keras
└── postal_digit_synthetic_v1/postal_digit_cnn.keras
```

Ne pas copier ces fichiers dans Git ni dans l'image Docker. Le service IA les reçoit en lecture seule sur `/app/models` via `MODEL_DIR_HOST=/srv/digit-recognition/models`. Leur absence ne déclenche aucun entraînement et produit `503 model_unavailable` à l'inférence concernée.

Copier `deploy/production.env.example` vers `.env.production`, sans versionner ce fichier, puis renseigner :

```text
DJANGO_SECRET_KEY=<secret-long-et-aleatoire>
DJANGO_ALLOWED_HOSTS=<backend-public>
MONGODB_URI=<uri-atlas>
MONGODB_DATABASE=postal_ocr
CORS_ALLOWED_ORIGINS=https://<frontend>.vercel.app
MODEL_DIR_HOST=/srv/digit-recognition/models
```

`DJANGO_DEBUG` est fixé à `false` dans `compose.production.yaml`. Django fait confiance à `X-Forwarded-Proto: https` transmis par Plesk grâce à `SECURE_PROXY_SSL_HEADER`; aucun certificat TLS n'est géré par Docker. Les endpoints de prédiction et de revue restent `csrf_exempt`, conformément au contrat API existant.

## Démarrer les services Docker

Depuis la racine du dépôt sur le VPS :

```sh
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml up -d
docker compose --env-file .env.production -f compose.production.yaml ps
curl -f http://127.0.0.1:8086/api/health/
curl -f http://127.0.0.1:8086/api/health/ready/
```

Le compose de production ne contient que `back` et `ia`. Django/Gunicorn est lié à `127.0.0.1:8086` sur l'hôte ; FastAPI utilise uniquement `expose: 8001` sur le réseau Docker.

## Configurer Plesk / Nginx

Créer un domaine ou sous-domaine backend, par exemple `api.postal.example.fr`, activer son certificat HTTPS dans Plesk, puis ajouter les directives Nginx suivantes dans la configuration du domaine (champ **Additional Nginx directives** ou équivalent) :

```nginx
location / {
    proxy_pass http://127.0.0.1:8086;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
}
```

Plesk reste responsable du certificat, de la redirection HTTP vers HTTPS et de l'exposition publique. Ne pas ouvrir le port `8086` dans le pare-feu : il est lié à `127.0.0.1` uniquement. Après propagation DNS, vérifier :

```sh
curl -f https://<backend-public>/api/health/
curl -f https://<backend-public>/api/health/ready/
```

## Déployer le front sur Vercel

Importer le dépôt sur Vercel avec :

- **Root Directory** : `front`
- **Framework Preset** : `Vite`

Conserver `front/vercel.json`, qui gère le fallback SPA. Définir ces variables avant le build Vercel :

```text
VITE_API_BASE_URL=https://<backend-public>/api
VITE_USE_MOCKS=false
```

Reporter ensuite l'URL Vercel finale exacte dans `CORS_ALLOWED_ORIGINS` sur le VPS, puis redémarrer `back`. Il ne faut jamais employer `*` comme origine CORS de production.

## Alternatives non utilisées

`Dockerfile.huggingface`, `deploy/start-huggingface.sh`, `deploy/huggingface/README.md` et `ia/scripts/push_models_to_hub.py` sont conservés pour une alternative Hugging Face précédente. Ils ne sont pas utilisés par l'architecture recommandée Vercel + VPS Plesk + Atlas. Le développement local reste inchangé : `docker compose up --build` lance front, back, ia et MongoDB local.
