# Guide de prise en main — Comparer des stratégies de pilotage agrivoltaïque

Marche à suivre informatique pour installer et utiliser
`run_comparaison_pilotage.py`, ajouté à PASE 2.0 pour comparer des stratégies de
pilotage de l'inclinaison des panneaux. Ce document ne traite que de l'outil : ni
modèle, ni interprétation des résultats.

**Auteur** : Hugo Lange — stage 2026, G2ELab

**Code** : https://github.com/hugolangepro/pase-pilotage

---

## 1. Ce que fait le programme

Une exécution lance **une simulation PASE complète par stratégie**, sur des inputs
strictement identiques (même parc, même année, même météo), puis agrège le tout en
une comparaison énergie / culture.

Quatre stratégies sont fournies par défaut :

| Stratégie | Définition |
|---|---|
| `tracking_pur` | Suivi du soleil toute l'année, avec correction de backtracking. Référence. |
| `antitrack_pur` | Plan des panneaux contenant le rayon solaire toute l'année — captation directe nulle. Sans backtracking. |
| `antitrack_printemps` | Tracking, sauf anti-tracking du 01/04 au 15/05. |
| `antitrack_printemps_et_track_midi_ete` | Idem, plus tracking de 11 h à 14 h du 01/06 au 31/08 et anti-tracking le reste de la journée. |

Elles sont définies dans `INPUTS/PILOTAGE/` et entièrement redéfinissables
(section 5.4). Un troisième mode, `fixed` (angle imposé), est également
disponible.

---

## 2. Ce qu'il faut installer (une seule fois)

Il y a **deux choses** à installer : un « moteur » Python, puis le code lui-même.

### 2.1 Installer Miniforge (le moteur Python)

Miniforge est un logiciel gratuit qui gère Python et toutes les bibliothèques
scientifiques nécessaires.

1. Aller sur **https://conda-forge.org/download/**
2. Télécharger la version correspondant à votre ordinateur :
   - **Windows** → le fichier qui se termine par `Windows-x86_64.exe`
   - **Mac récent (puce M1/M2/M3/M4)** → `MacOSX-arm64.sh`
   - **Mac ancien (puce Intel)** → `MacOSX-x86_64.sh`
3. **Sur Windows** : double-cliquer sur le fichier téléchargé et suivre
   l'installation en laissant toutes les options par défaut.
   **Sur Mac** : ouvrir l'application **Terminal** (⌘ + espace, taper
   « Terminal », Entrée), puis copier-coller cette ligne et appuyer sur Entrée :
   ```
   bash ~/Downloads/Miniforge3-MacOSX-arm64.sh
   ```
   Répondre `yes` à toutes les questions. **Fermer puis rouvrir le Terminal** à la fin.

> **Comment savoir si ça a marché ?** Ouvrez le Terminal (Mac) ou
> **« Miniforge Prompt »** depuis le menu Démarrer (Windows), tapez `conda --version`
> et appuyez sur Entrée. Si une version s'affiche (par exemple `conda 24.9.2`),
> c'est bon.

### 2.2 Récupérer le code

**Option A — la plus simple (sans logiciel supplémentaire)**

1. Aller sur https://github.com/hugolangepro/pase-pilotage
2. Cliquer sur le bouton vert **`< > Code`**, puis **`Download ZIP`**.
3. Ouvrir le fichier téléchargé pour le décompresser, et **déplacer le dossier
   obtenu sur le Bureau**. Il s'appellera `pase-pilotage-main`.
   Renommez-le simplement **`pase-pilotage`** pour la suite.

**Option B — avec GitHub Desktop** (si vous voulez pouvoir récupérer les mises à
jour facilement) : installer https://desktop.github.com, puis
`File > Clone repository > URL` et coller l'adresse du dépôt.

> ⚠️ Si vous utilisez GitHub Desktop, **n'utilisez jamais le bouton
> « Discard changes »** : il efface définitivement les fichiers de résultats.

### 2.3 Installer les bibliothèques scientifiques

Cette étape télécharge tout ce dont le programme a besoin. Elle prend
**15 à 30 minutes** et ne se fait qu'une fois.

Ouvrez le **Terminal** (Mac) ou le **Miniforge Prompt** (Windows), puis tapez les
commandes suivantes **une par une**, en appuyant sur Entrée après chacune.

**1) Se placer dans le dossier du code :**

Sur Mac :
```
cd ~/Desktop/pase-pilotage
```
Sur Windows :
```
cd %USERPROFILE%\Desktop\pase-pilotage
```

**2) Créer l'environnement :**

Sur Mac :
```
conda env create -f environment_unix.yml
```
Sur Windows :
```
conda env create -f environment_windows.yml
```

Le programme va afficher beaucoup de texte et sembler bloqué par moments : **c'est
normal**, il télécharge. Attendez que la main vous soit rendue (le curseur revient
au début d'une ligne).

**3) Activer l'environnement :**
```
conda activate pase-2026-07
```
Vous devez maintenant voir `(pase-2026-07)` au début de votre ligne de commande.
**C'est le signe que tout est prêt.**

> **À retenir** : l'étape 3 (`conda activate pase-2026-07`) est à refaire
> **à chaque fois** que vous ouvrez une nouvelle fenêtre de Terminal. Les étapes
> 1 et 2, elles, ne se font qu'une seule fois.

---

## 3. Lancer une simulation

Dans le Terminal, avec `(pase-2026-07)` affiché au début de la ligne et en étant
dans le dossier du code, tapez :

```
python run_comparaison_pilotage.py
```

Le programme affiche sa progression pendant environ **30 secondes**, puis se
termine par un résumé qui ressemble à ceci :

```
======================================================================
  SIMULATION TERMINEE en 30.2 s
  -> OUTPUTS/COMPARAISONS_PILOTAGE/SIMU_18_Werbomont_2005-2006_4pan_simple_...
======================================================================
  - tracking_pur                             energie=   3.81 MWh   biomasse_fin=435.0
  - antitrack_pur                            energie=   1.24 MWh   biomasse_fin=577.1
  - antitrack_printemps                      energie=   3.43 MWh   biomasse_fin=444.6
  - antitrack_printemps_et_track_midi_ete    energie=   2.74 MWh   biomasse_fin=537.5
```

`biomasse_fin` est la valeur finale moyenne sur les points de la zone d'intérêt,
dans l'unité de `VARIABLE_CROP` (g/m² avec le modèle SIMPLE).

> Des messages `UserWarning: FigureCanvasAgg is non-interactive` peuvent
> apparaître : ce ne sont pas des erreurs.

---

## 4. Où regarder les résultats

Tout est rangé dans le dossier du code, sous :

```
OUTPUTS  →  COMPARAISONS_PILOTAGE  →  SIMU_18_...
```

Le numéro s'incrémente à chaque exécution ; rien n'est jamais écrasé. Contenu du
dossier :

| Fichier / dossier | Contenu |
|---|---|
| `INFOS_SIMULATION.md` / `.pdf` | Fiche des inputs effectivement utilisés : lieu, période, géométrie du parc, puissance installée, modèle de culture, discrétisation du ciel, et le détail des règles de chaque stratégie. |
| `1 - graphiques de comparaison/comparison_ranking.png` | Classement des stratégies en énergie et en culture, avec l'arbitrage entre les deux. |
| `1 - graphiques de comparaison/comparison_bars.png` | Totaux annuels par stratégie. |
| `1 - graphiques de comparaison/comparison_overlay.png`, `_combined.png`, `_grid.png` | Séries temporelles superposées, avec fond coloré selon le mode de pilotage actif. |
| `1 - graphiques de comparaison/comparison_tracking_grid.png` | Inclinaison appliquée heure par heure vs position solaire, à quatre saisons — contrôle de ce que fait réellement l'algorithme. |
| `2 - graphiques par pilotage/<stratégie>/` | Intégrales d'énergie PV et de culture, traces de pilotage par saison, et `carte_biomasse_annuelle.png` (répartition spatiale sur la zone d'intérêt). |
| `3 - csv trace tracking/` | Par stratégie et par année : `datetime`, élévation et azimut solaires, angle de tracking vrai, inclinaison appliquée, mode actif. Format CSV. |
| `structure_parc.png` | Rendu 3D de la géométrie simulée. |
| `AVIS_SIMULATION.txt` | Gabarit de compte rendu, avec les résultats chiffrés pré-remplis. |
| `PERFORMANCE.txt` | Durées par étape, machine, paramètres influant sur le temps de calcul. |
| `4 - fichiers pkl/` | Séries brutes sérialisées (production, résultats agronomiques, tilt/mode par année), pour retraitement en Python. |

---

## 5. Changer ce qui est simulé

Toutes les options se règlent **en haut d'un seul fichier** :
`run_comparaison_pilotage.py`.

Ouvrez-le avec un éditeur de texte simple (TextEdit sur Mac, Bloc-notes sur
Windows). Repérez la zone signalée par :

```
#  >>>>>>>>>>>>>>  PARAMETRES A MODIFIER PAR L'UTILISATEUR  <<<<<<<<<<<<<<<<<
```

C'est le **tableau de bord** de la simulation. Il ne contient pas les valeurs
elles-mêmes, mais **désigne les fichiers** dans lesquels elles sont écrites :

```python
FICHIER_LOC       = 'pystics_loc.yaml'                # le lieu et la période
FICHIER_AV        = 'Example2_tracking_AV_hugo.yaml'  # la structure des panneaux
FICHIER_PV_MODULE = 'Example1_PV_Module.yaml'         # le modèle de panneau
FICHIER_CROP      = 'simple_example.yml'              # le modèle de culture
```

Il y a donc **deux façons de modifier une simulation** :

1. **Changer de fichier** dans ce tableau de bord (utiliser un lieu déjà préparé) ;
2. **Modifier les valeurs à l'intérieur d'un fichier** (sections 5.2 et 5.3).

Les autres réglages du tableau de bord :

| Réglage | À quoi il sert |
|---|---|
| `STRATEGIES` | La liste des stratégies comparées. Pour en retirer une, mettez un `#` au début de sa ligne. |
| `JOURS_TRACE` | Les quatre journées illustrées sur les graphiques de vérification. |
| `VARIABLE_CROP` / `UNITE_CROP` | Ce qu'on mesure côté culture. ⚠️ `UNITE_CROP` n'est qu'une étiquette d'affichage : g/m² avec SIMPLE, t/ha avec pySTICS. À corriger à la main si l'on change de modèle (sinon facteur 100 sur les figures). |
| `GENERER_IMAGES_3D` | Mettre `False` pour aller plus vite (pas d'images 3D). |
| `MULTIPROCESSING` | `True` calcule les stratégies en parallèle (plus rapide). **Laisser `False` avec le modèle pySTICS.** |

**Enregistrez le fichier**, puis relancez `python run_comparaison_pilotage.py`.
Un nouveau dossier `SIMU_` est créé : **les résultats précédents ne sont jamais
écrasés.**

---

### 5.1 Format des fichiers d'entrée

Les inputs sont dans `INPUTS/`, au format **YAML**. Chaque paramètre est un bloc
`Value` / `Type` / `Limit` / `Unit` / `Definition` :

```yaml
Latitude:
   Value: 50.376                    # ← seule ligne à modifier
   Type: float
   Limit: [-90, 90]                 # validé au démarrage
   Unit: degrés décimaux [-]
   Definition: Latitude of the location, used for...
```

> **Quatre points de vigilance**
>
> 1. **Ne modifiez que la ligne `Value:`.** Les lignes `Type`, `Limit`, `Unit` et
>    `Definition` décrivent le paramètre — les changer casse le programme.
> 2. **Conservez l'indentation.** En YAML les espaces en début de ligne sont
>    significatifs : remplacez la valeur, rien d'autre.
> 3. **Respectez les bornes `Limit`.** La validation est stricte et bloque le
>    démarrage, avec un message indiquant le paramètre fautif.
> 4. **Travaillez sur une copie** du fichier, désignée dans le tableau de bord :
>    les fichiers d'exemple restent ainsi intacts comme référence.

---

### 5.2 Changer le lieu et la période — dossier `INPUTS/SCENARIOS/`

Le fichier utilisé par défaut est `pystics_loc.yaml`. Les paramètres principaux :

| Paramètre | Valeur actuelle | Ce qu'il fait |
|---|---|---|
| `LocationName` | Werbomont | Nom du lieu. Sert à nommer les dossiers de résultats — **changez-le** si vous changez les coordonnées, sinon les résultats seront rangés sous l'ancien nom. |
| `Latitude` / `Longitude` | 50.376 / 5.677 | Coordonnées en degrés décimaux. On les obtient en faisant un clic droit sur un point dans Google Maps. |
| `Altitude` | 165 | Altitude du site, en mètres. |
| `SimulationStartingYear` | 2005 | Première année simulée. **Pas avant 2005** (limite des données météo PVGIS). |
| `SimulationEndingYear` | 2006 | Dernière année, **incluse**. Mettre la même valeur que la précédente pour ne simuler qu'un an. |
| `TimeZone` | Etc/GMT+0 | Fuseau horaire. |
| `PrecisionLevelOnSunPosition` | 1 | **Le réglage qui pilote le temps de calcul.** `1` = une position solaire moyenne par mois (rapide) ; `2` = par semaine ; `3` = chaque jour (précis mais **beaucoup** plus long). Gardez `1` pour explorer, passez à `3` pour un résultat final. |

> ⚠️ **Les années disponibles dépendent de la région du monde** : jusqu'à 2023 en
> Europe/Afrique/Asie centrale, 2020 pour l'Asie et l'Amérique du Sud sous 20°S,
> 2015 pour les Amériques au-dessus de 20°S. En cas de doute, restez entre 2005
> et 2015.

> ⚠️ **La première simulation dans un nouveau lieu télécharge la météo** depuis
> le serveur PVGIS : comptez quelques minutes. Elle est ensuite mise en cache et
> les simulations suivantes au même endroit redeviennent rapides.

**La zone d'intérêt** (la parcelle où la culture est simulée) se règle dans le
même fichier :

| Paramètre | Valeur actuelle | Ce qu'il fait |
|---|---|---|
| `Xmin_InterestZone` / `Xmax_InterestZone` | -2 / 2 | Étendue de la parcelle sur l'axe X, en mètres. |
| `dX_InterestZone` | 2 | Pas de la grille en X : un point de calcul tous les 2 m. |
| `Ymin_InterestZone` / `Ymax_InterestZone` | 0 / 1 | Étendue sur l'axe Y. |
| `dY_InterestZone` | 1 | Pas de la grille en Y. |

> ⚠️ **Attention au temps de calcul** : le nombre de points de calcul est le
> produit des deux grilles. Diviser les pas par deux **quadruple** le nombre de
> points, et donc la durée. La configuration livrée fait 6 points (30 secondes) ;
> une simulation à 1700 points prend plusieurs minutes.

---

### 5.3 Changer la structure du parc — dossier `INPUTS/AV_CENTRAL/`

Le fichier utilisé par défaut est `Example2_tracking_AV_hugo.yaml`. Le parc est
organisé en **blocs** de panneaux (une rangée sur son support), répétés dans le
champ.

| Paramètre | Valeur actuelle | Ce qu'il fait |
|---|---|---|
| `NumberOfPanelsX` / `NumberOfPanelsY` | 1 / 4 | Nombre de panneaux **dans un bloc**, en largeur et en longueur. |
| `RepetitionDistanceOfPanelsX` / `...Y` | 2,450 / 1,953 | Espacement entre panneaux voisins d'un même bloc, en mètres. |
| `NumberOfPVBlocksX` / `NumberOfPVBlocksY` | 1 / 1 | Nombre de blocs (de rangées) dans le champ. **C'est ce qu'on augmente pour simuler un vrai parc.** |
| `RepetitionDistanceOfPVBlocksX` / `...Y` | 4,5 / 49 | Distance entre deux blocs, en mètres. En X, c'est l'écart entre rangées : le réduire densifie le parc et accroît l'ombrage. |
| `Height` | 1,22 | Hauteur de l'axe de rotation au-dessus du sol, en mètres. |
| `Hinge` | Center | Les panneaux pivotent autour de leur `Center` (centre) ou de leur `Top` (bord haut, panneaux suspendus). |
| `CentralAzimut` | 90 | Orientation du parc : **0 = Nord, 90 = Est, 180 = Sud, 270 = Ouest**. |
| `RotationAxisNumber` | 1 | `1` = les panneaux peuvent tourner (indispensable au pilotage) ; `0` = panneaux fixes. |
| `TiltY` | 20 | Inclinaison de départ, en degrés. Sert de référence ; c'est la stratégie de pilotage qui commande l'inclinaison réelle. |
| `MaxTiltAngle` | 90 | **Paramètre ajouté pour le pilotage.** Inclinaison maximale que le tracker peut atteindre. `90` = aucune limite. Le mettre à `60` simule un tracker à débattement limité. |

> ⚠️ Avec `Hinge: Center`, un panneau très incliné peut toucher le sol si
> `Height` est faible. Le programme vous avertit dans ce cas.

**Le modèle de panneau** (dimensions, puissance crête, bifacialité) se règle
séparément dans `INPUTS/HARDWARE/PV_MODULES/Example1_PV_Module.yaml`.

---

### 5.4 Créer ou modifier une stratégie de pilotage — `INPUTS/PILOTAGE/`

Ces fichiers ont un format **différent et beaucoup plus simple** que les
précédents (pas de `Value`/`Type`/`Limit`). Une stratégie est un **planning** :

```yaml
name: ma_strategie                      # nom court, sans espace ni accent
description: Ce que fait ma stratégie   # phrase affichée sur les graphiques
default_mode: tracking                  # ce qu'on fait le reste de l'année
rules:
  - name: protection_printemps
    date_start: "04-01"                 # du 1er avril...
    date_end: "05-15"                   # ...au 15 mai inclus
    mode: anti_tracking                 # on privilégie la culture
```

**Les trois modes possibles :**

| Mode | Effet |
|---|---|
| `tracking` | Les panneaux suivent le soleil. Maximise l'électricité. |
| `anti_tracking` | Les panneaux se mettent « en tranche » face au soleil. Maximise la lumière au sol. |
| `fixed` | Angle imposé. Nécessite une ligne supplémentaire `fixed_angle: 30` (en degrés). |

**Les règles du planning :**

- On peut **restreindre à une plage horaire** en ajoutant `hour_start: 11` et
  `hour_end: 14`. L'heure de début est **incluse**, l'heure de fin est **exclue**
  (11, 12 et 13 h dans cet exemple).
- **La première règle qui correspond l'emporte** : l'ordre des règles compte.
- Une période peut chevaucher le Nouvel An (`date_start: "12-01"` →
  `date_end: "02-28"`), et une plage horaire peut chevaucher minuit.
- Les dates s'écrivent **`"MM-DD"` entre guillemets**, sans l'année : la stratégie
  fonctionne quelle que soit l'année simulée.

**Pour créer votre stratégie** : dupliquez un fichier existant, renommez la copie
(par exemple `strategie_ete_agricole.yaml`), modifiez `name`, `description` et les
règles, puis **ajoutez son chemin à la liste `STRATEGIES`** en haut de
`run_comparaison_pilotage.py` :

```python
STRATEGIES = [
    os.path.join('INPUTS', 'PILOTAGE', 'strategie_tracking_pur.yaml'),
    os.path.join('INPUTS', 'PILOTAGE', 'strategie_ete_agricole.yaml'),   # ← la vôtre
]
```

> ⚠️ Deux stratégies comparées ne peuvent pas porter le même `name` : le
> programme refuse de démarrer pour éviter d'écraser des résultats. Pensez à
> changer le `name` **à l'intérieur** du fichier, pas seulement son nom de fichier.

Le fichier `strategie_antitrack_printemps_et_track_midi_ete.yaml` est l'exemple
le plus complet (trois règles combinant saisons et heures) — c'est le meilleur
point de départ pour comprendre.

---

### 5.5 Changer le modèle de culture — `INPUTS/CROPS/config/`

| Fichier | Modèle |
|---|---|
| `simple_example.yml` | **SIMPLE** — modèle rapide, utilisé par défaut. Résultats en g/m². |
| `pystics_example.yml` | **pySTICS** — modèle agronomique détaillé (blé d'hiver). Beaucoup plus lent (~4 min) et exige une installation supplémentaire. Résultats en t/ha. |
| `grassim_example.yml` | **Gras-Sim** — prairies. |

> Passer à pySTICS demande des étapes supplémentaires décrites dans
> `NOTES/MIGRATION_PASE_2.0.md`, et impose de mettre `MULTIPROCESSING = False`.
> Commencez par le modèle SIMPLE.

---

### 5.6 Exemple complet : simuler un vrai parc près de Gembloux

1. Dupliquer `INPUTS/SCENARIOS/pystics_loc.yaml` en `mon_site.yaml`.
2. Dans cette copie : `LocationName` → `Gembloux`, `Latitude` → `50.565114`,
   `Longitude` → `4.702089`, `Altitude` → `165`, `SimulationStartingYear` et
   `SimulationEndingYear` → `2020`.
   *(Ces valeurs sont celles du fichier `Example1_loc.yaml` déjà fourni — vous
   pouvez d'ailleurs simplement utiliser ce fichier directement.)*
3. Dupliquer `INPUTS/AV_CENTRAL/Example2_tracking_AV_hugo.yaml` en
   `mon_parc.yaml`, et y mettre `NumberOfPVBlocksX` → `3` (trois rangées).
4. Dans `run_comparaison_pilotage.py` : `FICHIER_LOC = 'mon_site.yaml'` et
   `FICHIER_AV = 'mon_parc.yaml'`.
5. Relancer `python run_comparaison_pilotage.py`.

La première exécution téléchargera la météo de Gembloux (quelques minutes), puis
un nouveau dossier `SIMU_` apparaîtra avec la comparaison complète.
