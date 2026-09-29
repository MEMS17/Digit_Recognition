# Protocole d’évaluation IA et courrier

Statut : spécification de la prochaine réalisation, sans modèle entraîné ni résultat mesuré. Responsable : A (toi avec Codex). B fournit les parcours front et l’environnement de déploiement nécessaires aux mesures de bout en bout. Les objectifs ci-dessous sont provisoires et devront être confirmés sur des données représentatives.

## 1. Jeux de données et séparation

### MNIST

L’import vérifiera la source et sa version, ses empreintes, les labels 0 à 9, les dimensions 28 × 28 et les effectifs attendus : 60 000 exemples d’entraînement et 10 000 exemples de test. La [source officielle MNIST](https://yann.lecun.org/exdb/mnist/index.html) décrit cette répartition ; ce sont des contrôles attendus, pas des comptes constatés dans MongoDB.

L’entraînement et l’évaluation chargent les données depuis `mnist_train` et `mnist_test` dans MongoDB, jamais directement depuis le CSV. L’import du CSV appartient à une étape distincte.

- Construire dans `mnist_train` une séparation stratifiée par label : 50 000 entraînement et 10 000 validation, graine 42.
- Sauvegarder les identifiants de chaque partition dans un manifeste versionné et réutiliser exactement les mêmes partitions pour les trois modèles.
- Ajuster les transformations apprises uniquement sur l’entraînement. Réserver les augmentations à cette partition.
- Choisir modèles, hyperparamètres et seuils avec entraînement/validation. Le test reste inaccessible au réglage et n’est ouvert qu’après gel des choix.
- Vérifier les doublons et documenter les anomalies avant gel. Une modification des partitions crée une nouvelle version du protocole ; ne pas déplacer silencieusement des exemples pour améliorer un résultat.

Après consultation du test, toute nouvelle optimisation devra être présentée comme telle et nécessitera un nouveau jeu indépendant pour une nouvelle estimation finale. Les corrections utilisateurs ne deviennent des labels qu’après vérification humaine ; elles ne réintègrent jamais automatiquement le test.

### Corpus postal distinct

Préparer des courriers fictifs ou autorisés avec code postal français de cinq chiffres. Annoter la chaîne exacte (zéros initiaux conservés), le rectangle de la zone destinataire contenant le code et les conditions d’acquisition. Identifier également les cas sans code lisible ou ambigus. Une adresse expéditeur éventuelle ne doit pas être prise pour la destination.

Pilote proposé, à constituer : au moins 300 images couvrant au moins 10 scripteurs. Il sert à détecter les difficultés et à vérifier la chaîne ; il ne suffit pas à démontrer une faible erreur d’acceptation. Augmenter le corpus si les intervalles d’incertitude restent trop larges, particulièrement le nombre de scripteurs et de modèles d’enveloppes indépendants.

Viser 60 % entraînement, 20 % validation et 20 % test, par groupes indépendants, avec effectifs approximatifs lorsque les groupes sont indivisibles. Former les groupes comme les composantes reliant un même scripteur, une même enveloppe ou un même modèle de mise en page synthétique : aucun de ces éléments ne traverse les partitions. Répartir les groupes avant génération des variantes. Si toutes les images partagent un seul modèle de mise en page, créer de nouveaux modèles indépendants avant de prétendre mesurer la généralisation à des enveloppes inédites.

Les photos, recadrages et augmentations d’un même original restent ensemble. Les images synthétiques issues d’un même fond, patron, fonte manuscrite ou original restent dans le même groupe ; conserver aussi leur provenance et graine de génération. Rapporter séparément les résultats sur photos réelles et images synthétiques. Le test final inclut des photos inédites, pas uniquement du synthétique.

Les crops de référence et enveloppes complètes partagent les mêmes partitions. Un crop issu d’une enveloppe de test ne sert jamais à entraîner la reconnaissance. Contrôler les doublons exacts et visuels avant gel. Séparer également un petit corpus de dessins du canvas, étiqueté humainement, pour évaluer l’écart avec MNIST.

## 2. Comparaison des modèles et prétraitement

Comparer SVM, Random Forest et CNN sur les mêmes partitions. Le CNN est une option d’implémentation future ; TensorFlow n’est pas installé par cette spécification. Si les ressources imposent un sous-échantillon exploratoire, le fixer et le signaler ; ne pas présenter cette expérience comme une comparaison sur l’entraînement complet.

Définir avant les expériences les espaces d’hyperparamètres et budgets de recherche : noyau/C/gamma pour SVM, nombre d’arbres/profondeur/contraintes de feuilles pour Random Forest, architecture/taux d’apprentissage/batch/régularisation pour CNN. L’arrêt anticipé du CNN consulte uniquement la validation. Conserver les essais, y compris les échecs, leur durée et leurs paramètres. Choisir selon performance de validation, latence CPU et taille de l’artefact ; justifier le compromis final.

Le prétraitement partagé entraînement/inférence est versionné : décodage, niveaux de gris, polarité, recadrage utile, proportions conservées, centrage dans 28 × 28, normalisation et ordre des dimensions. Les adaptations entre MNIST et images reçues sont explicites. Les variantes de prétraitement sont des hyperparamètres sélectionnés sur validation. Les entrées vides restent des échecs contrôlés, sans chiffre inventé.

Évaluer par étapes : chiffre isolé, code dans une zone de référence recadrée, localisation seule, puis chaîne sur l’enveloppe entière. Cela permet de distinguer erreurs de localisation, segmentation, classification et contrôle métier. Un référentiel postal peut signaler une incohérence ; il ne valide pas la lecture et ne doit pas corriger silencieusement la prédiction.

## 3. Mesures et dénominateurs

| Mesure | Définition à publier |
|---|---|
| Accuracy chiffre | Chiffres corrects / totalité des exemples du jeu concerné ; compléter par précision, rappel, F1 par classe et matrice de confusion |
| Code exact sur crop | Chaînes de cinq chiffres exactement correctes / tous les crops de référence éligibles, y compris échecs et abstentions |
| Localisation | IoU = aire d’intersection / aire d’union avec la zone annotée ; absence de détection sur une cible présente vaut 0. Rapporter IoU moyen et rappel à IoU ≥ 0,5, seuil fixé avant test |
| Faux positifs de localisation | Images négatives sur lesquelles une zone postale est détectée / toutes les images négatives ; rapport distinct pour courriers ambigus |
| Code exact de bout en bout | Codes exactement corrects / toutes les enveloppes de test avec code cible annoté, avant correction humaine ; erreurs API, absence de zone, segmentation ratée, timeout et abstention comptent comme échecs |
| Couverture automatique | Courriers acceptés automatiquement / tous les courriers éligibles soumis, y compris cas négatifs et ambigus |
| Taux d’erreur parmi les acceptés | Courriers acceptés à tort / courriers acceptés automatiquement ; un cas sans code accepté est une erreur. Si aucun accepté : non calculable, jamais 0 % |
| Révision humaine | Courriers orientés vers vérification / tous les courriers éligibles soumis ; publier à part les erreurs techniques et rejets, car ils empêchent parfois couverture + révision = 100 % |
| Latence | p50 et p95 par étape IA et API complète, y compris traitements échoués/timeouts avec leur nombre ; durée cold-start distincte |

Publier numérateurs et dénominateurs, pas seulement les pourcentages. Les fichiers hors contrat (format interdit, fichier corrompu, taille excessive) constituent un jeu de robustesse séparé avec vérification des rejets. Fixer les critères d’éligibilité avant le test, sans retirer a posteriori les images difficiles.

Conserver les scores bruts et sorties avant contrôle métier, puis les décisions finales. Un score SVM, une probabilité de forêt ou une sortie softmax CNN n’est pas automatiquement une probabilité calibrée. Toute calibration utilise exclusivement des données dédiées issues de l’entraînement/validation ; seuils et calibration sont gelés avant test. Rapporter la courbe couverture/erreur sur validation puis le point de fonctionnement gelé sur test. Ne pas afficher un « pourcentage de certitude » sans validation correspondante. Le score API peut être nul. Évaluer les états `recognized`, `needs_review` et `unreadable` en accord avec le contrat API. Aucun des trois modèles ne sait rejeter par défaut toutes les entrées hors distribution : inclure blanc, bruit, lettres et zones sans code dans les jeux négatifs, et mesurer les acceptations à tort.

## 4. Objectifs provisoires et décision d’acceptation

| Parcours | Objectif initial, encore non vérifié |
|---|---|
| MNIST test | Accuracy ≥ 98 % |
| Code postal recadré | Codes exacts ≥ 90 % sur test postal indépendant |
| Enveloppe complète | Codes exacts ≥ 85 % sur test postal indépendant |
| Acceptation automatique | Erreur parmi les acceptés ≤ 1 %, uniquement si soutenue par une borne statistique suffisante |
| Latence CPU | Objectif exploratoire p95 ≤ 2 s par enveloppe, hors téléversement réseau ; à confirmer après mesure du premier modèle |

Pour les performances, publier des intervalles à 95 % et leur méthode. Rééchantillonner les groupes indépendants du corpus postal pour refléter les corrélations entre images ; si le nombre de groupes est trop faible, indiquer explicitement que l’estimation est fragile et enrichir le corpus.

Pour activer l’acceptation automatique, exiger une borne supérieure unilatérale à 95 % de l’erreur parmi les acceptés ≤ 1 %, avec méthode justifiée au regard des dépendances entre exemples. Zéro erreur dans un petit lot ne démontre pas ce niveau de sûreté. Une formule binomiale supposant des essais indépendants ne doit pas masquer des images répétées du même scripteur ou de la même enveloppe. En l’absence d’éléments suffisants, la vérification humaine reste le fonctionnement par défaut, même si le score du modèle est élevé. Ces seuils sont des objectifs de projet, pas une certification pour un tri postal réel.

## 5. Reproductibilité et rapport final

Exécuter dans Docker et enregistrer : version/image Docker, dépendances verrouillées, système, processeur, RAM, limites de ressources et nombre de threads. La référence de latence est CPU, batch 1, concurrence 1 ; effectuer un échauffement documenté puis plusieurs passages, avec nombre de requêtes et distribution des tailles d’images. Publier séparément le temps API avec lecture/persistance MongoDB et le temps IA seul ; préciser si la base est locale ou Atlas et mesurer le réseau front séparément.

Chaque expérience sauvegarde identifiant, graine (42 par défaut), manifeste des données, paramètres, prétraitement, versions des bibliothèques, empreinte du modèle, métriques et durée. Documenter les opérations non déterministes. Les artefacts lourds restent hors Git ; enregistrer leur emplacement et empreinte, sans secret.

Le rapport final comprend : tableau des trois modèles, choix argumenté, matrices de confusion, exemples réussis et ratés, résultats MNIST/canvas/crops/enveloppes séparés, effectifs, intervalles, latences, seuil de révision et limites du corpus. Distinguer les résultats avant et après intervention humaine. Aucun gain de productivité pour La Poste ne sera affirmé sans mesure du processus concerné.
