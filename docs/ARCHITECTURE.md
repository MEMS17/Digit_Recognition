# Architecture et périmètre

## Objectif

Lire un code postal français de cinq chiffres sur une image de courrier. Conserver les zéros initiaux : un code postal est une chaîne de caractères. Le MVP commence par une zone postale recadrée, puis la chaîne complète localise cette zone sur une enveloppe. L'application de dessin d'un chiffre demandée par le sujet reste un parcours distinct à livrer.

## Séparation

- `front/` : React, TypeScript et Vite. Dessin, import d'image, résultats et correction humaine. Responsable : collaborateur.
- `back/` : Django et pymongo. API publique, validation des images, orchestration de l'inférence et persistance. Responsable : toi avec Codex.
- `ia/` : exploration, import des données, entraînement, évaluation, localisation, segmentation et export des modèles. Responsable : toi avec Codex.
- `docs/` : décisions, contrat API et planning commun.
- `compose.yaml` : environnement Docker local partagé. Déploiement futur : collaborateur.

Le front appelle `/api` ; Vite transmet au back sur le réseau Docker. MongoDB n'est pas exposé sur le poste. Le service IA écoute sur le port interne 8001, sans publication sur le poste : le back conserve l'API publique et la persistance, puis appelle l'IA via `IA_SERVICE_URL`. En production recommandée, Vercel sert le front, un VPS Plesk héberge Django et l'IA interne, MongoDB Atlas remplace le conteneur local et les modèles sont montés en lecture seule depuis le VPS. L'ancienne configuration Hugging Face reste une alternative non utilisée, documentée dans [DEPLOYMENT.md](DEPLOYMENT.md).

## Contrats V1 implémentés

- [API.md](API.md) : routes publiques, limites image, résultats, erreurs et correction.
- [MONGODB.md](MONGODB.md) : types, index et import relançable des trois collections.
- [EVALUATION.md](EVALUATION.md) : splits, comparaison des modèles et objectifs à mesurer.
- [POSTAL_SCOPE.md](POSTAL_SCOPE.md) : courrier destinataire, corpus et scénarios d'acceptation.

Ces documents définissent le contrat V1 exploité par le front, Django et le service IA. La santé, les créations de prédiction et la revue humaine sont disponibles ; l'enveloppe complète reste explicitement hors du MVP.

### Frontière back / IA retenue

À l'intégration, l'IA écoutera sur le port interne 8001, sans publication sur le poste ou Internet. Deux routes internes synchrones sont prévues : `POST /internal/v1/infer/digit/` et `POST /internal/v1/infer/postal-code/`. Multipart identique aux routes publiques (`image`, plus `input_kind` pour le code). Le back valide et conserve les octets originaux ; il les transmet à l'IA. L'IA applique une seule fois EXIF, composition alpha et prétraitement versionné. Le back calcule les dimensions orientées pour valider le résultat, sans réencoder le fichier transmis.

L'IA retourne HTTP 200 avec les champs métier du contrat public : `task`, `value`, `status`, `score`, `bbox`, `image` (dimensions), `model_version`, `preprocessing_version`, `reasons`, `reference_check`. Elle effectue le contrôle de référentiel et la décision de révision dans le pipeline versionné. Elle ne produit ni identifiant de prédiction, ni jeton, ni date de création, ni correction, et n'écrit pas dans `predictions`. Le back valide cette réponse, attribue les champs de persistance, insère puis retourne HTTP 201 au front. Toute sortie IA incohérente est un incident serveur, jamais transmise comme succès.

Le contrat d'erreur interne suit les codes image/modèle de l'API publique ; indisponibilité réseau ou délai dépassé devient `503 model_unavailable`, réponse invalide devient `500 internal_error`. Fixer au départ un timeout de connexion de 2 s et de lecture de 30 s, configurables ; aucune relance automatique d'inférence. Ces délais sont des limites techniques et non des objectifs de latence. Aucun entraînement au démarrage : artefacts chargés explicitement, absence d'artefact signalée par `503`.

Le service d'inférence n'a pas besoin d'accès en écriture à MongoDB. Les commandes d'import et d'entraînement, exécutées séparément dans l'environnement IA, utilisent leurs propres droits. Le déploiement de B devra conserver les routes internes privées ; tout accès réseau hors réseau Docker de confiance exigera une protection entre services.

## Données

MongoDB local facilite le développement ; MongoDB Atlas reste la cible exigée pour la livraison. Même configuration par `MONGODB_URI` et `MONGODB_DATABASE`. Collections prévues : `mnist_train`, `mnist_test`, `predictions`. Le contrat de stockage retient des pixels MNIST uint8 binaires et les fichiers utilisateurs originaux en BSON Binary, limités à 5 MiB, avec résultat et expiration dans le même document. Voir [MONGODB.md](MONGODB.md).

L'entraînement charge MNIST depuis MongoDB. Créer la validation à partir du train et réserver le test à l'évaluation finale. Pour les courriers, constituer un jeu annoté distinct, avec séparation par scripteur/enveloppe pour éviter les fuites. Utiliser des courriers fictifs ou autorisés et limiter la conservation des adresses.

## Chaîne cible, non implémentée

Image → validation → correction d'orientation/contraste → localisation de la zone postale → segmentation ou lecture de séquence → reconnaissance → contrôle de format/référentiel → résultat ou vérification humaine.

Une valeur présente dans un référentiel ne prouve pas que la lecture est correcte. Le score du modèle ne doit pas être présenté comme une probabilité fiable sans validation/calibration. Mesurer le taux de codes entièrement corrects, les erreurs acceptées, le taux de révision et la latence.

## Organisation des agents

Pour le code, un agent back travaille uniquement dans `back/`, un agent front dans `front/`, un agent IA dans `ia/`. Le coordinateur gère la racine et `docs/`, puis vérifie les interfaces. Pour une phase documentaire, il peut attribuer un fichier de spécification distinct à chaque agent ; aucun fichier n'est édité simultanément. Une modification transverse nécessite coordination avant édition. Cette séparation technique ne change pas la répartition des deux membres du groupe. Aucun push automatique. L'étape suivante ne commence qu'après accord de l'utilisateur.

## Limite du socle

Compose est destiné au développement : serveurs de développement, MongoDB interne sans authentification, secret local de secours. La configuration de production, Atlas, HTTPS, secrets, limites d'upload et politique de conservation font partie des tâches de déploiement ; ce fichier ne doit pas être publié tel quel.
