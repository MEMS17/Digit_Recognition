# API publique

Base de production : `https://api-digit.etsgsm.org/api`.
Les routes conservent leur slash final.
L'application est sans compte utilisateur ; seule la correction exige un jeton.

## Santé Django

`GET /api/health/` — aucun paramètre.

```sh
curl https://api-digit.etsgsm.org/api/health/
```

Réponse `200` : `{"status":"ok","service":"back"}`.
Ce contrôle indique que Django répond, sans vérifier MongoDB ni les modèles.

## Disponibilité du service IA

`GET /api/health/ready/` — aucun paramètre.

```sh
curl https://api-digit.etsgsm.org/api/health/ready/
```

Réponse `200` : `{"status":"ok","service":"back","ia":"reachable"}`.
Si l'IA ne répond pas, `503` : `{"status":"degraded","service":"back","ia":"unavailable"}`.
Ce contrôle ne garantit ni la disponibilité d'Atlas ni le chargement des modèles.

## Reconnaître un chiffre

`POST /api/v1/predictions/digit/`.

Paramètre multipart : un fichier `image`.

```sh
curl -F "image=@chiffre.png" https://api-digit.etsgsm.org/api/v1/predictions/digit/
```

Succès : `201 Created`, après inférence et persistance.
Principales erreurs : `400`, `413`, `415`, `422`, `503`.

## Lire un code postal

`POST /api/v1/predictions/postal-code/`.

Paramètres multipart : `image` et `input_kind=crop` pour une zone déjà recadrée.

```sh
curl -F "image=@code.png" -F "input_kind=crop" https://api-digit.etsgsm.org/api/v1/predictions/postal-code/
```

Succès : `201 Created`.
`input_kind=envelope` renvoie `503 capability_unavailable` :
la localisation sur une enveloppe complète n'est pas implémentée.
Principales autres erreurs : `400`, `413`, `415`, `422`, `503`.

## Images et réponse de prédiction

PNG ou JPEG uniquement, une image fixe de **5 MiB maximum**.
Chaque dimension est limitée à 12 000 pixels, avec au plus 12 000 000 pixels au total.
Les codes postaux sont des chaînes de cinq chiffres, zéros initiaux compris.

Extrait d'une réponse postale ; les valeurs ci-dessous sont illustratives :

```json
{
  "prediction_id": "2c0fb22f-2995-456d-a0a8-fda9b00bb837",
  "task": "postal_code",
  "value": "01234",
  "status": "needs_review",
  "score": 0.92,
  "model_version": "postal-digit-synthetic-v1",
  "reasons": ["acceptance_policy_unvalidated"],
  "review_token": "<jeton-de-correction>",
  "review": null
}
```

La réponse comprend aussi `bbox`, `image`, `preprocessing_version`,
`reference_check` et `created_at`.
Les coordonnées de `bbox` sont exprimées en pixels dans l'image orientée.
`task` vaut `digit` ou `postal_code`.

| Statut | Signification |
|---|---|
| `recognized` | Chiffre reconnu et proposé à l'utilisateur |
| `needs_review` | Proposition nécessitant une vérification humaine |
| `unreadable` | Aucune lecture complète ; `value` et `score` peuvent être nuls |

Le score est compris entre 0 et 1 lorsqu'il est disponible.
Il ne représente pas une certitude calibrée.
Le pipeline postal conserve la vérification humaine même avec un score élevé.

## Corriger ou confirmer

`PATCH /api/v1/predictions/{prediction_id}/review/`.

Corps JSON : `corrected_value`, exactement un chiffre ou cinq selon la prédiction.
Le jeton `review_token`, reçu uniquement à la création, sert exclusivement à la correction humaine.

```sh
curl -X PATCH https://api-digit.etsgsm.org/api/v1/predictions/2c0fb22f-2995-456d-a0a8-fda9b00bb837/review/ \
  -H "Content-Type: application/json" -H "Authorization: Bearer <review_token>" \
  -d '{"corrected_value":"01234"}'
```

Succès : `200`, avec la prédiction et `review: {"corrected_value":"01234","reviewed_at":"…"}`.
La correction ne remplace pas la lecture initiale.
Erreurs principales : `400` (format), `401` (jeton absent), `404` (prédiction inaccessible ou expirée).
Le délai de correction est de 30 jours après création.
Aucun endpoint public ne liste les prédictions.

## Erreurs communes

Les erreurs applicatives utilisent `{"error":{"code":"…","message":"…","fields":{}}}`.
Un proxy peut renvoyer une réponse non JSON.

| HTTP | Situation principale |
|---|---|
| 400 | Paramètre ou JSON invalide |
| 405 | Méthode non autorisée |
| 413 | Image trop volumineuse ou dimensions excessives |
| 415 | Format non pris en charge |
| 422 | Image vide ou indécodable |
| 503 | IA/modèle, stockage ou fonctionnalité indisponible |

## API interne

Django appelle FastAPI sur le réseau Docker via
`POST /internal/v1/infer/digit/` et `POST /internal/v1/infer/postal-code/`.
La santé interne est `GET /health`. Ces routes ne sont pas exposées au navigateur.
