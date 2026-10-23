# Migration du système de pilotage vers PASE 2.0

*Journal de la transition d'environnement : passage du travail de pilotage
(développé sur une version locale plus ancienne de PASE) vers **PASE 2.0**
(sorti le 2026-07-22). Document de reprise — état au 2026-07-23.*

---

## 1. Objectif

Le système de pilotage (tracking / anti-tracking / mixte + outillage de comparaison)
avait été développé sur une version locale de PASE (branche `develop`, antérieure à
la 2.0). PASE 2.0 apporte de gros changements (Python 3.12, nouveaux modèles de ciel,
refactors, corrections d'irradiance…). Objectif : **porter proprement tout le pilotage
sur 2.0** pour que le travail soit à jour et reprenable.

## 2. État de départ (diagnostic git)

- Le dossier `pase_pilotage` est un **clone du dépôt officiel PASE**
  (`origin = https://gitlab.uliege.be/deal-public/pase.git`), sur `develop` au commit
  `4e753e7` (antérieur à la 2.0 ; tags locaux jusqu'à v1.3.0 seulement).
- Le travail de pilotage était **entièrement non commité** (working tree) :
  - **~29 fichiers NOUVEAUX** (le gros du travail) ;
  - **seulement 3 fichiers PASE existants modifiés** : `configuration.py`,
    `production.py`, `light.py`.

## 3. Stratégie retenue

- **Même clone**, migration via une **branche créée depuis le tag `v2.0.0`**.
- Niveau visé : **version propre et reprenable** (tests qui passent, code balisé, docs).

## 4. Branches git créées

| Branche | Rôle | Commit |
|---|---|---|
| `feature/pilotage` | **Sauvegarde** du travail sur l'ANCIENNE version de PASE (état de départ figé) | `18bd1ad` |
| `pilotage-sur-2.0` | **Branche de travail** : PASE 2.0 (depuis `v2.0.0`) + pilotage réintégré | `ae9f354` |

> ⚠️ Rien n'est perdu : `feature/pilotage` conserve l'intégralité du travail original.
> `git switch feature/pilotage` pour y revenir.

## 5. Nouvel environnement Python

PASE 2.0 impose **Python 3.12** (l'ancien env `pase3` en 3.10 ne convient plus).

```bash
conda create -n pase20 python=3.12 pip -y
conda activate pase20
pip install -e .          # install editable depuis le clone (packaging pyproject 2.0)
```

Binaire python : `/opt/homebrew/Caskroom/miniforge/base/envs/pase20/bin/python`

Versions installées (nettement plus récentes qu'avant) : **PASE 2.0.1.dev**, python 3.12,
**numpy 2.5**, **pandas 3.0**, scipy 1.18, pvlib 0.15, **pyvista 0.48 / vtk 9.6**,
trimesh 4.12, embreex 4.4, matplotlib 3.11.

## 6. Diagnostic des 3 fichiers hooks (base → v2.0.0)

Résultat **très favorable** :

| Fichier | Changé en 2.0 ? | Décision |
|---|---|---|
| `production.py` | **Non — 0 ligne de diff** | Version hookée déposée **telle quelle** (drop-in) |
| `configuration.py` | Refactoré (classe parente), mais **sous-classe tracking + points d'accroche préservés** | Hooks **réappliqués** (contexte identique) |
| `light.py` | Modéré | Modif **NON portée** (voir ci-dessous) |

**`light.py` volontairement non porté** : la modif locale n'était pas du pilotage, mais
une **parallélisation joblib du calcul du diffus** (`_sky_contrib_worker`, marquée
`MODIF PERF`), indépendante et dans une zone refactorée en 2.0. On garde le `light.py`
de 2.0. Conséquence : le multiprocessing **par stratégie** de l'orchestrateur fonctionne
toujours (il parallélise les stratégies entre elles) ; on perd juste un petit gain sur le
diffus *à l'intérieur* d'une stratégie, re-portable plus tard si besoin.

## 7. Ce qui a été porté et comment

**Fichiers NOUVEAUX (copiés depuis `feature/pilotage`)** :
`pase/PHOTOVOLTAICS/pilotage.py`, les 5 modules de `pase/DATA_MANAGEMENT/plots/`
(tracking_trace, pv_energy_integral, biomass_integral, plot_comparison_graphs,
scene_screenshot), `pase/DATA_MANAGEMENT/simulation_report.py` et `simulation_results.py`,
`run_comparaison_pilotage.py`, `example_tracking_hugo.py`, `compare_simulations.py`,
`tests/PHOTOVOLTAICS/test_pilotage_*.py`, `INPUTS/PILOTAGE/*.yaml`, `NOTES/`.

**Hooks réappliqués sur les fichiers 2.0** :
- `configuration.py` : 2 blocs `[HUGO - PILOTAGE]` dans `PV_Configuration_3D.__init__`
  (extraction des kwargs `pilotage_controller`/`sun_datetimes` + délégation du calcul d'angles).
- `production.py` : 4 blocs `[HUGO - PILOTAGE]` + 2 signatures balisées en inline
  (`__init__(..., pilotage_controller=None)` et `get_tiltY_along_time(..., datetimes=None)`).

## 8. Traçabilité — toutes les modifications sont balisées

- **Fichiers PASE 2.0 existants modifiés : seulement 2** — `configuration.py` (4 marqueurs)
  et `production.py` (10 marqueurs). **100 % des lignes de code ajoutées** y sont encadrées
  par des blocs `# ===== [HUGO - PILOTAGE] DEBUT/FIN =====`, ou balisées en commentaire inline
  pour les 2 lignes `def` (qu'on ne peut pas encadrer par des blocs).
- Tous les autres fichiers du pilotage sont **entièrement nouveaux** (le fichier complet est
  du pilotage, avec un marqueur en tête).
- `.gitignore` : ajout d'une règle `.DS_Store` (hygiène, pas une modif de code pilotage).
- **Retrouver tout instantanément** : `grep -rn "HUGO - PILOTAGE" .` (18 fichiers).

## 9. Pièges rencontrés et résolus

- **`.DS_Store`** (macOS) : ajoutés au `.gitignore` pour ne pas polluer les commits.
- **`save_csv.py` disparu du working tree** au changement de branche : classique **conflit de
  casse macOS** sur `pase/DATA_MANAGEMENT/OUTPUT/` (cf. #213 du changelog 2.0). Fichier 2.0
  restauré (`git checkout v2.0.0 -- .../save_csv.py`) — **ne jamais committer sa suppression**.
- **Test unitaire obsolète** : `test_pilotage_unitaire.py` chargeait
  `strategie_antitrack_printemps.yaml` en s'attendant à l'ancienne version à 3 règles ; ce
  fichier a été scindé depuis. Corrigé : la stratégie de test est désormais définie **en dur**
  dans le test (indépendante des YAML éditables) + chemins dérivés de `__file__` (portable).

## 10. État actuel — MIGRATION FONCTIONNELLE ✅

Tout est validé sur PASE 2.0 (python 3.12, pandas 3.0, numpy 2.5, pyvista 0.48, matplotlib 3.11) :

- ✅ Env `pase20` monté, **PASE 2.0 s'importe**.
- ✅ Cœur du pilotage porté (hooks + fichiers), **balisé à 100 %**.
- ✅ **Test unitaire : 22/22** ; **Test d'intégration : 8/8** (dont **non-régression 0.000 %**
  entre tracking pur via contrôleur et pipeline historique).
- ✅ **Smoke test** du pipeline complet (1 stratégie) : 2.25 MWh.
- ✅ **Orchestrateur de comparaison COMPLET** (`run_comparaison_pilotage.py`) : 4 stratégies en
  **multiprocessing** (25,7 s), **tous** les graphes (matplotlib 3.11), **toutes** les images 3D
  (pyvista 0.48, off-screen), docs md/pdf/avis/performance générés **sans aucune erreur**.
- ✅ Commité sur `pilotage-sur-2.0`.

> **Bonne surprise** : l'API du pipeline (OutputsManager, Light, Ray_casting_scene, PV_Production,
> run_crop_simu, set_interest_zone_orientation…) est **quasi inchangée** entre l'ancienne version
> et 2.0 — l'adaptation s'est donc réduite aux INPUTS. Les changements 2.0 (zone qui tourne avec
> l'azimut #48, ciel Perez #117, échantillonnage météo #193) sont gérés **en interne**, sans
> changer les appels.

### Comment relancer
```bash
conda activate pase20
PY=/opt/homebrew/Caskroom/miniforge/base/envs/pase20/bin/python
$PY tests/PHOTOVOLTAICS/test_pilotage_unitaire.py        # 22/22
$PY tests/PHOTOVOLTAICS/test_pilotage_integration.py     # 8/8
$PY run_comparaison_pilotage.py                          # run de comparaison complet
```

## 11. Points d'attention / finitions optionnelles

- ⚠️ **Les résultats de BIOMASSE changent** vs l'ancienne version (l'énergie PV, elle, est
  identique). Normal : 2.0 corrige plusieurs bugs d'irradiance (diffus trop bas, GHI au sol,
  horizon sur le diffus, shading factor, orientation de la zone…) qui affectent la lumière au sol
  → la culture. C'est **plus juste** : re-générer les comparaisons sur 2.0 et les traiter comme la
  **nouvelle référence**.
- **INPUTS** : on est parti des exemples 2.0 (`Example1_loc`, `Example1_PV_Module`,
  `simple_example`) + `Example2_tracking_AV_hugo.yaml` (= exemple 2.0 + `MaxTiltAngle`). Adapter
  ces choix / valeurs de parc au besoin de l'étude.
- **Optionnel** : re-porter la parallélisation joblib du diffus (`light.py`, laissée de côté) sur
  le diffus refactoré de 2.0, si on veut accélérer le calcul *à l'intérieur* d'une stratégie.

## 12. STICS (via pySTICS) sur PASE 2.0 — ✅ FONCTIONNE

PASE 2.0 intègre le modèle de culture **STICS via pySTICS** (réimplémentation Python,
`CropModel: pystics`) — plus besoin de Java. **Validé** : run complet du blé d'hiver 2006 →
`Dry_yield ≈ 6 t/ha`, `Total_ET ≈ 865 mm` (valeurs réalistes, avec variation spatiale due à
l'ombrage des panneaux).

### Recette complète (à refaire dans un nouvel env)

**1. Sous-module + dépendances** (le `pyproject` de pySTICS est cassé → on installe à la main) :
```bash
git submodule update --init pase/CROPS/STICS/PYSTICS/pySTICS
$PY -m pip install unidecode xmltodict "setuptools<81" "pandas>=2.2,<3"
```
- `setuptools<81` : `pkg_resources` a été retiré au-delà (pySTICS l'utilise).
- **`pandas<3` (IMPORTANT)** : pySTICS n'est **pas compatible pandas 3.0** (il affecte des floats
  dans des colonnes int, refusé en 3.0). pandas 2.3 marche pour pySTICS **ET** le pilotage
  (tests 22/22 revalidés en 2.3). → **l'env STICS tourne sur pandas 2.3.**

**2. Rendre `pystics` importable** : c'est un package "namespace" (sans `__init__.py`) → ajouter
`pase/CROPS/STICS/PYSTICS/pySTICS` au `sys.path` (ou `PYTHONPATH`). L'install `pip -e` échoue
(pyproject en layout `src/` alors que le package est à plat).

**3. Corrections apportées (2 bugs upstream, à remonter)** :
- `INPUTS/CROPS/config/pystics_example.yml` : `Possibilities` était une chaîne → mis en **liste
  YAML** (sinon rejeté par la validation stricte 2.0). *(commité)*
- `pase/CROPS/STICS/PYSTICS/run_pystics_from_PASE.py` : la météo par position était **écrite**
  dans `parametrization_files/example/` mais **relue** dans `.../pase/` → `FileNotFoundError`.
  Corrigé (écriture dans `pase/`), balisé `[HUGO - FIX STICS]`. *(commité)*

**4. Blé d'hiver = bisannuel** : `simu_init.yaml` a `AnnualCropOption: 0` et `BeginDate 240 /
EndDate 700` (jour 240 → jour 700 = **2 ans**). Il faut donc simuler **2 années consécutives**,
avec une météo **horaire (PVGIS)** ET **journalière (PRECIP/VP)** couvrant **les deux**. La 1ère
année (semis) est sautée → résultats sous la 2ème année.

**5. Combinaison de données qui marche** (horaire en cache + journalier cohérent) :
```
Latitude=50.376, Longitude=5.677 (Werbomont), Années 2005-2006
DailyWeatherFileName = 'PRECIP_VP_Loc1'   # couvre 2005-2015
```
> ⚠️ `PRECIP_VP_Loc1.csv` couvre **2005-2015** (pas 2019-2020). Pour d'autres années, fournir un
> fichier météo journalière (précipitations + pression de vapeur, format Agri4Cast) couvrant la
> période **et** disposer de l'horaire PVGIS correspondant.

**6. Coût** : pySTICS simule chaque point du sol (~4-5 s/point). Une zone de 128 points ≈ 9 min ;
réduire la zone d'intérêt pour des essais rapides.

### Pour comparer des pilotages AVEC pySTICS
Pointer la config crop de `run_comparaison_pilotage.py` sur `pystics_example.yml`, et régler
loc/années sur une période bisannuelle valide (ex. Werbomont 2005-2006). Le reste du pipeline
(pilotage, multiprocessing, graphes) est inchangé — seul le modèle de culture change.

## 12. Commandes utiles pour reprendre

```bash
cd /Users/hugolange/Desktop/pase_pilotage
git switch pilotage-sur-2.0                    # branche de travail 2.0
conda activate pase20                          # env Python 3.12
PY=/opt/homebrew/Caskroom/miniforge/base/envs/pase20/bin/python

$PY tests/PHOTOVOLTAICS/test_pilotage_unitaire.py     # doit afficher 22/22 OK
grep -rn "HUGO - PILOTAGE" .                           # retrouver toutes les modifs

git switch feature/pilotage                    # revenir a la sauvegarde (ancienne version)
```
