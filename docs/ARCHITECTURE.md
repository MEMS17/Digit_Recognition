# Architecture

## Vue générale

Le front React/TypeScript construit avec Vite est hébergé sur Vercel.
Il propose le dessin, l'import d'image, l'affichage des résultats et la correction humaine.

Django est le backend public, exécuté avec Gunicorn sur un VPS Plesk :

- réception et validation des requêtes ;
- appel au service IA ;
- stockage des prédictions ;
- enregistrement des corrections humaines.

FastAPI est un service interne au réseau Docker.
Il décode les images, segmente les zones postales et réalise l'inférence avec les modèles Keras.

MongoDB Atlas stocke les prédictions et corrections via PyMongo.
Aucune base SQL n'est utilisée.
Les modèles sont des fichiers locaux du VPS montés en lecture seule dans le conteneur IA.

## Flux chiffre

```text
Canvas → PNG → Django → FastAPI IA → CNN
                                     ↓
Résultat front ← MongoDB ← Django ← Prédiction
```

Le dessin est exporté en PNG.
L'IA normalise le chiffre dans une image 28 × 28 compatible avec le CNN.
Django attribue un identifiant, conserve l'image et le résultat, puis répond au front.
Le résultat n'est annoncé comme enregistré qu'après insertion dans MongoDB.

## Flux postal

```text
Image recadrée → Django → FastAPI → Segmentation
                                     ↓
                                 Cinq chiffres
                                     ↓
                                 Modèle postal
                                     ↓
Front / vérification humaine ← Django + MongoDB ← Code postal
```

Les composantes sombres sont triées de gauche à droite.
Chaque chiffre est normalisé puis classé.
Les labels sont assemblés en une chaîne de cinq caractères pour préserver les zéros initiaux.
Le score postal est le minimum des cinq scores individuels.

Une segmentation inexploitable donne un résultat `unreadable`.
Une proposition complète est retournée avec `needs_review` :
aucune politique d'acceptation automatique n'est validée sur du courrier réel.
La correction est enregistrée séparément et ne remplace pas la prédiction initiale.

## Données

MNIST comprend 60 000 images train et 10 000 images test.
Le train est séparé en 50 000 exemples d'entraînement et 10 000 de validation,
avec stratification et graine 42.
Les données sont chargées depuis les collections `mnist_train` et `mnist_test`.
Le test final est réservé à l'évaluation après sélection du modèle.

Le corpus postal synthétique contient 360 images : 240 train, 60 validation et 60 test.
Il comprend des zones positives et des cas absents, illisibles ou ambigus.
Les annotations JSONL décrivent les images, les codes, les rectangles et les partitions.
Le validateur contrôle leur cohérence et les regroupements de provenance.

La collection `predictions` conserve l'image source, la valeur proposée, le score,
les versions du modèle, les dates et la correction éventuelle.
Seule l'empreinte du jeton de correction est stockée.
Les corrections expirées après 30 jours sont refusées ; la purge physique nécessite
un index TTL sur `expires_at` configuré dans MongoDB.
Les corrections ne servent pas automatiquement à un nouvel entraînement.

## Limites

- Le MVP accepte une zone postale déjà recadrée ; l'enveloppe complète n'est pas prise en charge.
- Le corpus postal actuel est synthétique et peu représentatif des écritures et prises de vue réelles.
- Le score du modèle n'est pas une certitude absolue ni une probabilité calibrée.
- Certains exemples négatifs produisent une proposition de code erronée.
- La présence d'un code dans un référentiel postal n'est pas vérifiée actuellement.

Les interfaces sont décrites dans [API](API.md), les mesures dans
[Résultats IA](MODEL_RESULTS.md) et l'installation dans [Déploiement](DEPLOYMENT.md).
