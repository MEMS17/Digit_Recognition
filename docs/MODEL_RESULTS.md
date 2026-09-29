# Résultats des baselines MNIST — validation uniquement

Exécution locale Docker du 29 septembre 2026. Ces résultats comparent trois premiers modèles, mais ne constituent pas encore l'évaluation finale : `mnist_test` n'a jamais été chargé par le script d'entraînement. Les modèles utilisent exactement le manifeste `mnist_train_val_v1` : 50 000 images pour l'entraînement et 10 000 pour la validation, réparties de façon stratifiée avec la graine 42.

## Prétraitement commun

Les 784 pixels uint8 sont lus depuis MongoDB, convertis en `float32`, puis normalisés par division par 255. Aucune augmentation, optimisation par grille ni donnée de test n'a été utilisée pendant cette baseline.

## Comparaison

| Modèle | Paramètres baseline | Accuracy validation | F1 macro | Entraînement CPU | Latence unitaire p50 / p95 CPU | Taille artefact |
|---|---|---:|---:|---:|---:|---:|
| SVM RBF | `C=10`, `gamma=scale` | **98,26 %** | 98,25 % | 223,8 s | **11,0 / 15,5 ms** | 67,0 Mo |
| Random Forest | 200 arbres, `max_features=sqrt` | 96,80 % | 96,79 % | **37,1 s** | 78,4 / 132,6 ms | 249,4 Mo |
| CNN | Conv32 → Pool → Conv64 → Pool → Dense128 → Dropout, 8 époques max | **98,87 %** | **98,86 %** | 173,2 s | 85,6 / 116,2 ms | **2,7 Mo** |

La latence est une mesure locale, CPU, batch 1, sur 100 appels successifs. Elle inclut le coût du framework : elle sert à comparer ce même environnement et non à annoncer une latence de production. Le CNN a atteint 98,87 % après huit époques ; l'arrêt anticipé n'a pas été déclenché avant la limite prévue.

## Premières erreurs observées

Les matrices de confusion complètes sont présentes dans l'artefact local `ia/models/mnist_baseline_v1/results.json`. Sur validation :

- Le SVM confond surtout `7 → 2` (10 cas) et `3 → 8` (9 cas).
- La Random Forest confond surtout `3 → 8` (17 cas), `3 → 2` (12 cas) et `7 → 2` (11 cas).
- Le CNN réduit ces confusions ; son erreur la plus fréquente est `8 → 1` (7 cas).

Ces exemples montrent que les écritures proches et certaines formes ambiguës restent difficiles. Ils ne permettent pas encore de conclure sur des dessins de canvas ou des codes postaux manuscrits : MNIST ne représente ni les images de courriers ni leur bruit ou leur mise en page.

## Décision provisoire

Le CNN est le candidat principal à optimiser grâce à sa meilleure accuracy et à son artefact très compact. Le SVM reste un candidat sérieux pour un déploiement CPU à faible latence. La Random Forest est conservée comme point de comparaison, mais n'est pas prioritaire pour l'optimisation à cause de sa performance inférieure, sa latence et sa taille.

Avant de sélectionner un modèle final : définir des espaces d'hyperparamètres, optimiser les candidats sur validation, geler le choix, puis évaluer une seule fois sur `mnist_test`. Les poids et résultats techniques sont volontairement ignorés par Git ; ils devront être archivés avec leurs empreintes lors de la livraison.

## Optimisation v1 et gel du candidat

L'optimisation a également été réalisée sans accès au test. Le SVM a utilisé un `GridSearchCV` à trois folds sur un sous-échantillon stratifié de 10 000 images du train, puis le meilleur réglage a été réentraîné sur les 50 000 images. Les CNN ont été comparés directement sur la validation externe.

| Candidat | Réglage | Accuracy validation | F1 macro | Observations |
|---|---|---:|---:|---|
| SVM optimisé | `C=3`, `gamma=scale` | 98,20 % | 98,19 % | meilleur score CV : 96,13 % ; inférieur à la baseline SVM sur validation |
| CNN A | `lr=0,001`, dropout `0,25` | **98,87 %** | **98,86 %** | meilleur candidat, identique à la baseline CNN |
| CNN B | `lr=0,0005`, dropout `0,15` | 98,80 % | 98,79 % | légèrement inférieur |
| CNN C | `lr=0,0005`, dropout `0,35` | 98,84 % | 98,83 % | légèrement inférieur |

Le candidat est donc gelé : **CNN A** (`learning_rate=0.001`, `dropout=0.25`, batch 128, huit époques effectivement exécutées lors de la baseline). Son artefact validé est `ia/models/mnist_tuning_v1/cnn_tuned.keras`. Les comparaisons suivantes ne modifieront plus ses hyperparamètres avant l'évaluation unique sur `mnist_test`.

L'optimisation n'a pas amélioré la baseline, ce qui est un résultat utile : elle confirme que le réglage initial est le meilleur parmi les options mesurées. Les artefacts locaux conservent le détail du GridSearch, les historiques CNN et les matrices de confusion.

## Évaluation finale sur MNIST test

Le 29 septembre 2026, le CNN gelé a été chargé sans nouvel entraînement et évalué une
fois sur les 10 000 images de `mnist_test`. Le script a vérifié les effectifs, les
identifiants et les dimensions avant l'inférence. L'artefact évalué a pour empreinte
SHA-256 `21f8caaedcfcc9787c314f5a516cb33317d2b821f7b6dde421f51aff860e68ec`.

| Modèle | Jeu | Accuracy | F1 macro | Erreurs | Latence p50 / p95 CPU |
|---|---:|---:|---:|---:|---:|
| CNN A gelé | 10 000 images test | **99,06 %** | **99,05 %** | 94 | 65,1 / 81,7 ms |

Les confusions les plus fréquentes sont `8 → 0` (10 cas), `9 → 7` (7 cas), puis
`6 → 0` et `4 → 9` (6 cas chacun). Ces résultats confirment le choix du CNN pour
la reconnaissance de chiffres MNIST. Ils ne mesurent toutefois ni la localisation
d'une zone postale, ni la segmentation de cinq chiffres, ni la robustesse aux
photos de courriers réels. Ces sujets nécessitent leur propre jeu de données annoté
et une évaluation de bout en bout.

Le détail reproductible — rapport par classe, matrice de confusion, paramètres,
latence et premiers exemples d'erreur — est conservé localement dans
`ia/models/mnist_final_evaluation_v1/results.json`. Cet artefact est ignoré par Git.
