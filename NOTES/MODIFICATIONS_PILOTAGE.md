# Système de pilotage des trackers PASE — documentation complète des modifications

> **Usage de ce fichier** : documentation de référence des modifications apportées en juillet 2026
> (stage Hugo Lange — pilotage agrivoltaïque). Sert de référence pour comprendre, vérifier
> ou étendre le code.
> Le plan d'implémentation d'origine est dans `NOTES/PLAN_PILOTAGE.md`.

---

## 1. Objectif

Étudier l'impact du **pilotage de l'inclinaison des panneaux** sur les rendements agricoles et
énergétiques d'un système agrivoltaïque simulé avec PASE. Trois besoins :

1. **Tracer** ce que fait l'algorithme de tracking (angle panneau vs position du soleil, heure
   par heure) — en graphique matplotlib ET en CSV.
2. **Anti-tracking** : orienter les panneaux « en tranche » face au soleil (captation directe
   nulle → lumière maximale au sol pour les cultures).
3. **Planning de pilotage** : basculer tracking / anti-tracking / tilt fixe à n'importe quelle
   heure et n'importe quelle période de l'année, via un fichier YAML, pour comparer des
   stratégies avec l'outillage existant (`save_simulation` + `compare_simulations.py`).

Décisions prises avec Hugo :
- Limite d'angle **configurable** (`MaxTiltAngle` en YAML), **défaut = 90° (sans limite)**.
- Anti-tracking **pur** : tilt = angle de tracking vrai ± 90°, **sans** correction backtracking
  (le backtracking sert à maximiser la production PV, hors sujet en anti-tracking).
- Tout code ajouté/modifié encadré de marqueurs visuels :
  `# ============== [HUGO - PILOTAGE] DEBUT AJOUT ============== ` … `FIN AJOUT`
  (variante `DEBUT/FIN MODIF` pour le code existant modifié). **Chercher `[HUGO - PILOTAGE]`
  dans le repo pour retrouver instantanément toutes les modifications.**

---

## 2. Fait architectural essentiel (à connaître avant toute modification)

**Le tracking est implémenté DEUX FOIS dans PASE**, avec la même math mais des résolutions
temporelles et des limites différentes :

| | Côté géométrie / lumière | Côté production électrique |
|---|---|---|
| Fichier | `pase/PHOTOVOLTAICS/configuration.py` | `pase/PHOTOVOLTAICS/production.py` |
| Classe | `PV_Configuration_3D` | `PV_Production` |
| Entrée soleil | `Sun_positions_sampled` (jours échantillonnés selon `PrecisionLevelOnSunPosition`, nuit filtrée) | `Sun_positions` (8760/8784 h, année complète) |
| Sortie | un mesh PyVista **par position solaire** (`PV_central_PD_list`) → ray casting → lumière au sol → cultures | série `tiltY` numpy → HDKR/GTI → puissance |
| Limite historique | clamp codé en dur **±60°** | angles > ±90° **mis à 0** (bug) |

Pipeline mathématique commun (identique dans les deux fichiers) :
vecteur soleil tourné dans le repère de la centrale (azimut) → angle de tracking vrai
`arctan2(sun_x_cc, sun_z_cc)` → correction backtracking (évite l'ombrage mutuel entre rangées)
→ limitation d'angle.

**Conséquence** : toute modification des angles doit toucher les deux côtés de façon cohérente.
C'est pourquoi la solution centralise la logique dans UN module (`pilotage.py`) que les deux
côtés appellent.

### Bugs historiques découverts (importants)

1. **`production.py get_limitated_angle`** (bug corrigé dans le nouveau chemin) : les angles
   au-delà de ±90° étaient mis à **0** (panneau à plat) au lieu d'être clampés. Corrigé en
   `np.clip(±MaxTiltAngle)` — l'ancienne version est gardée en commentaire dans le code.
   Impact énergétique mesuré : **nul** (ces angles n'arrivent que la nuit, quand la production
   est nulle de toute façon) — vérifié par le test de non-régression (§6).
2. **`configuration.py get_sun_vect_in_central_coord`** (bug NON corrigé dans le chemin
   historique, mais évité par le contrôleur) : reçoit `CentralAzimut` en **degrés** mais
   l'utilise directement dans `np.cos/np.sin` (qui attendent des **radians**). Le
   `TrackingController` convertit correctement en radians → quand on passe un contrôleur, les
   angles géométrie sont justes ET identiques à ceux de la production.

---

## 3. Fichiers CRÉÉS

### 3.1 `pase/PHOTOVOLTAICS/pilotage.py` — le cœur du système

Deux classes :

**`PilotageStrategy`** — le planning.
- `PilotageStrategy.from_yaml(path)` : charge un fichier `INPUTS/PILOTAGE/*.yaml`.
  Choix : `yaml.safe_load` pur + validateur dédié, PAS `YAML_Inputs_provider`, car le format
  PASE `{Value, Type, Limit}` est prévu pour des scalaires indépendants, pas pour une liste de
  règles hétérogènes.
- `resolve(datetime_index)` → `(modes, fixed_angles)` : résolution **vectorisée** du mode actif
  à chaque instant. Règles :
  - `date_start`/`date_end` : format `"MM-DD"`, bornes **incluses**, indépendant de l'année
    (year-agnostic → gère les années template de PASE et le 29/02), fenêtre à cheval sur le
    nouvel an autorisée (ex. `12-01` → `02-28`).
  - `hour_start`/`hour_end` : heure de début **incluse**, heure de fin **EXCLUE**
    (`hour_start <= h < hour_end`), fenêtre à cheval sur minuit autorisée.
  - **La première règle qui matche gagne** (l'ordre des règles compte) ; sinon `default_mode`.
  - Modes : `tracking` | `anti_tracking` | `fixed` (avec `fixed_angle` en degrés, obligatoire).
- Validation stricte au chargement (mode inconnu, `fixed` sans `fixed_angle`, borne de date ou
  d'heure seule, format MM-DD invalide → `ValueError` avec message explicite).

**`TrackingController`** — le calcul d'angle, utilisé par LES DEUX côtés de PASE.
- `TrackingController.from_inputs(strategy, pv_params_dict)` : constructeur pratique depuis le
  dictionnaire d'inputs agrégé (extrait `CentralAzimut`, calcule `GCR_x`, lit
  `MaxTiltAngle` avec défaut 90, `Height`/`span_x`/`Hinge` pour le warning de garde au sol).
- `compute_tilt(sun_vect, datetime_index)` → dict d'arrays alignés :
  `{'tilt_deg', 'mode', 'true_angle_deg', 'sun_vect_cc'}`. Pipeline :
  1. Rotation du vecteur soleil dans le repère de la centrale (azimut converti en **radians** —
     corrige le bug historique côté géométrie).
  2. Angle de tracking vrai `arctan2(x_cc, z_cc)` ∈ (-90°, 90°) le jour.
  3. **tracking** : angle vrai + correction backtracking (méthode reprise à l'identique de
     `PV_Production.get_backT_corr_angle`, version la plus générale avec `soil_angle`).
  4. **anti_tracking** : `np.where(true_angle > 0, true_angle - 90°, true_angle + 90°)` →
     le plan du panneau contient le rayon solaire (normale ⊥ soleil, captation directe nulle),
     résultat dans (-90°, 90°], **sans backtracking**.
  5. **fixed** : angle de la règle.
  6. Assemblage par masques de mode puis **clamp** final `np.clip(±MaxTiltAngle)`.
- Warning (via logger) à la construction si `Height - span_x/2·sin(MaxTiltAngle)` ≤ 0 avec
  `Hinge: Center` (le check statique de `Inputs_aggregator._check_panel_ground_clearance`
  n'utilise que le `TiltY` du YAML, pas le tilt dynamique).

### 3.2 `INPUTS/PILOTAGE/` — les stratégies (nouveau dossier)

- `strategie_tracking_pur.yaml` : `default_mode: tracking`, `rules: []` — référence de
  non-régression (reproduit le comportement historique).
- `strategie_antitrack_pur.yaml` : anti-tracking toute l'année — cas extrême « lumière max au sol ».
- `strategie_antitrack_printemps.yaml` : exemple mixte — anti-tracking du 01/04 au 15/05,
  puis en été (01/06–31/08) tracking de 11h à 14h et anti-tracking le reste de la journée,
  tracking par défaut le reste de l'année. Le format y est documenté en commentaires.

Pour créer une nouvelle stratégie : copier un de ces fichiers, éditer les règles, changer
`STRATEGIE_PILOTAGE` dans `example_tracking_hugo.py`.

### 3.3 `pase/DATA_MANAGEMENT/plots/tracking_trace.py` — la trace de vérification

`export_tracking_trace(tilt_series, mode_series, true_angle_series, sun_positions_df, label,
day=None, max_tilt_deg=90, csv_dir='OUTPUTS', fig_dir='OUTPUTS/GRAPHS', show=False)` :

- **CSV** `OUTPUTS/tracking_trace_<label>.csv` — année complète, résolution horaire, colonnes :
  `datetime, sun_elevation, sun_azimuth, true_tracking_angle, applied_panel_tilt, mode`.
- **Figure** `OUTPUTS/GRAPHS/tracking_trace_<label>_<day>.png` — pour le jour `day`
  (`'YYYY-MM-DD'`) : tilt appliqué (noir) + angle de tracking vrai (orange, axe gauche),
  élévation solaire (bleu, axe droit), bandes de fond colorées par mode actif
  (vert=tracking, rouge=anti_tracking, bleu=fixed), pointillés ±MaxTiltAngle.
- La trace est construite côté **production** (horaire, année complète). Les meshes 3D côté
  géométrie n'existent qu'aux positions solaires échantillonnées mais utilisent le **même**
  contrôleur → mêmes angles (vérifié, §6).
- `savefig` avant `show` (backend matplotlib 'MacOSX' forcé, comme les autres modules de plots).

---

## 4. Fichiers MODIFIÉS (blocs marqués `[HUGO - PILOTAGE]`)

### 4.1 `INPUTS/AV_CENTRAL/Example2_tracking_AV_hugo.yaml`
Ajout du paramètre :
```yaml
MaxTiltAngle:
   Value: 90        # 90 = pas de limite (défaut demandé par Hugo)
   Type: float
   Limit: [0, 90]
```
Lu partout via `inputs.get('MaxTiltAngle', 90)` → les autres YAML d'exemple (sans ce paramètre)
continuent de fonctionner.

### 4.2 `pase/PHOTOVOLTAICS/production.py` (`PV_Production`)
- `__init__(self, inputs, pilotage_controller=None)` : nouveau kwarg optionnel ; stocke
  `self.max_tilt` (radians) et initialise `self.tiltY_per_year / mode_per_year /
  true_angle_per_year = {}`.
- `get_tiltY_along_time(self, sun_vect, datetimes=None)` : si un contrôleur est présent,
  **délègue entièrement** à `controller.compute_tilt(sun_vect, datetimes)` (et mémorise
  mode/angle vrai dans `self._last_mode / _last_true_angle`) ; sinon pipeline historique
  inchangé.
- Dans `get_several_years_of_electricity_production` : passe `datetimes=WD[year].index`
  (dates réelles de l'année → le planning est résolu sur les vraies dates) et **stocke** les
  séries par année (`pd.Series` indexées sur l'index météo) — c'est la source de la trace.
- **Bugfix** `get_limitated_angle` : `np.clip(tiltY, -self.max_tilt, self.max_tilt)` au lieu de
  la mise à 0 (ancienne version en commentaire).

### 4.3 `pase/PHOTOVOLTAICS/configuration.py` (`PV_Configuration_3D`)
- `__init__` : nouveaux kwargs `pilotage_controller=None, sun_datetimes=None`, extraits par
  `kwargs.pop(...)` **avant** `super().__init__(**kwargs)` (la classe parente ne les connaît
  pas). Si contrôleur fourni : `self.tiltY_along_time = controller.compute_tilt(sun_vector,
  sun_datetimes)['tilt_deg']` (+ `self.pilotage_mode_along_time`) à la place du pipeline
  historique. La boucle de construction des meshes (`create_tilted_central` par position
  solaire) est inchangée — elle consomme `tiltY_along_time` en degrés comme avant.
- `sun_datetimes` attendu : `Sun_positions_samp.SP.index` (aligné 1:1 avec `solar_vector`,
  nuit déjà filtrée).
- Sans contrôleur : comportement historique strictement inchangé (les autres scripts
  `example_*.py` ne sont pas affectés).

### 4.4 `pase/DATA_MANAGEMENT/simulation_results.py`
- `save_simulation(..., pilotage=None)` : kwarg optionnel ; si fourni, ajoute la clé
  `'pilotage'` au pickle. **Rétro-compatible** : les anciens pickles n'ont simplement pas la
  clé ; `load_simulation` / `compare_simulations.py` inchangés.

### 4.5 `example_tracking_hugo.py` (script principal de Hugo)
1. **En tête de script** (à modifier pour changer de configuration) :
   ```python
   STRATEGIE_PILOTAGE = os.path.join('INPUTS', 'PILOTAGE', 'strategie_antitrack_printemps.yaml')
   JOUR_TRACE = '2020-06-15'   # jour du graphique de vérification
   ```
2. Après l'agrégation des inputs : chargement de la stratégie + création du contrôleur
   (`TrackingController.from_inputs`).
3. `PV_Configuration_3D(..., pilotage_controller=..., sun_datetimes=Sun_positions_samp.SP.index)`.
4. `PV_Production(PV_params_dict, pilotage_controller=...)`.
5. Après le calcul de production : boucle `export_tracking_trace` par année (CSV toujours,
   figure pour l'année contenant `JOUR_TRACE`).
6. `save_simulation(f'pilotage_{strategie.name}', ..., pilotage={...})` — le label inclut le
   nom de la stratégie ; le pickle contient tilt/mode/angle vrai par année.

---

## 5. Comment lancer / comparer des stratégies

```bash
# Environnement : conda pase3 (le .venv du repo est incomplet)
/opt/homebrew/Caskroom/miniforge/base/envs/pase3/bin/python example_tracking_hugo.py
```

1. Choisir la stratégie via `STRATEGIE_PILOTAGE` en tête d'`example_tracking_hugo.py`.
2. Lancer la simulation → CSV dans `OUTPUTS/`, figure dans `OUTPUTS/GRAPHS/`,
   pickle dans `OUTPUTS/simulations/pilotage_<nom>.pkl`.
3. Changer de stratégie, relancer.
4. `python compare_simulations.py` → graphes de comparaison (biomasse ; la production PV
   annuelle s'affiche aussi dans le terminal à chaque run).

Astuce vitesse : mettre `PrecisionLevelOnSunPosition: 1` (jour 15 de chaque mois) dans
`INPUTS/SCENARIOS/Example1_loc_hugo.yaml` pour des tests rapides ; `3` (tous les jours) pour
les résultats finaux.

---

## 6. Vérification effectuée (tout est passé)

### 6.1 Tests unitaires du module seul (22 vérifications)
Script : `tests/PHOTOVOLTAICS/test_pilotage_unitaire.py` (relançable à tout moment avec l'env
conda pase3). Couvre :
- Chargement des 3 YAML de stratégie.
- Résolution du planning : 9 assertions sur des instants précis (avril → anti_tracking,
  15 mai inclus / 16 mai exclu, 12h-13h été → tracking, 14h → anti (hour_end exclu),
  janvier/septembre → default).
- Fenêtre à cheval sur le nouvel an (12-01 → 02-28) + mode `fixed` avec angle.
- **Math tracking** : sur vecteurs solaires synthétiques (soleil balayant Est→Ouest),
  tilt = angle vrai exactement (GCR faible = pas de backtracking), signe + à l'Est / - à l'Ouest.
- **Math anti-tracking** : `|tilt - angle_vrai| = 90°` exactement, et produit scalaire
  normale·soleil = 0 (captation directe nulle vérifiée numériquement).
- Clamp : `|tilt| ≤ 60` partout avec MaxTiltAngle=60.
- Backtracking : angle réduit quand le soleil est bas avec GCR=0.53.
- Rotation d'azimut en radians (bug historique évité).
- 3 cas d'erreur de validation rejetés proprement.

### 6.2 Test d'intégration sur le vrai pipeline (8 étapes)
Script : `tests/PHOTOVOLTAICS/test_pilotage_integration.py` (relançable ; sorties de test dans
`OUTPUTS/GRAPHS/TEST_PILOTAGE/`). Météo Gembloux 2020 depuis le cache
PVGIS, stratégie mixte `antitrack_printemps`, sans GUI ni ray casting :
1. `MaxTiltAngle` parsé depuis le YAML (=90).
2. Météo chargée (8784 pas, 2020 bissextile).
3. Positions solaires : 143 échantillonnées (niveau 1) / 8784 complètes.
4. **Géométrie 3D avec contrôleur** : 143 meshes construits, tilts jusqu'à ±89° (quasi
   verticaux) sans erreur, 67 instants en anti-tracking.
5. Production stratégie mixte : 1.51 MWh (2020).
6. **Cohérence géométrie ↔ production** : sur les 143 instants appariés (par mois-jour-heure),
   modes identiques des deux côtés, différence d'angle médiane 0.11° (uniquement due aux
   10 min d'écart d'horodatage PVGIS, voir §7).
7. **Non-régression** : `strategie_tracking_pur` via contrôleur = 2.252 MWh vs pipeline
   historique = 2.252 MWh, **écart 0.000 %** → le nouveau système reproduit exactement le
   tracking historique, et le bugfix clamp n'a aucun impact énergétique (les angles hors
   limites n'existaient que la nuit).
8. **Trace** : CSV vérifié (modes corrects aux instants tests, perpendicularité anti-tracking
   à 0.01° près), figure du 15/06 générée et inspectée visuellement — tilt suit l'angle vrai
   dans la bande tracking 11h-14h, à 90° de l'angle vrai partout ailleurs.

### 6.3 Compilation
`python -m py_compile` OK sur les 7 fichiers créés/modifiés, `example.py` (chemin historique)
compris.

---

## 7. Pièges et limites à connaître (pour les modifications futures)

- **Horodatage** : la météo PVGIS est indexée à **HH:10** (tz-naïve) ; les positions solaires
  à HH:00 (tz-aware, années template 2005/2020). PASE aligne **par position**, pas par
  timestamp. Le CSV de trace est donc à HH:10. Pour comparer des séries entre les deux côtés,
  apparier sur (mois, jour, heure).
- **Saut d'angle en anti-tracking** : quand l'angle de tracking vrai change de signe (passage
  du soleil dans le plan de l'axe), le tilt anti-tracking bascule de +90° côté à -90° côté
  (ex. +88° → -77°). C'est inhérent à la contrainte tilt ∈ (-90°, 90°] ; les deux orientations
  sont perpendiculaires au soleil.
- **La nuit**, les valeurs de tilt/mode dans la trace n'ont pas de sens physique (production
  et lumière nulles) — ne pas s'en inquiéter en lisant le CSV.
- **Hash de variant** : `OutputsManager.setup_variant` n'inclut PAS le fichier de stratégie
  dans le hash → deux stratégies différentes réutilisent le même `variant_XX`. La comparaison
  passe par les pickles `OUTPUTS/simulations/` (distincts par label), pas par les variants.
- **Chemin historique intact** : sans `pilotage_controller`, `configuration.py` garde son
  clamp ±60° ET son bug d'azimut degrés/radians ; `production.py` sans contrôleur utilise le
  nouveau clamp `MaxTiltAngle` (défaut 90°, quasi équivalent à l'ancien comportement — écart
  mesuré nul). Pour un comportement 100 % identique des deux côtés, toujours passer par le
  contrôleur.
- Le check statique de garde au sol (`_check_panel_ground_clearance`) utilise le `TiltY` du
  YAML ; avec le pilotage dynamique c'est le **warning du TrackingController** qui couvre le
  cas `Hinge: Center` à MaxTiltAngle.

---

## 8. Récapitulatif des fichiers

| Fichier | Statut | Rôle |
|---|---|---|
| `pase/PHOTOVOLTAICS/pilotage.py` | **créé** | Stratégie YAML + contrôleur d'angles (cœur) |
| `INPUTS/PILOTAGE/strategie_*.yaml` (×3) | **créés** | Stratégies de pilotage |
| `pase/DATA_MANAGEMENT/plots/tracking_trace.py` | **créé** | Trace CSV + figure journalière |
| `INPUTS/AV_CENTRAL/Example2_tracking_AV_hugo.yaml` | modifié | + `MaxTiltAngle` |
| `pase/PHOTOVOLTAICS/production.py` | modifié | Délégation, bugfix clamp, stockage séries |
| `pase/PHOTOVOLTAICS/configuration.py` | modifié | Délégation (kwargs contrôleur + datetimes) |
| `pase/DATA_MANAGEMENT/simulation_results.py` | modifié | Pickle + clé `pilotage` (rétro-compat.) |
| `example_tracking_hugo.py` | modifié | Câblage complet + trace + sauvegarde |
| `tests/PHOTOVOLTAICS/test_pilotage_unitaire.py` | **créé** | 22 vérifications unitaires du module pilotage |
| `tests/PHOTOVOLTAICS/test_pilotage_integration.py` | **créé** | 8 étapes d'intégration sur le vrai pipeline |
| `NOTES/PLAN_PILOTAGE.md` | créé | Plan d'implémentation d'origine |
| `NOTES/MODIFICATIONS_PILOTAGE.md` | créé | Ce document |

Toutes les modifications sont retrouvables avec : `grep -rn "HUGO - PILOTAGE" .`

---

## 9. Journal des modifications (postérieures au document initial)

> Les sections 1-8 ci-dessus décrivent le **cœur du système de pilotage** (module
> `pilotage.py`, anti-tracking, MaxTiltAngle, trace de vérification). Ce journal liste,
> **par date**, tout ce qui a été ajouté ensuite. Les nouveaux fichiers/fonctions
> restent tous marqués `[HUGO - PILOTAGE]`.

### 2026-07-20 — Outillage de comparaison, visuels, multiprocessing

**Orchestrateur de comparaison** — nouveau `run_comparaison_pilotage.py` : lance
plusieurs politiques de pilotage sur le MÊME parc/année/météo et range tout dans une
arborescence auto-numérotée `OUTPUTS/COMPARAISONS_PILOTAGE/SIMU_<N>_<mots-cles>/`
(sous-dossiers : 1 comparaison, 2 par pilotage, 3 CSV, 4 pkl). Garde-fou : refuse deux
stratégies de même `name:`.

**Documents auto-générés** — nouveau module `pase/DATA_MANAGEMENT/simulation_report.py` :
- `INFOS_SIMULATION.md` : fiche des inputs (résumé important en avant + détail complet).
- `INFOS_SIMULATION.pdf` : même contenu, PDF lisible généré via **matplotlib** (aucune
  dépendance ajoutée). `.md` et `.pdf` partagent la même source (`_blocs_description`).
- `AVIS_SIMULATION.txt` : fiche d'avis à remplir (résultats pré-remplis).
- `PERFORMANCE.txt` : durées + machine + stratégie d'exécution.
- Titre du dossier SIMU enrichi : nombre de panneaux + modèle de culture.

**JOURS_TRACE** — évolution du format : d'une date unique → **liste de jours** (une figure
par jour) → ajout d'un **mot-clé de saison** (titre + nom de fichier) → format final
**`('MM-DD', 'saison')` sans année** (l'année de simulation est préfixée automatiquement :
changer d'année ne casse plus rien).

**Visuels de comparaison** (`plot_comparison_graphs.py`, `pv_energy_integral.py`,
`biomass_integral.py`, `tracking_trace.py`) :
- Bandes de fond colorées par **mode de pilotage** (vert=tracking, rouge=anti-tracking,
  bleu=fixe, **violet=hybride** = un jour qui mélange plusieurs modes) sur les intégrales
  PV/biomasse et le graphe `grid`. Helper partagé `draw_mode_bands` (classification par jour).
- Nouveau graphe **`comparison_ranking.png`** : classement énergie PV vs biomasse (bump
  chart) — montre l'arbitrage d'un coup d'œil.
- Nouveau **`comparison_tracking_grid.png`** : grille des traces de pilotage (lignes =
  saisons, colonnes = pilotages) — remplace l'ancienne comparaison par jour.

**Images 3D** — nouveau module `pase/DATA_MANAGEMENT/plots/scene_screenshot.py` (rendu
**off-screen** PyVista, sans fenêtre) : `structure_parc.png` (une fois) + carte de biomasse
par pilotage.

**AVIS** — retrait des rubriques « hypothèse » et « verdict global ».

**Performance / multiprocessing** — `run_comparaison_pilotage.py` restructuré (pipeline par
stratégie = fonction top-level `run_one_strategy`, orchestration sous `if __name__ ==
'__main__'`). Les stratégies (indépendantes) sont calculées **en parallèle** (flags
`MULTIPROCESSING`, `N_WORKERS`, `GENERER_IMAGES_3D`). Pièges résolus : (a) PASE parallélise
déjà le diffus en interne (`joblib n_jobs=-1`, light.py) → répartition des cœurs entre
workers pour éviter la sur-souscription ; (b) threads BLAS/OpenMP cappés à 1/processus ;
(c) arrêt explicite du pool loky en fin de worker (sinon deadlock). **Mesuré : 77 s → 16 s
(~4.8× sur 4 stratégies).**

**Robustesse backend matplotlib** — les modules de plot ne forcent plus `MacOSX` s'ils
détectent qu'`Agg` a été choisi (mode batch) → plus de `plt.show()` bloquant.

### 2026-07-21 — Netteté des images 3D + carte de biomasse annuelle

- **Netteté** des captures 3D (`scene_screenshot.py`) : résolution portée à **1920×1280**,
  **supersampling ×2** et **anti-aliasing SSAA** (helper `_screenshot_net`). La structure du
  parc affiche en plus les arêtes des panneaux (`show_edges`).
- **Carte de biomasse annuelle** : renommée `carte_biomasse_annuelle.png`, titre « Biomasse
  cumulée sur l'année ». Rappel : la biomasse s'accumulant sur la saison, la valeur de fin de
  saison à chaque point du sol = la biomasse totale produite **sur l'année** à cet endroit.
  La caméra utilise `vue='defaut'` = **cadrage automatique de PyVista**, identique à la vue
  proposée à l'ouverture de la fenêtre interactive `visualize_map` (pas de zoom forcé).
  Options alternatives : `vue='dessus'` (vue de haut) ou `vue='iso'`.
- Ajout de ce **journal daté** au présent document.

### Nouveaux fichiers depuis le document initial

| Fichier | Rôle |
|---|---|
| `run_comparaison_pilotage.py` | Orchestrateur de comparaison multi-pilotages (+ multiprocessing) |
| `pase/DATA_MANAGEMENT/simulation_report.py` | Arborescence SIMU + fiche inputs (md/pdf) + avis + performance |
| `pase/DATA_MANAGEMENT/plots/scene_screenshot.py` | Captures 3D off-screen (structure parc + carte biomasse) |
| `pase/DATA_MANAGEMENT/plots/plot_comparison_graphs.py` | (existant) + ranking, grid tracking, bandes de mode |
| `INPUTS/PILOTAGE/strategie_antitrack_printemps_et_track_midi_ete.yaml` | Stratégie mixte d'exemple (hybride en été) |
