# PASE — Nouveautés : comparer des politiques de pilotage

*Résumé des fonctionnalités ajoutées à PASE pour étudier l'impact du **pilotage de
l'inclinaison des panneaux** sur les rendements agricole et énergétique.*

---

## Le besoin

À l'origine, PASE simule **un** système agrivoltaïque avec du tracking classique.
Pour mon stage, il fallait pouvoir **tester et comparer plusieurs façons de piloter
les panneaux** (les suivre le soleil ? les mettre « en tranche » pour laisser la
lumière au sol ? un mélange selon la saison / l'heure ?) sur le **même parc**, la
**même année** et la **même météo**, afin de voir laquelle favorise le plus l'énergie,
la culture, ou un compromis.

## Ce qui a été ajouté

### 1. Un système de pilotage des panneaux
Trois modes possibles, combinables dans un simple fichier YAML :
- **tracking** : les panneaux suivent le soleil (maximise l'énergie) ;
- **anti-tracking** : panneaux « en tranche » face au soleil (maximise la lumière au
  sol → la culture) ;
- **fixe** : angle imposé.

Une **stratégie de pilotage** = un planning : on peut dire « anti-tracking d'avril à
mi-mai, tracking de 11 h à 14 h l'été, tracking le reste de l'année », etc. Chaque
stratégie est un fichier dans `INPUTS/PILOTAGE/`.

### 2. Un lanceur de comparaison unique
Un seul script, `run_comparaison_pilotage.py` : on y liste les stratégies à comparer,
on lance, et **tout est calculé et rangé automatiquement** dans un dossier daté et
numéroté `OUTPUTS/COMPARAISONS_PILOTAGE/SIMU_<N>_.../`.

### 3. Des résultats visuels et documentés
Pour chaque comparaison, on obtient :

| Sortie | À quoi ça sert |
|---|---|
| **Graphes de comparaison** | Superposition des courbes énergie & biomasse, barres de totaux, et un **classement** (quelle stratégie est la meilleure en énergie / en biomasse, et l'arbitrage entre les deux) |
| **Graphes par stratégie** | Énergie et biomasse cumulées, avec le **fond coloré selon le mode actif** (on voit quand le pilotage freine la production) |
| **Images 3D** | Vue du parc + **carte de répartition de la biomasse au sol** (effet d'ombrage) |
| **Traces de vérification** | Inclinaison des panneaux heure par heure vs position du soleil (pour vérifier ce que fait l'algorithme) |
| **Fiche des inputs** (`.md` + `.pdf`) | Toutes les caractéristiques du parc et des stratégies, pour garder une trace |
| **Fiche d'avis** + **fiche de performance** | Pour noter ses observations et suivre les temps de calcul |

### 4. Des calculs beaucoup plus rapides
Les stratégies étant indépendantes, elles sont calculées **en parallèle** sur les
cœurs du processeur. Gain mesuré : **~77 s → ~16 s** pour 4 stratégies (≈ 5× plus
rapide), ce qui permet d'envisager des parcs plus grands et une meilleure précision.

## Comment on l'utilise

1. Écrire (ou réutiliser) les stratégies voulues dans `INPUTS/PILOTAGE/*.yaml`.
2. Les lister en tête de `run_comparaison_pilotage.py` (+ choix du parc, de l'année…).
3. Lancer le script → un dossier `SIMU_<N>` complet est généré, prêt à analyser.

## Ce que ça permet de conclure

En un run, on visualise directement le **compromis énergie / agriculture** de chaque
politique de pilotage : typiquement, l'anti-tracking sacrifie beaucoup d'énergie pour
gagner un peu de biomasse, le tracking fait l'inverse, et les **stratégies mixtes**
(saison/heure) permettent de chercher le meilleur équilibre selon l'objectif visé.
