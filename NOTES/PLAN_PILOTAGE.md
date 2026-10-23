# Plan — Pilotage des trackers PASE : anti-tracking, planning tracking/anti-tracking, trace de vérification

## Contexte

Stage : étudier l'impact du pilotage de l'inclinaison des panneaux sur les rendements agricoles et énergétiques d'un système agrivoltaïque, via PASE. Le tracking 1 axe existe déjà (`RotationAxisNumber: 1`). Objectifs :
1. Analyser + tracer ce que fait le tracking (angle panneau vs position soleil, heure par heure) — graphique matplotlib **et** CSV.
2. Implémenter l'**anti-tracking** (panneau « en tranche » face au soleil : tilt = angle de tracking vrai ± 90°, **sans** correction backtracking).
3. Permettre un **planning de pilotage** (YAML dédié) : basculer tracking / anti-tracking / tilt fixe par fenêtres de dates (MM-DD) et d'heures, pour comparer des stratégies via l'outillage `save_simulation` / `compare_simulations.py` existant.

**Décisions utilisateur** : limite d'angle configurable en YAML (`MaxTiltAngle`), **défaut = 90° (pas de limite)** ; planning en fichier YAML dédié ; trace = graphique + CSV ; anti-tracking pur (sans backtracking). Tout code ajouté/modifié encadré de marqueurs visuels :

```python
# ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
...
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============
```
(variante `DEBUT/FIN MODIF` pour le code existant modifié).

## Fait architectural clé (analyse)

Le tracking est implémenté **deux fois** avec la même math (`arctan2(sun_x_cc, sun_z_cc)` + correction backtracking + limitation) :
- **Côté géométrie/lumière** : `pase/PHOTOVOLTAICS/configuration.py`, `PV_Configuration_3D.__init__` (l.1348-1375) → `get_tiltY_along_time` (l.1584-1642, clamp codé en dur ±60°) → un mesh PyVista par position solaire échantillonnée (`Sun_positions_sampled`, nuit filtrée). Alimente le ray casting → lumière au sol → cultures.
- **Côté production électrique** : `pase/PHOTOVOLTAICS/production.py`, `PV_Production.get_tiltY_along_time` (l.257-334), résolution horaire année complète (`Sun_positions`). **Bug** : `get_limitated_angle` (l.327-334) met à **0** les angles au-delà de ±90° au lieu de clamper. Le `tiltY` calculé est une variable locale (l.81), jamais stockée.

Toute modification doit toucher les deux côtés de façon cohérente → logique centralisée dans un module unique.

## Fichiers à créer

### 1. `pase/PHOTOVOLTAICS/pilotage.py` (nouveau — cœur du système)

- **`PilotageStrategy`** : charge le YAML de stratégie (`yaml.safe_load` pur + validateur dédié — le format `{Value,Type,Limit}` de `YAML_Inputs_provider` ne convient pas à une liste de règles). `from_yaml(path)` ; `resolve(datetime_index) -> (modes, fixed_angles)` vectorisé : clé `month*100+day` pour les dates (bornes incluses, wrap autorisé si start > end), `hour_start <= h < hour_end` (wrap autorisé), **première règle qui matche gagne**, sinon `default_mode`. Year-agnostic (gère les années template et le 29/02). Modes : `tracking`, `anti_tracking`, `fixed` (+ `fixed_angle`).
- **`TrackingController`** : `__init__(strategy, azimut_deg, GCR_x, max_tilt_deg=90)` ; `compute_tilt(sun_vect, datetime_index) -> dict {'tilt_deg', 'mode', 'true_angle_deg', 'sun_vect_cc'}`. Pipeline (fonctions reprises de `production.py:284-334`, version la plus générale) :
  1. Rotation du vecteur soleil dans le repère de la centrale → `true_angle = arctan2(x_cc, z_cc)` ∈ (-90°, 90°) pour soleil au-dessus de l'horizon.
  2. `tracking` : `true_angle + backtracking_corr(GCR_x)`.
  3. `anti_tracking` : `np.where(true_angle > 0, true_angle - π/2, true_angle + π/2)` → résultat dans (-90°, 90°], plan du panneau contenant le rayon solaire (captation directe nulle). Pas de backtracking.
  4. `fixed` : angle de la règle.
  5. Assemblage par masques de mode + **clamp** `np.clip(±max_tilt_deg)`.
- Warning (via `PASE_Logger`) si `Height - span_x/2·sin(max_tilt)` ≤ 0 avec `Hinge: Center` (le check statique `_check_panel_ground_clearance` de `yaml_inputs_provider.py:234` n'utilise que le TiltY du YAML, pas le tilt dynamique).

### 2. `INPUTS/PILOTAGE/` (nouveau dossier) — fichiers de stratégie

```yaml
# strategie_antitrack_printemps.yaml
name: antitrack_printemps
default_mode: tracking
rules:
  - name: protection_cultures_printemps
    date_start: "04-01"     # MM-DD, indépendant de l'année
    date_end: "05-15"
    mode: anti_tracking
  - name: prod_midi_ete
    date_start: "06-01"
    date_end: "08-31"
    hour_start: 11          # optionnel
    hour_end: 14
    mode: tracking
```
Fournir aussi : `strategie_tracking_pur.yaml` (rules: [], référence non-régression) et `strategie_antitrack_pur.yaml`.

### 3. `pase/DATA_MANAGEMENT/plots/tracking_trace.py` (nouveau — trace de vérification)

```python
def export_tracking_trace(tilt_series, mode_series, true_angle_series,
                          sun_positions_df,  # SP.sp_leapY/sp_nonleapY (elevation, azimuth)
                          label, day=None,   # 'YYYY-MM-DD' → figure de ce jour
                          csv_dir='OUTPUTS', fig_dir='OUTPUTS/GRAPHS') -> (csv_path, fig_path)
```
- **CSV** (`OUTPUTS/tracking_trace_<label>.csv`) : `datetime, sun_elevation, sun_azimuth, true_tracking_angle, applied_panel_tilt, mode` — année complète, résolution horaire (côté production). Alignement par position (mêmes longueurs 8760/8784).
- **Figure** (`OUTPUTS/GRAPHS/tracking_trace_<label>_<day>.png`) : tilt appliqué + angle de tracking vrai (axe gauche, °), élévation solaire (axe droit), bandes `axvspan` colorées par mode actif, pointillés ±MaxTiltAngle. `savefig` avant tout `show` (backend MacOSX utilisé ailleurs).

## Fichiers à modifier

### 4. `INPUTS/AV_CENTRAL/Example2_tracking_AV_hugo.yaml` — paramètre `MaxTiltAngle`

```yaml
MaxTiltAngle:
   Value: 90        # 90 = pas de limite (défaut)
   Type: float
   Limit: [0, 90]
```
Lecture partout via `inputs.get('MaxTiltAngle', 90)` pour ne pas casser les autres YAML.

### 5. `pase/PHOTOVOLTAICS/production.py`

- `__init__` (l.18) : + kwarg `pilotage_controller=None` ; `self.max_tilt` depuis `inputs.get('MaxTiltAngle', 90)`.
- `get_tiltY_along_time` (l.257) : si contrôleur → délègue à `controller.compute_tilt(sun_vect, datetimes)` ; sinon pipeline historique.
- **Bugfix** `get_limitated_angle` (l.327-334) : mise à zéro > ±π/2 → **clamp à ±max_tilt** (ancienne version gardée en commentaire pour le rapport).
- `get_several_years_of_electricity_production` (l.68-112) : stocker par année `self.tiltY_per_year[year]`, `self.mode_per_year[year]`, `self.true_angle_per_year[year]` en `pd.Series` indexées sur `WD[year].index` (source de la trace).

### 6. `pase/PHOTOVOLTAICS/configuration.py`

- `PV_Configuration_3D.__init__` (l.1348-1375) : + kwargs `pilotage_controller=None, sun_datetimes=None` (extraits **avant** `super().__init__(**kwargs)`). Si contrôleur : `self.tiltY_along_time = controller.compute_tilt(sun_vector, sun_datetimes)['tilt_deg']` à la place de `self.get_tiltY_along_time(...)`. Boucle `create_tilted_central` (l.1370-1373) inchangée.
- Datetimes fournis par `Sun_positions_samp.SP.index` (aligné 1:1 avec `solar_vector`, nuit déjà filtrée — light.py:472-512).

### 7. `example_tracking_hugo.py` — câblage

1. Paramètres en tête de script (bloc marqué) : `STRATEGIE_PILOTAGE = 'INPUTS/PILOTAGE/strategie_antitrack_printemps.yaml'`, `JOUR_TRACE = '2020-06-15'`.
2. Après l.60 : `PilotageStrategy.from_yaml(...)` + `TrackingController(strategie, azimut_deg=PV_params_dict['CentralAzimut'], GCR_x=..., max_tilt_deg=PV_params_dict.get('MaxTiltAngle', 90))`.
3. l.138 : passer `pilotage_controller=controller, sun_datetimes=Sun_positions_samp.SP.index` à `PV_Configuration_3D`.
4. l.191 : `PV_Production(PV_params_dict, pilotage_controller=controller)`.
5. Après l.194 : `export_tracking_trace(...)` avec les séries stockées + `Sun_positions_complete.sp_*` pour le jour `JOUR_TRACE`.
6. l.284 : label de `save_simulation` incluant le nom de la stratégie.

### 8. `pase/DATA_MANAGEMENT/simulation_results.py` — extension rétro-compatible

`save_simulation(label, production, agro_results, pilotage=None)` : ajoute au pickle `{'pilotage': {strategy_name, tilt_per_year, mode_per_year}}`. `load_simulation` / `compare_simulations.py` inchangés (accès `.get`).

## Points de vigilance (vérifiés à l'implémentation)

- Shading factors (`production.py:336+`) : masques par signe du tilt → OK avec séries mixtes ; à |tilt|→90°, `cos_teta`→0 → direct nul (cohérent anti-tracking).
- `get_ground_coverage_ratio` : `cos(90°)=0` → GHI au sol maximal, cohérent.
- Géométrie `Hinge: Center` à ±90° : vérifier que le panneau ne traverse pas le sol (warning du contrôleur).

## Ordre de travail

1 (pilotage.py) → 4 (YAML MaxTiltAngle) → 5 (production.py) → 6 (configuration.py) → 2 (stratégies YAML) → 3 (trace) → 7-8 (câblage + sauvegarde) → vérification.

## Vérification

1. **Test unitaire sans simulation** (script scratchpad) : contrôleur seul sur des positions solaires de Gembloux — (a) tracking : tilt négatif matin / positif après-midi, ≈ true_angle hors backtracking ; (b) anti-tracking : `|tilt - true_angle| == 90°` exactement ; (c) avec MaxTiltAngle=60 : `|tilt| ≤ 60` partout.
2. **Run 1 an** : `python example_tracking_hugo.py` (2020-2020 déjà configuré ; passer temporairement `PrecisionLevelOnSunPosition: 1` pour accélérer).
3. **Contrôle de la trace** : ouvrir le PNG du 15/06 et le CSV — mode et tilt conformes au planning (anti-tracking en avril = true_angle ∓ 90°, tracking 11h-14h en été).
4. **Non-régression** : run `strategie_tracking_pur.yaml` + MaxTiltAngle=90 vs run de référence actuel — seul écart attendu : le bugfix zéro→clamp (à quantifier).
5. **Comparaison** : `save_simulation` de 2 stratégies puis `python compare_simulations.py`.
