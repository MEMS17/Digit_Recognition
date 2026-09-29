# Schéma MongoDB — contrat v1

Statut : spécification à implémenter, aucune collection ni aucun index créés par cette étape. Responsable A (back et IA). Base `postal_ocr`, sélectionnée avec `MONGODB_DATABASE`, connexion par `MONGODB_URI`. Le même schéma s'applique au service Docker local et à Atlas.

## 1. MNIST : `mnist_train` et `mnist_test`

Un document représente une image. Champs obligatoires :

| Champ | Type BSON | Règle |
|---|---|---|
| `_id` | string | `mnist-v1:train:000000` ou `mnist-v1:test:000000`, index source à partir de zéro |
| `schema_version` | int | `1` |
| `dataset_version` | string | `mnist-v1`, attaché à un manifeste de sources immuable |
| `source_index` | int | Numéro de ligne de données, sans en-tête, à partir de zéro |
| `label` | int | 0 à 9 |
| `pixels` | binData | 784 octets uint8, ordre ligne par ligne, sans normalisation flottante |
| `width`, `height` | int | 28 et 28 |
| `pixel_sha256` | string | SHA-256 hexadécimal des 784 octets |
| `source_sha256` | string | SHA-256 du fichier CSV source exact |
| `imported_at` | date | UTC, date de première insertion |

Le split officiel est déterminé par la collection. Ne pas stocker la validation dans `mnist_test` : un manifeste de splits versionné affecte les identifiants du train à entraînement/validation, selon [EVALUATION.md](EVALUATION.md). Lecture des octets avec uint8, conversion/normalisation ensuite dans le prétraitement.

Index : `_id` unique natif ; index composé unique `(dataset_version, source_index)` ; index non unique `(dataset_version, label)`. Le hash de pixels n'est pas unique : des images identiques peuvent exister. Auditer les doublons et les conflits de labels plutôt que supprimer aveuglément des lignes du benchmark.

## 2. Import relançable à construire ensuite

1. Valider les sources, provenance, format CSV avec ou sans en-tête, 785 colonnes par ligne, valeurs entières et pixels dans `[0,255]`. Ne pas deviner silencieusement un format ambigu.
2. Écrire un manifeste local sans données personnelles : URLs, sommes SHA-256, dimensions, version du dataset et comptes attendus. Pour le MNIST officiel complet : 60 000 train et 10 000 test ; ces comptes doivent être vérifiés après import. [Source MNIST](https://yann.lecun.org/exdb/mnist/index.html).
3. Traiter par lots bornés (par exemple 1 000 documents) et utiliser des upserts sur les identifiants déterministes. Un document existant identique reste inchangé ; une différence de source, pixels ou label sous le même identifiant provoque un échec explicite, sans écrasement.
4. Une interruption permet la reprise. Un import partiel n'est pas prêt pour l'entraînement : le script de validation doit réussir avant toute lecture d'entraînement. Aucune suppression de collection automatique.
5. Vérifier comptes, types, tailles, labels, hashes et séparation des identifiants, puis produire un rapport local. Relancer doit ajouter zéro doublon.

## 3. `predictions`

Un document persiste la prédiction et l'image envoyée dans une seule insertion. Les champs API sont définis dans [API.md](API.md). Le document n'est jamais renvoyé brut au navigateur.

| Champ | Type / contenu | Règle |
|---|---|---|
| `_id` | string UUID v4 | Exposé comme `prediction_id` |
| `schema_version` | int | `1` |
| `task` | string | `digit` ou `postal_code` |
| `input_kind` | string | `canvas` pour chiffre ; `crop` ou `envelope` pour code |
| `image.bytes` | binData | Fichier original validé PNG/JPEG, au plus 5 MiB |
| `image.mime_type` | string | Format réellement décodé, pas seulement le Content-Type annoncé |
| `image.sha256` | string | SHA-256 des octets originaux |
| `image.width`, `image.height` | int | Dimensions après application de l'orientation EXIF, chacune ≤ 12 000 et produit ≤ 12 000 000 pixels |
| `image.orientation_applied` | bool | `true` : repère de coordonnées après normalisation EXIF, octets originaux conservés |
| `value` | string ou null | Exactement un chiffre ASCII, ou cinq selon la tâche ; zéro initial conservé |
| `status` | string | `recognized`, `needs_review` ou `unreadable` |
| `score` | double ou null | `[0,1]` si disponible ; pas une probabilité calibrée implicite |
| `bbox` | objet ou null | `{x,y,width,height}`, pixels entiers bornés dans l'image orientée ; absent si pas de zone déterminée |
| `model_version` | string | Version de l'artefact/pipeline réellement utilisé |
| `preprocessing_version` | string | Version du traitement réellement utilisé |
| `reasons` | tableau de strings | Codes définis dans le contrat API |
| `reference_check` | objet | `{status, version}` selon le contrat API |
| `review_token_hash` | string | SHA-256 du jeton aléatoire, jamais le jeton en clair |
| `review` | objet ou null | `{corrected_value, reviewed_at}` ; correction utilisateur non vérifiée |
| `created_at` | date UTC | Création serveur |
| `expires_at` | date UTC | Création + 30 jours, non prolongée par une correction |

Le jeton de révision est produit avec 32 octets cryptographiquement aléatoires et encodé en base64url. Le client le reçoit une seule fois, à la création ; seul son hash est conservé. Pas de journalisation du jeton ni du corps image. La possession du jeton permet la correction, sans compte utilisateur. Aucun endpoint de consultation globale publique n'est prévu.

La correction met à jour uniquement `review` de manière atomique, sans écraser `value`, `score` ou les versions. Même valeur renvoyée : opération idempotente, `reviewed_at` inchangé. Nouvelle correction : dernière valeur remplace la précédente, sans historique à ce stade. Ne pas traiter ces corrections comme labels d'entraînement fiables ; une revue humaine séparée sera nécessaire.

Index : `_id` unique natif ; `(created_at)` pour exploitation interne ; `(task, status, created_at)` pour analyses internes ; TTL sur `expires_at` avec `expireAfterSeconds: 0`. Le serveur refuse les révisions lorsque `expires_at <= maintenant`, même si le document existe encore : la suppression TTL est asynchrone. [Documentation TTL MongoDB](https://www.mongodb.com/docs/manual/core/index-ttl/).

La conservation de 30 jours est une décision du projet, pas une obligation réglementaire. Le TTL supprime ensemble image et résultat ; les sauvegardes doivent avoir leur propre durée de conservation documentée au déploiement.

## 4. Choix de stockage et validation

Stocker les fichiers originaux binaires directement dans `predictions` ; ne pas encoder en base64 et ne pas stocker une image réencodée potentiellement plus volumineuse. Avec une limite de 5 MiB pour l'image et des métadonnées bornées, la taille reste sous le maximum MongoDB de 16 MiB par document. Vérifier aussi la taille BSON avant insertion. GridFS n'est pas nécessaire dans ce périmètre. [Limite des documents BSON](https://www.mongodb.com/docs/v8.0/core/document/).

Les validators MongoDB à implémenter imposeront les types, champs requis et enums. La validation applicative vérifiera en complément longueur exacte des pixels, cohérence tâche/valeur, géométrie bbox, taille BSON et état de révision. Les dates sont des dates BSON, pas des strings ; les réponses HTTP les convertissent en ISO 8601 UTC.

Pas d'index unique sur les images utilisateur : un nouvel envoi est une nouvelle prédiction. Pas de transaction multidocument nécessaire pour cette version. Une erreur d'insertion entraîne une erreur API, sans réponse de succès prétendant que le résultat est conservé.

## 5. Préparer Atlas sans le configurer maintenant

- B crée le projet/cluster de déploiement et configure l'accès réseau du serveur ; A définit les utilisateurs et droits nécessaires avec B.
- Identité d'import : écriture sur les collections MNIST ; identité d'entraînement : lecture de MNIST ; identité API : lecture/écriture de `predictions`. L'identité de bootstrap des index/validators est distincte à terme.
- Secrets injectés via environnement, jamais dans Git ni les logs. Utiliser l'URI fournie par Atlas et conserver TLS ; ne pas désactiver la validation des certificats.
- Mesurer volume importé et capacité disponible avant de choisir une offre ; aucun dimensionnement ou quota gratuit n'est supposé garanti.
- Le Compose actuel conserve son MongoDB local. Le passage à Atlas et l'éventuel profil Compose sans Mongo local seront une modification ultérieure.

## 6. Critères de validation de l'implémentation future

Import complet contrôlé, reprise après interruption, deuxième exécution sans doublons, entrée malformée rejetée, conflit de version non écrasé, lecture IA depuis MongoDB, insertion image + prédiction, correction autorisée uniquement avec le jeton correspondant, prédiction originale conservée et refus après expiration. Aucun de ces contrôles fonctionnels n'est exécuté pendant ce cadrage.
