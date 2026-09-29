# Architecture et périmètre

## Objectif

Lire un code postal français de cinq chiffres sur une image de courrier. Conserver les zéros initiaux : un code postal est une chaîne de caractères. Le MVP commence par une zone postale recadrée, puis la chaîne complète localise cette zone sur une enveloppe. L'application de dessin d'un chiffre demandée par le sujet reste un parcours distinct à livrer.

## Séparation

- `front/` : React, TypeScript et Vite. Dessin, import d'image, résultats et correction humaine. Responsable : collaborateur.
- `back/` : Django et pymongo. API publique, validation des images, orchestration de l'inférence et persistance. Responsable : toi avec Codex.
- `ia/` : exploration, import des données, entraînement, évaluation, localisation, segmentation et export des modèles. Responsable : toi avec Codex.
- `docs/` : décisions, contrat API et planning commun.
- `compose.yaml` : environnement Docker local partagé. Déploiement futur : collaborateur.

Le front appelle `/api` ; Vite transmet au back sur le réseau Docker. MongoDB n'est pas exposé sur le poste. Le service IA sert actuellement d'espace de travail, sans serveur d'inférence. L'interface entre le back et l'IA sera définie avant leur intégration : paquet Python versionné et artefacts de modèle, ou service interne si les dépendances le justifient. Aucun modèle n'est simulé dans cette initialisation.

## Données

MongoDB local facilite le développement ; MongoDB Atlas reste la cible exigée pour la livraison. Même configuration par `MONGODB_URI` et `MONGODB_DATABASE`. Collections prévues : `mnist_train`, `mnist_test`, `predictions`. Le format final des documents sera défini dans la prochaine phase. Les images doivent respecter les limites de taille BSON ; décider alors entre encodage compact, GridFS ou stockage objet selon leur taille.

L'entraînement charge MNIST depuis MongoDB. Créer la validation à partir du train et réserver le test à l'évaluation finale. Pour les courriers, constituer un jeu annoté distinct, avec séparation par scripteur/enveloppe pour éviter les fuites. Utiliser des courriers fictifs ou autorisés et limiter la conservation des adresses.

## Chaîne cible, non implémentée

Image → validation → correction d'orientation/contraste → localisation de la zone postale → segmentation ou lecture de séquence → reconnaissance → contrôle de format/référentiel → résultat ou vérification humaine.

Une valeur présente dans un référentiel ne prouve pas que la lecture est correcte. Le score du modèle ne doit pas être présenté comme une probabilité fiable sans validation/calibration. Mesurer le taux de codes entièrement corrects, les erreurs acceptées, le taux de révision et la latence.

## Organisation des agents

Un agent back travaille uniquement dans `back/`, un agent front dans `front/`, un agent IA dans `ia/`. Le coordinateur gère la racine et `docs/`, puis vérifie les interfaces. Une modification transverse nécessite coordination avant édition. Cette séparation technique ne change pas la répartition des deux membres du groupe. Aucun push automatique. L'étape suivante ne commence qu'après accord de l'utilisateur.

## Limite du socle

Compose est destiné au développement : serveurs de développement, MongoDB interne sans authentification, secret local de secours. La configuration de production, Atlas, HTTPS, secrets, limites d'upload et politique de conservation font partie des tâches de déploiement ; ce fichier ne doit pas être publié tel quel.
