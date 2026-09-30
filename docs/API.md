# Contrat API v1

Statut : V1 implémentée. Les routes publiques de prédiction, de revue et de santé sont servies par Django ; l'inférence est déléguée au service FastAPI IA interne. Les exemples illustrent le contrat et ne constituent pas une promesse de taux de réussite. Responsable : binôme back/IA ; consommateur : collaborateur front/déploiement.

## Conventions

Le front utilise des chemins relatifs `/api/`. En développement, Vite les transmet au back via Docker. Les endpoints v1 conservent leur slash final. JSON utilise UTF-8 ; les dates sont des chaînes UTC ISO 8601. Les chiffres et codes postaux sont des chaînes, afin de conserver les zéros initiaux.

Les opérations de prédiction sont synchrones. Un `201 Created` signifie que l'inférence et la persistance sont terminées, y compris pour un résultat illisible. Une panne de MongoDB ne doit jamais produire un succès non enregistré. Aucun endpoint public ne permet de lister ou relire des prédictions. Les images et les jetons ne figurent pas dans les journaux applicatifs.

## Santé existante

`GET /api/health/` retourne `200 OK` :

```json
{"status":"ok","service":"back"}
```

Ce contrôle indique uniquement que le processus Django répond. Il ne garantit ni MongoDB disponible ni modèle chargé. Il ne faut pas l'utiliser pour annoncer au front que l'inférence est prête.

`GET /api/health/ready/` retourne `200 OK` si Django répond et si le service IA interne est joignable :

```json
{"status":"ok","service":"back","ia":"reachable"}
```

Il retourne `503` avec `ia: "unavailable"` sinon. Cette route ne teste ni Atlas ni le chargement des modèles et n'expose aucun détail interne.

## Validation commune des images

Les deux créations acceptent `multipart/form-data`, avec exactement un fichier `image`. Un canvas est exporté en PNG par le front.

- Formats acceptés : PNG ou JPEG, détectés par signature et décodage, sans se fier à l'extension ou au MIME déclaré.
- Fichier : au maximum 5 MiB (5 242 880 octets). Corps multipart : au maximum 6 MiB, également imposé au proxy.
- Image : largeur et hauteur strictement positives, chacune au maximum 12 000 pixels, produit au maximum 12 000 000 pixels ; vérifier les dimensions avant le décodage complet.
- Une seule image fixe : fichiers animés et formats multiples refusés. Les images invalides ou tronquées sont refusées.
- Pour l'inférence, appliquer l'orientation EXIF, composer la transparence sur fond blanc, puis convertir en RGB. La base conserve les octets source pour la traçabilité pendant la durée de conservation ; les réponses ne renvoient ni image ni métadonnées source.
- Les coordonnées de sortie se rapportent à cette image après orientation, avant tout redimensionnement du modèle. `image.width` et `image.height` en sont les dimensions.

`bbox` est un rectangle en pixels entiers `{x,y,width,height}` : origine en haut à gauche, x vers la droite, y vers le bas ; rectangle demi-ouvert `[x,x+width) × [y,y+height)`, entièrement contenu dans l'image. Pour `digit` et `crop`, il couvre l'image entière ; pour `envelope`, il désigne la zone postale détectée, ou vaut `null` si aucune zone exploitable n'est localisée. Toute transformation interne doit être inversée pour fournir ces coordonnées.

## Reconnaître un chiffre

`POST /api/v1/predictions/digit/`

Champ multipart requis : `image`. Aucun `input_kind` sur cette route : la base utilise implicitement `canvas`. Exemple de réponse `201 Created` :

```json
{
  "prediction_id": "95f68fe7-59ad-45db-b989-ed854026c07f",
  "task": "digit",
  "value": "7",
  "status": "recognized",
  "score": 0.97,
  "bbox": {"x": 0, "y": 0, "width": 280, "height": 280},
  "image": {"width": 280, "height": 280},
  "model_version": "digit-example-v1",
  "preprocessing_version": "digit-preprocessing-v1",
  "reasons": [],
  "reference_check": {"status": "not_applicable", "version": null},
  "created_at": "2026-09-29T12:00:00Z",
  "review_token": "EXAMPLE_ONLY_REPLACE_WITH_RANDOM_OPAQUE_TOKEN",
  "review": null
}
```

## Reconnaître un code postal

`POST /api/v1/predictions/postal-code/`

Champs multipart requis : `image` et `input_kind`, égal à `crop` (zone postale déjà recadrée) ou `envelope` (courrier entier). La cible est exactement cinq chiffres ASCII, sans espaces. Tant que la localisation n'est pas disponible, `envelope` renvoie `503 capability_unavailable` ; aucun résultat fictif ni bascule silencieuse vers `crop`.

Exemple de réponse `201 Created`, nécessitant une vérification :

```json
{
  "prediction_id": "2c0fb22f-2995-456d-a0a8-fda9b00bb837",
  "task": "postal_code",
  "value": "01230",
  "status": "needs_review",
  "score": 0.68,
  "bbox": {"x": 600, "y": 420, "width": 340, "height": 80},
  "image": {"width": 1600, "height": 1000},
  "model_version": "postal-pipeline-example-v1",
  "preprocessing_version": "postal-preprocessing-v1",
  "reasons": ["low_score"],
  "reference_check": {"status": "not_checked", "version": null},
  "created_at": "2026-09-29T12:01:00Z",
  "review_token": "EXAMPLE_ONLY_REPLACE_WITH_RANDOM_OPAQUE_TOKEN",
  "review": null
}
```

## Sémantique du résultat

| Champ | Règle |
|---|---|
| `prediction_id` | UUID v4 généré par le back ; ne constitue pas une autorisation. |
| `task` | `digit` ou `postal_code`. |
| `value` | Une ou cinq positions ASCII `[0-9]` selon la tâche ; `null` si aucune valeur complète valide n'est disponible. |
| `status` | `recognized` : valeur complète et critères d'acceptation validés ; `needs_review` : valeur complète proposée mais incertaine ; `unreadable` : aucune valeur complète proposée, `value=null`. |
| `score` | Nombre fini entre 0 et 1, ou `null` si indisponible. Score interne non calibré : ne pas afficher « probabilité d'être correct ». Pour un code segmenté, minimum des scores des cinq chiffres ; définition et seuil liés à la version du pipeline. |
| `model_version` | Version immuable du modèle ou manifeste du pipeline complet, incluant localisateur et reconnaisseur pour une enveloppe. |
| `preprocessing_version` | Version immuable de la chaîne de transformation. |
| `reasons` | Liste de codes stables ; vide pour `recognized`, au moins un code pour les autres états. |
| `reference_check` | `not_applicable` pour un chiffre ; sinon `not_checked`, `found` ou `not_found`, avec version du référentiel si utilisé. Un code existant ne prouve pas une bonne lecture. |
| `review_token` | Secret opaque retourné seulement à la création ; absent des réponses ultérieures. |
| `review` | `null` initialement, puis annotation humaine distincte de la prédiction. |

Codes `reasons` v1 : `low_score`, `score_unavailable`, `acceptance_policy_unvalidated`, `reference_not_found`, `no_postal_region`, `multiple_postal_regions`, `segmentation_failed`, `invalid_digit_count`, `no_digit_detected`. En présence de plusieurs zones concurrentes sans sélection fiable : `unreadable`, `value=null`, `bbox=null`. Une valeur hors référentiel impose `needs_review`. Un référentiel indisponible donne `not_checked` et ne constitue pas seul un rejet. Les seuils d'acceptation sont choisis sur validation et versionnés ; aucune valeur universelle n'est fixée ici. Sans politique d'acceptation validée, une valeur complète reste `needs_review` avec la raison `acceptance_policy_unvalidated`.

Une image valide contenant zéro, quatre ou six chiffres est un résultat métier `201 unreadable`, pas une erreur HTTP. L'échec technique d'un modèle disponible est une erreur serveur.

## Correction humaine sans compte utilisateur

`PATCH /api/v1/predictions/{prediction_id}/review/`

En-têtes : `Content-Type: application/json`, `Authorization: Bearer <review_token>`.

```json
{"corrected_value":"01280"}
```

Le back exige une chaîne correspondant exactement à `[0-9]{1}` pour un chiffre ou `[0-9]{5}` pour un code postal. La même valeur peut être soumise pour confirmer la lecture. La correction n'écrase jamais `value`, `score`, `status`, ni les versions du résultat original. Elle ne déclenche pas de réentraînement et n'est pas automatiquement une vérité terrain validée.

Réponse `200 OK` après persistance de l'annotation :

```json
{
  "prediction_id": "2c0fb22f-2995-456d-a0a8-fda9b00bb837",
  "task": "postal_code",
  "value": "01230",
  "status": "needs_review",
  "score": 0.68,
  "bbox": {"x": 600, "y": 420, "width": 340, "height": 80},
  "image": {"width": 1600, "height": 1000},
  "model_version": "postal-pipeline-example-v1",
  "preprocessing_version": "postal-preprocessing-v1",
  "reasons": ["low_score"],
  "reference_check": {"status": "not_checked", "version": null},
  "created_at": "2026-09-29T12:01:00Z",
  "review": {"corrected_value": "01280", "reviewed_at": "2026-09-29T12:02:00Z"}
}
```

Générer le jeton avec au moins 256 bits aléatoires cryptographiques ; conserver seulement son empreinte SHA-256 côté base, comparer en temps constant et transmettre via HTTPS en production. Le front le garde en mémoire le temps du parcours, jamais dans l'URL ni dans les logs. La perte du jeton interdit une correction ultérieure depuis cette session. Une nouvelle correction autorisée remplace l'annotation actuelle ; répéter la même correction laisse son horodatage inchangé. Cette capacité de correction ne constitue pas une authentification de personne.

La prédiction et ses données expirent 30 jours après `created_at`. Le serveur refuse toute correction à partir de cette échéance avec `404 prediction_not_found`, même si le nettoyage TTL de MongoDB n'a pas encore supprimé le document. Une correction ne prolonge jamais cette durée. L'annotation reste non vérifiée pour l'usage IA ; l'API ne publie ni les octets d'image, ni leur empreinte, ni l'empreinte du jeton.

## Erreurs

Enveloppe JSON commune (les erreurs du proxy peuvent ne pas respecter ce format, le front doit le tolérer) :

```json
{
  "error": {
    "code": "invalid_field",
    "message": "input_kind doit valoir crop ou envelope.",
    "fields": {"input_kind": "Valeur non acceptée."}
  }
}
```

| HTTP | Codes et situations |
|---|---|
| `400` | `invalid_request` : multipart/JSON mal formé ; `invalid_field` : champ requis absent, inconnu, dupliqué ou valeur incorrecte ; `fields` détaille les champs. |
| `401` | `review_token_required` : bearer absent ou mal formé. |
| `404` | `prediction_not_found` : UUID inconnu ou jeton incorrect, même réponse pour éviter l'énumération ; UUID mal formé également. |
| `405` | `method_not_allowed` : méthode incompatible avec la route. |
| `413` | `image_too_large` ou `request_too_large` : octets, dimensions ou pixels dépassés. |
| `415` | `unsupported_media_type` : type de requête ou format réel du fichier non accepté, y compris animation. |
| `422` | `invalid_image` : fichier d'un format accepté mais corrompu ou impossible à décoder ; ne sert pas pour une écriture illisible. |
| `429` | `rate_limited` si limitation activée au déploiement ; respecter `Retry-After` lorsqu'il est fourni. |
| `503` | `model_unavailable`, `capability_unavailable` ou `storage_unavailable` : dépendance indisponible ; aucune création annoncée comme réussie. |
| `500` | `internal_error` : incident inattendu, sans trace technique dans la réponse. |

Pour une erreur sans champ concerné, `fields` vaut `{}`. Le front utilise `code` pour son comportement, `message` pour l'explication. Un POST relancé après interruption réseau peut créer un doublon : pas de répétition automatique des créations dans cette version, ni de garantie d'idempotence implicite.

## États à prévoir dans le front

1. Saisie/import : aperçu de l'image orientée et choix explicite zone recadrée/courrier ; garder les zéros initiaux dans tous les champs.
2. Envoi et traitement : indicateur d'attente, bouton désactivé pour empêcher les doubles clics.
3. `recognized` : afficher la valeur et permettre sa confirmation/correction ; aucune prétention de certitude absolue.
4. `needs_review` : afficher la proposition, les raisons compréhensibles et la correction manuelle.
5. `unreadable` : expliquer l'absence de lecture, permettre une nouvelle image ou une saisie manuelle liée à la prédiction.
6. Correction : attente puis confirmation uniquement après `200`, afficher la correction séparément de la lecture initiale.
7. Erreur : validation locale utile mais serveur faisant autorité ; traiter dépendance indisponible, limite d'upload et réponse non JSON. Un timeout ne signifie pas nécessairement que la prédiction n'a pas été enregistrée.

Les éventuels fixtures front reprennent les exemples de ce document et sont explicitement présentés comme données de démonstration. Aucun endpoint simulé ne doit être présenté comme une inférence réelle.
