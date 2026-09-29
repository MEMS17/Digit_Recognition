# Périmètre de lecture des courriers

Statut : spécification pour les prochaines étapes ; aucune fonction de lecture ni politique de purge n'est implémentée par ce document. A = toi avec Codex (back et IA). B = collaborateur (front et déploiement).

## Objectif et limites

Identifier le code postal du destinataire sur le recto d'un courrier, puis proposer sa lecture ou demander une vérification humaine. La cible est un code français de cinq chiffres ASCII, représenté partout par une chaîne : le format attendu est `^[0-9]{5}$`. Ne jamais convertir cette valeur en entier. Une chaîne conforme au format ne prouve ni l'existence du code dans un référentiel ni l'exactitude de la lecture.

Le périmètre initial couvre des courriers fictifs ou dont l'utilisation est autorisée, avec un code manuscrit lisible. La reconnaissance du nom, de la rue ou de l'adresse complète, les codes internationaux, le routage effectif du courrier et l'intégration aux systèmes de La Poste sont hors périmètre. La lecture automatique de courriers sans restriction de mise en page n'est pas promise : chaque résultat sera accompagné du périmètre réellement évalué.

Le code expéditeur ne doit pas être choisi à la place du code destinataire. Si les deux zones sont candidates et ne peuvent pas être distinguées de manière fiable, l'application demande une sélection humaine. Une zone absente, un nombre de chiffres différent de cinq ou une image illisible ne doit pas produire de code artificiellement complété.

## Progression et conditions de passage

| Jalon | Entrée et fonctionnement | Condition de passage |
|---|---|---|
| 1 — chiffre obligatoire | Dessin d'un chiffre dans le canvas, prétraitement commun et prédiction | Parcours demandé par le sujet livré, trois modèles comparés, résultats et erreurs documentés |
| 2 — cinq cases | Cinq dessins traités individuellement et assemblés de gauche à droite | Cinq cases renseignées, conservation des zéros, correction possible, évaluation du code entier |
| 3 — zone recadrée (`crop`) | Image contenant un seul code ; segmentation puis reconnaissance, ou lecture de séquence si justifiée | Jeu postal distinct annoté, exactitude du code entier mesurée, refus et erreurs documentés |
| 4 — enveloppe (`envelope`) | Image du recto ; localisation du code destinataire puis lecture | Localisation et lecture évaluées séparément et ensemble ; absence, ambiguïté et révision prises en charge |

Le passage à l'enveloppe dépend d'une lecture de zone déjà évaluée. La décision segmentation/lecture de séquence repose sur les échecs observés et les données disponibles, pas sur une obligation d'utiliser une architecture plus complexe. Le protocole d'évaluation commun fixe les métriques et les seuils ; un succès sur quelques exemples de démonstration ne valide pas un jalon.

## Entrées image et coordonnées

Pour `crop` et `envelope`, accepter une seule image JPEG ou PNG, au maximum **5 MiB (5 242 880 octets)** et **12 millions de pixels décodés** (`largeur × hauteur`). Vérifier le contenu décodé, pas seulement l'extension ou le type annoncé. Les PDF, HEIC, images animées et documents multipages sont hors périmètre. Les mêmes limites doivent être annoncées dans le front et appliquées par le back ; un dépassement doit être rejeté avant l'inférence.

La chaîne applique d'abord l'orientation EXIF. Le back valide les dimensions orientées ; l'IA effectue la normalisation effective une seule fois sur les octets transmis. L'image de référence est alors l'image complète, orientée correctement, avant tout redimensionnement de travail. Les dimensions de référence et le rectangle de localisation utilisent cette image. Le front affiche cette même orientation. Chaque dimension est aussi limitée à 12 000 pixels, conformément à l'API.

Un rectangle est décrit par `x`, `y`, `width`, `height` en **pixels entiers**, origine en haut à gauche, dans cette image de référence. « Normalisée » désigne ici l'orientation, pas des coordonnées entre 0 et 1. Les bornes doivent respecter `x >= 0`, `y >= 0`, `width > 0`, `height > 0`, `x + width <= image_width` et `y + height <= image_height`. Les sorties d'un détecteur travaillant sur une image réduite doivent être reprojetées dans ce repère avant exposition par l'API.

En mode `crop`, l'image importée est elle-même la référence ; son rectangle complet représente la zone fournie, sans prétendre connaître sa position dans une enveloppe d'origine. En mode `envelope`, le rectangle indique la zone localisée dans le recto complet. Si l'utilisateur sélectionne une zone manuellement, la même convention s'applique. Un aperçu réduit doit convertir ses coordonnées d'affichage vers ce repère. Pour la v1, le front exporte la sélection en nouvelle image et l'envoie avec `input_kind=crop` : il s'agit d'une nouvelle prédiction, pas d'une modification du rectangle serveur. Aucun paramètre de sélection de zone n'est accepté par l'API v1.

Le parcours cinq cases appelle cinq fois la route chiffre et assemble les valeurs côté front, seulement lorsque chaque valeur est disponible. Les corrections restent associées à chaque prédiction de chiffre et à son jeton. Ce parcours ne crée pas de document de code postal agrégé ; la route `postal-code` sert aux images de codes complets.

## Corpus et annotations

Commencer par des enveloppes fictives avec plusieurs écritures et dispositions. Ajouter progressivement rotations, ombres, bruit, tailles de chiffres, chiffres rapprochés ou collés, code absent et deux blocs d'adresse. Réserver un jeu de test avant les ajustements ; ne pas inventer de volume minimal garantissant la performance. Publier les effectifs obtenus et les limites de couverture.

Pour chaque image, conserver dans un manifeste de corpus :

- Un identifiant stable, une référence de fichier, son empreinte, ses dimensions après orientation et son mode (`crop` ou `envelope`).
- La transcription humaine du code destinataire sous forme de chaîne, ou une annotation explicite d'absence/illisibilité/ambiguïté ; ne pas fabriquer de transcription dans ces cas.
- Le rectangle du code destinataire dans le repère ci-dessus et, lorsqu'ils existent, les rectangles candidats avec leur rôle destinataire/expéditeur/inconnu.
- Des identifiants pseudonymes de scripteur, d'enveloppe source et de modèle de mise en page, ainsi que le groupe de provenance.
- La provenance synthétique/autorisée, les conditions d'utilisation, la version d'annotation et son état de vérification.
- Le split affecté (`train`, `validation`, `test`) et les relations entre original, recadrages et augmentations.

Un original, ses recadrages et ses augmentations restent dans le même split. Les scripteurs, enveloppes et familles de modèles de mise en page doivent être groupés afin d'éviter leur présence de part et d'autre des splits ; si les contraintes empêchent une séparation indépendante, le signaler et compléter le corpus. Affecter les splits avant les augmentations. Ne pas utiliser le test pour régler la localisation, les seuils ou le prétraitement.

Les images, manifests contenant des données utilisateur et modèles volumineux restent dans des volumes Docker ou un stockage de données non suivi par Git. Git contient les scripts et les conventions, pas des adresses réelles, des secrets ou des justificatifs d'autorisation. Les chemins et empreintes permettent de retrouver les données sans les copier dans les rapports.

## Vérification humaine et conservation

Une sortie doit distinguer code proposé, état de révision, motifs d'incertitude et correction humaine. Aucun remplacement silencieux par un code du référentiel n'est autorisé. Un score modèle reste un score tant que sa calibration n'a pas été validée.

Une correction saisie par un utilisateur n'est pas automatiquement une étiquette fiable pour l'entraînement. Une sélection et une vérification d'annotation séparées seront nécessaires avant toute incorporation à un corpus ; la version initiale ne s'entraîne pas en continu sur les corrections.

Choix de conception : conserver les images de prédiction et leurs données associées **30 jours à compter de la création**, par défaut, puis les purger. La durée sera configurable au déploiement. Cette décision est un objectif à implémenter et à vérifier, pas une garantie actuelle. La purge doit supprimer les fichiers associés et les documents ; un index d'expiration MongoDB seul ne suffit pas pour un stockage de fichiers séparé. Les journaux ne doivent pas contenir les images ou les adresses. Le corpus de recherche autorisé suit une politique distincte, documentée avec sa provenance.

## Scénarios d'acceptation à implémenter

| Scénario | Comportement attendu |
|---|---|
| Cinq cases contenant `0`, `1`, `2`, `3`, `4` | Assemblage exact en `"01234"` ; exemple synthétique de format seulement, sans affirmer que ce code existe |
| Case vide ou dessin illisible | Demande de compléter/corriger ; aucune substitution automatique par zéro |
| Zone avec cinq chiffres lisibles | Code proposé, possibilité de correction et état de révision conformes au contrat |
| Zone à quatre ou six chiffres | Révision demandée ; aucun ajout ou retrait silencieux de chiffre |
| Enveloppe avec code destinataire et code expéditeur | Bonne zone sélectionnée si identifiable ; sinon sélection humaine, sans certitude inventée |
| Aucun code présent | État d'absence exploitable dans le front, sans fausse lecture |
| JPEG avec orientation EXIF | Aperçu orienté et rectangle superposé sur la même zone avant/après réduction d'affichage |
| PNG/JPEG valide à la limite puis au-delà de chaque limite | Entrée à la limite admise ; dépassement rejeté sans inférence |
| PDF, HEIC, animation ou faux JPEG | Erreur explicite de format, sans tentative de lecture du code |
| Code conforme mais absent du référentiel | Signal distinct du contrôle de format ; aucune correction silencieuse |
| Correction humaine | Valeur d'origine conservée distinctement, correction tracée, aucune admission automatique dans l'entraînement |
| Donnée expirée | Une fois la purge implémentée : document et fichier supprimés, référence non accessible |

## Ordre de réalisation et répartition

Ces actions détaillent les cartes existantes de [TRELLO.md](TRELLO.md) ; elles ne créent pas une seconde liste de tâches concurrente.

| Priorité | Responsable | Action | Cartes liées |
|---|---|---|---|
| P0 | A | Formaliser les entrées, les états de révision, le repère image et les métriques | 02, 04, 05 |
| P0 | B | Reprendre ces limites et états dans les maquettes | 09 |
| P1 | A | Livrer le parcours chiffre, comparer les modèles et constituer le corpus postal annoté | 06–08, 11–15, 18, 20 |
| P1 | B | Livrer le canvas, l'intégration API et les cinq cases | 16, 17, 21 |
| P2 | A | Évaluer la zone recadrée, puis la localisation destinataire et la chaîne complète | 22–25, 28–30 |
| P2 | B | Livrer l'import, l'aperçu orienté, la sélection et la correction manuelles | 26, 27, 31 |
| P2 | A | Implémenter limites, conservation et purge ; documenter les résultats et limites | 32, 34 |
| P2 | B | Déployer avec volumes persistants, configuration de durée et vérification de la purge | 19, 33, 35 |

Chaque étape de réalisation reste soumise au rythme convenu avec l'utilisateur. Ce cadrage ne lance ni import, ni entraînement, ni implémentation d'API.
