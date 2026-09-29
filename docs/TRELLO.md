# Plan Trello — lecture de codes postaux

Responsables : **A = toi avec Codex (back + IA)** ; **B = collaborateur (front + déploiement)**. Chaque ligne représente une carte. Les priorités sont ordonnées P0 → P1 → P2 → P3 ; suivre les dépendances avant de commencer. Le socle est initialisé et le cadrage technique est rédigé ; les fonctionnalités restent à implémenter.

## Point d'avancement du cadrage

- Carte 01 : initialisation réalisée et vérifiée dans Docker.
- Carte 02 : périmètre et objectifs provisoires rédigés dans [POSTAL_SCOPE.md](POSTAL_SCOPE.md) et [EVALUATION.md](EVALUATION.md) ; aucune performance mesurée.
- Carte 04 : [contrat API v1](API.md) prêt pour le développement et la relecture du collaborateur ; pas d'intégration réalisée.
- Carte 05 : [schéma et procédure Atlas](MONGODB.md) documentés ; les collections MNIST et leurs index existent localement. Atlas et la collection `predictions` restent à configurer avec le back.
- Carte 06 : import MNIST validé localement : 60 000 documents train, 10 000 documents test, pixels 28 × 28 et reprise sans doublon vérifiés. Les données vivent dans le volume Docker local et ne sont pas versionnées.
- Carte 07 : notebook d'exploration exécuté depuis MongoDB : image avec label, chiffres 0 à 9, neuf écritures de 7 et représentants moyens produits dans `ia/notebooks/01_exploration_mnist.ipynb`.
- Carte 08 : manifeste `mnist_train_val_v1` créé dans MongoDB : 50 000 entraînement, 10 000 validation, stratification par label et graine 42. Le test reste séparé.
- Carte 11 : SVM RBF, Random Forest et CNN entraînés depuis MongoDB sur le même split. Les résultats de validation sont consignés dans [MODEL_RESULTS.md](MODEL_RESULTS.md) ; `mnist_test` reste intact.
- Carte 12 : optimisation SVM par GridSearchCV et comparaison de trois réglages CNN terminées sur validation. Le CNN avec `lr=0.001` et dropout `0.25` est gelé ; `mnist_test` reste intact.
- Prochaine réalisation proposée : carte 13, sérialiser le candidat gelé avec ses métadonnées de prétraitement, puis carte 14 pour son intégration dans l'API chiffre. L'évaluation finale sur `mnist_test` interviendra après ce gel, sans modification des réglages.

Listes suggérées : À faire, Prêt, En cours, À relire, Terminé. Étiquettes : Back, IA, Front, Données, Déploiement, Documentation. Ajouter à chaque carte le responsable, la priorité, la dépendance et le critère d'acceptation ci-dessous.

| ID | Priorité | Qui | Tâche | Dépendances | Critère de fin |
|---|---|---|---|---|---|
| 01 | P0 | A | Initialiser front/back/ia et Docker | — | Socle séparé, commandes et limites documentées |
| 02 | P0 | A | Formaliser le périmètre et les métriques | 01 | Dessin un chiffre + lecture courrier ; critères quantifiés convenus |
| 03 | P0 | B | Créer Trello et organiser les branches | 01 | Cartes assignées, conventions et revues documentées |
| 04 | P0 | A | Définir le contrat API avec B | 02 | Requêtes, réponses, erreurs et états de révision validés |
| 05 | P0 | A | Définir schéma MongoDB et configuration Atlas | 02 | Trois collections minimales, index et accès documentés |
| 06 | P0 | A | Importer MNIST dans MongoDB | 05 | Import relançable, comptes/labels/dimensions contrôlés |
| 07 | P0 | A | Explorer MNIST dans le notebook | 06 | Chiffres 0–9, neuf 7, images moyennes et anomalies présentés |
| 08 | P0 | A | Définir splits et prétraitement partagé | 07 | Validation issue du train, test réservé, transformations reproductibles |
| 09 | P0 | B | Concevoir les écrans | 02,04 | Dessin, import courrier, chargement, erreur et correction maquettés |
| 10 | P0 | B | Installer une CI de validation | 01 | Build front et contrôles back/IA exécutables sans secrets |
| 11 | P1 | A | Entraîner une baseline puis trois modèles | 08 | Comparaison SVM, Random Forest et CNN, ou alternative motivée |
| 12 | P1 | A | Optimiser et sélectionner le modèle | 11 | Recherche d'hyperparamètres, accuracy, confusion, latence et coût comparés |
| 13 | P1 | A | Exporter modèle et contrat d'inférence | 12 | Artefact versionné, métadonnées et prétraitement cohérent |
| 14 | P1 | A | Implémenter validation d'image et API chiffre | 04,13 | Image valide prédite ; entrée vide/invalide/trop grande rejetée |
| 15 | P1 | A | Persister images et résultats | 05,14 | Prédiction, version modèle et correction distinguées |
| 16 | P1 | B | Développer le canvas chiffre | 09,04 | Dessin, effacement, envoi et affichage utilisables |
| 17 | P1 | B | Brancher le front sur l'API chiffre | 14,16 | Parcours réel avec gestion des erreurs |
| 18 | P1 | A | Évaluer des dessins hors MNIST | 17 | Jeu étiqueté du groupe, erreurs et limites analysées |
| 19 | P1 | B | Préparer le déploiement de préproduction | 10,17 | Images de production, HTTPS, secrets et Atlas configurés |
| 20 | P1 | A | Constituer un corpus postal annoté | 02,08 | Codes complets, rectangles de localisation, provenance et splits documentés |
| 21 | P1 | B | Ajouter le parcours cinq cases | 17 | Cinq chiffres assemblés en chaîne, zéros initiaux conservés |
| 22 | P2 | A | Lire une zone postale déjà recadrée | 13,20 | Segmentation et reconnaissance évaluées sur codes complets |
| 23 | P2 | A | Traiter bruit, rotation et chiffres collés | 22 | Échecs mesurés, stratégie segmentation/séquence justifiée |
| 24 | P2 | A | Localiser le code sur l'enveloppe | 20,22 | Zone détectée sur jeu séparé ; absence/ambiguïté gérées |
| 25 | P2 | A | Intégrer la chaîne courrier dans l'API | 23,24,04 | Upload → localisation → code, avec résultats intermédiaires exploitables |
| 26 | P2 | B | Développer l'import et l'aperçu courrier | 09,04 | Sélection, aperçu et limites de fichier expliquées |
| 27 | P2 | B | Afficher zone détectée et correction | 25,26 | Code lisible, rectangle et validation/correction manuelle |
| 28 | P2 | A | Ajouter le contrôle du code postal | 25 | Format cinq chiffres et référentiel versionné, sans correction silencieuse |
| 29 | P2 | A | Définir la politique d'incertitude | 25,28 | Seuils validés ; erreurs acceptées et taux de révision mesurés |
| 30 | P2 | A | Évaluer la chaîne complète | 27,29 | Taux de codes exacts, latence, erreurs de localisation et lecture publiés |
| 31 | P2 | B | Tester les parcours et l'accessibilité | 27 | Mobile, clavier, erreurs, réseau indisponible et fichiers invalides vérifiés |
| 32 | P2 | A | Durcir l'API et la conservation | 25 | Limites, décodage sûr, logs sans adresse et suppression des données prévus |
| 33 | P2 | B | Déployer la version finale | 19,30,31,32 | URL fonctionnelle, redémarrage et supervision vérifiés |
| 34 | P2 | A | Finaliser notebook et rapport d'évaluation | 30 | Démarche, bonnes/mauvaises prédictions et limites conservées |
| 35 | P2 | B | Finaliser README et guide de lancement | 33 | Installation testée, liens Trello, application et présentation |
| 36 | P2 | A | Préparer les slides IA et métier | 34 | Problème postal, données, comparaison et limites expliqués |
| 37 | P2 | B | Préparer slides architecture et démo | 33,35,36 | Environ dix slides au total et scénario de secours |
| 38 | P2 | A | Répéter la soutenance avec B | 37 | 5 min contexte, 15 min approche/démo, préparation aux questions |
| 39 | P3 | A | Étudier la lecture directe de séquences | 30 | Seulement si nécessaire : gain mesuré face à la segmentation |
| 40 | P3 | B | Améliorer l'aide au cadrage photo | 30,31 | Conseils basés sur les échecs observés |

## Jalons

1. Socle initialisé → accord utilisateur avant toute suite.
2. Cahier des charges minimum livré : MNIST, trois modèles, dessin, Atlas, API et déploiement.
3. Codes complets lus dans une zone recadrée.
4. Courriers lus de bout en bout sur le périmètre évalué, avec vérification humaine.
5. Livraison et soutenance.

La lecture de tous les courriers sans contrainte n'est pas une promesse : cadrer types d'enveloppes, qualité photo et écritures couvertes, puis mesurer les résultats.
