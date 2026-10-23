#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ============== [HUGO - PILOTAGE] FICHIER ENTIEREMENT NOUVEAU ==============
#
# ORCHESTRATEUR DE COMPARAISON DE POLITIQUES DE PILOTAGE (+ MULTIPROCESSING)
# =========================================================================
#
# Lance UNE simulation complete comparant PLUSIEURS politiques de pilotage
# (tracking / anti-tracking / mixte...) sur LE MEME parc agrivoltaique, LA MEME
# annee et LA MEME meteo. Produit une arborescence de sortie auto-numerotee :
#
#   OUTPUTS/COMPARAISONS_PILOTAGE/SIMU_<N>_<mots-cles>/
#     ├── INFOS_SIMULATION.md / .pdf   <- fiche descriptive des inputs
#     ├── AVIS_SIMULATION.txt          <- fichier a remplir pour donner ton avis
#     ├── PERFORMANCE.txt              <- durees + strategie d'execution (perf)
#     ├── structure_parc.png           <- vue 3D du parc
#     ├── 1 - graphiques de comparaison/
#     ├── 2 - graphiques par pilotage/
#     ├── 3 - csv trace tracking/
#     └── 4 - fichiers pkl/
#
# PERFORMANCE : les politiques de pilotage sont INDEPENDANTES -> elles sont
# calculees EN PARALLELE (multiprocessing), une par coeur CPU. Sur une machine a
# N coeurs et K strategies, le temps passe de ~K*T a ~ceil(K/N)*T. Activable /
# desactivable via le flag MULTIPROCESSING ci-dessous.
#
# ---------------------------------------------------------------------------
# POUR LANCER (env conda pase3, depuis la racine du repo) :
#   /opt/homebrew/Caskroom/miniforge/base/envs/pase3/bin/python run_comparaison_pilotage.py
# ---------------------------------------------------------------------------

import os

# ============== [HUGO - PILOTAGE] DEBUT AJOUT (PERF) ==============
# Limiter les threads bas-niveau (BLAS/OpenMP) A 1 PAR PROCESSUS. Indispensable
# des qu'on parallelise : sinon chaque processus numpy lancerait ~18 threads BLAS
# -> explosion du nombre de threads et sur-souscription. On laisse le parallelisme
# se faire au niveau processus (workers + joblib), pas au niveau thread BLAS.
# NB : doit etre defini AVANT l'import de numpy (fait transitivement plus bas).
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============

import copy
import time

import pandas as pd

# ===========================================================================
#  >>>>>>>>>>>>>>  PARAMETRES A MODIFIER PAR L'UTILISATEUR  <<<<<<<<<<<<<<<<<
# ===========================================================================

# --- Politiques de pilotage a comparer (fichiers YAML de INPUTS/PILOTAGE/) ---
STRATEGIES = [
    os.path.join('INPUTS', 'PILOTAGE', 'strategie_tracking_pur.yaml'),
    os.path.join('INPUTS', 'PILOTAGE', 'strategie_antitrack_pur.yaml'),
    os.path.join('INPUTS', 'PILOTAGE', 'strategie_antitrack_printemps.yaml'),
    os.path.join('INPUTS', 'PILOTAGE', 'strategie_antitrack_printemps_et_track_midi_ete.yaml'),
]

# --- Fichiers d'inputs du parc (identiques pour toutes les strategies) ---
# NB (PASE 2.0) : on part des exemples 2.0 (validation YAML stricte). Le seul fichier
# specifique au pilotage est le YAML AV (copie de l'exemple 2.0 + MaxTiltAngle).
# Config active : modele de culture SIMPLE, Werbomont 2005-2006, petite zone (~30 s).
# Autre lieu pret a l'emploi : FICHIER_LOC = 'Example1_loc.yaml' (Gembloux 2020).
# Pour pySTICS (ble d'hiver) : FICHIER_CROP = 'pystics_example.yml', UNITE_CROP = 't/ha',
# MULTIPROCESSING = False (voir NOTES/MIGRATION_PASE_2.0.md).
FICHIER_LOC       = 'pystics_loc.yaml'                # SCENARIOS/ (Werbomont 2005-2006, zone reduite)
FICHIER_AV        = 'Example2_tracking_AV_hugo.yaml'  # AV_CENTRAL/ (exemple 2.0 + MaxTiltAngle)
FICHIER_PV_MODULE = 'Example1_PV_Module.yaml'         # HARDWARE/PV_MODULES/ (exemple 2.0)
FICHIER_CROP      = 'simple_example.yml'              # CROPS/config/ (modele SIMPLE)

# --- Variable de culture pour les graphiques de comparaison ---
# ATTENTION A L'UNITE : elle depend du MODELE DE CULTURE, pas seulement du nom
# de la variable. Dans SIMPLE, Dry_yield = Biomass * HI (simple.py) -> g/m².
# Dans pySTICS, Dry_yield vient de mafruit -> t/ha. Mettre 't/ha' sur une sortie
# SIMPLE mele les deux et fausse les figures d'un facteur 100.
#   SIMPLE  -> 'Biomass' (g/m²) ou 'Dry_yield' (g/m²)
#   pySTICS -> 'Dry_yield' (t/ha) ou 'Total_ET' (mm)
VARIABLE_CROP = 'Dry_yield'
UNITE_CROP    = 'g/m²'          # <- config SIMPLE active ci-dessus

# --- Jours a tracer sur les figures de verification du pilotage ---
# Format : (jour 'MM-DD', mot-cle). PAS d'annee -> l'annee de la simulation est
# ajoutee automatiquement, donc changer d'annee ne provoque aucune erreur.
JOURS_TRACE = [
    ('02-15', 'hiver'),
    ('05-01', 'printemps'),
    ('07-15', 'ete'),
    ('10-15', 'automne'),
]

# --- Mots-cles du dossier SIMU_<N>_<mots-cles> (laisser '' pour auto) ---
MOTS_CLES = ''

# --- Ou ranger les dossiers de comparaison ---
BASE_DIR = os.path.join('OUTPUTS', 'COMPARAISONS_PILOTAGE')

# ---------------------------- PERFORMANCE ----------------------------------
# Calculer les strategies EN PARALLELE (True) ou une par une (False) ?
# NB : avec pySTICS, garder False -> pySTICS ecrit dans des fichiers partages
# (parametrization_files/pase/), le parallele provoquerait des collisions entre workers.
MULTIPROCESSING = False
# Nombre de processus paralleles. None -> automatique = min(nb strategies, nb coeurs).
# Reduire si la RAM sature (chaque worker garde meteo + maillages en memoire).
N_WORKERS = None
# Generer les images 3D (structure du parc + carte de biomasse) ? Un peu couteux
# (rendu PyVista) : mettre False pour aller au plus vite sur de gros parcs.
GENERER_IMAGES_3D = True

# ===========================================================================
#  >>>>>>>>>>>>>>  FIN DES PARAMETRES  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ===========================================================================


# ---------------------------------------------------------------------------
#  IMPORTS (au niveau module : necessaires aussi dans les workers 'spawn')
# ---------------------------------------------------------------------------
from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import (YAML_Inputs_provider,
                                                       Inputs_aggregator)
from pase.DATA_MANAGEMENT.input_checker import InputsEvaluator
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        get_cache_key,
                                                        Weather_data)
from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.PHOTOVOLTAICS.pilotage import PilotageStrategy, TrackingController
from pase.CROPS.run_crop_simulations import run_crop_simu

from pase.DATA_MANAGEMENT.simulation_results import save_simulation
from pase.DATA_MANAGEMENT.simulation_report import (creer_arborescence_simu,
                                                    mots_cles_auto,
                                                    infos_strategies,
                                                    ecrire_description_inputs,
                                                    ecrire_description_pdf,
                                                    ecrire_template_avis,
                                                    ecrire_performance)
from pase.DATA_MANAGEMENT.plots.scene_screenshot import (save_park_structure,
                                                         save_variable_map,
                                                         derniere_date_variable)
from pase.DATA_MANAGEMENT.plots.pv_energy_integral import plot_pv_energy_integral
from pase.DATA_MANAGEMENT.plots.biomass_integral import plot_biomass_integral
from pase.DATA_MANAGEMENT.plots.tracking_trace import export_tracking_trace
from pase.DATA_MANAGEMENT.plots.plot_comparison_graphs import (plot_comparison_overlay,
                                                               plot_comparison_grid,
                                                               plot_comparison_bars,
                                                               plot_comparison_combined,
                                                               plot_comparison_tracking_grid,
                                                               plot_comparison_ranking,
                                                               _biomass_curve,
                                                               _crop_array_at_year,
                                                               _crop_final_mean)
import matplotlib
matplotlib.use('Agg', force=True)   # jamais de fenetre interactive en mode batch


# ===========================================================================
#  PIPELINE D'UNE STRATEGIE  (fonction top-level -> executable en parallele)
# ===========================================================================
def run_one_strategy(task):
    """Execute TOUT le pipeline PASE pour UNE politique de pilotage et sauvegarde
    ses sorties (graphes, traces, images, pkl). Retourne les donnees necessaires
    aux graphes de comparaison. Concu pour tourner dans un process isole.
    """
    import matplotlib
    matplotlib.use('Agg', force=True)   # securite : aucune fenetre dans le worker

    # ============== [HUGO - PILOTAGE] PERF ==============
    # Cap du parallelisme INTERNE de PASE (joblib n_jobs=-1 dans le calcul du
    # diffus, light.py). En mode parallele, chaque worker n'a droit qu'a une part
    # des coeurs -> evite la sur-souscription (workers x joblib). loky lit cette
    # variable pour dimensionner son pool.
    os.environ['LOKY_MAX_CPU_COUNT'] = str(task.get('inner_jobs', 1))

    t0 = time.time()
    Loc = task['Loc']; AV = task['AV']; PV_params = task['PV_params']
    crop_config = task['crop_config']
    nom = task['nom']; chemin_yaml = task['chemin_yaml']
    var, unite = task['VARIABLE_CROP'], task['UNITE_CROP']
    dossier_simu = task['dossier_simu']
    print(f'  [worker] {nom} : demarrage...', flush=True)

    strat = PilotageStrategy.from_yaml(chemin_yaml)
    controller = TrackingController.from_inputs(strat, PV_params)

    # --- meteo / soleil / zone / lumiere reconstruits a neuf (process isole) ---
    WD = Weather_data(Loc['Latitude'], Loc['Longitude'],
                      Loc['SimulationStartingYear'], Loc['SimulationEndingYear'],
                      Loc['WeatherDataOption'], copy.deepcopy(task['raw_weather']),
                      Loc['WeatherFileName'], Loc['DailyWeatherFileName'])
    n_steps = len(WD.nyears_data[str(Loc['SimulationStartingYear'])])
    Sun_samp = Sun_positions_sampled(Loc['Latitude'], Loc['Longitude'],
                                     Loc['PrecisionLevelOnSunPosition'],
                                     Loc['LocationName'], n_steps, Loc['TimeZone'])
    Sun_complete = Sun_positions(Loc['Latitude'], Loc['Longitude'], n_steps, Loc['TimeZone'])
    M = Mesh(); M.set_interest_zone_orientation(Loc, AV)
    M.add_oriented_plane_ground_mesh(
        Loc['Xmin_InterestZone'], Loc['Xmax_InterestZone'],
        Loc['Ymin_InterestZone'], Loc['Ymax_InterestZone'],
        Loc['dX_InterestZone'], Loc['dY_InterestZone'], flag='crop')
    Light_instance = Light(WD.nyears_data, Sun_complete)
    discrete_sky = ReinhartSky(MF=Loc['MF']).reinhart_patches

    # --- geometrie 3D + ray casting (la partie la plus couteuse) ---
    PV_3D = PV_Configuration_3D(PV_params, Sun_samp.solar_vector, visualization=False,
                                pilotage_controller=controller,
                                sun_datetimes=Sun_samp.SP.index)
    L = Ray_casting_scene(mesh=M, geometry=PV_3D.PV_central_PD, discrete_sky=discrete_sky)
    L.get_light_maps(Sun_samp.solar_vector, visualization=False)
    L.get_daily_irradiation_map(Sun_samp.SP, Light_instance.data, visualization=False)

    # --- production electrique ---
    PV_central = PV_Production(PV_params, pilotage_controller=controller)
    PV_central.get_several_years_of_electricity_production(
        Sun_complete, Light_instance.data, WD.nyears_data)
    energie_totale = sum(PV_central.production[y]['P_central'].sum()
                         for y in PV_central.production)

    # --- modele de culture ---
    agro_results = run_crop_simu(crop_config, task['option_2D'], WD.nyears_daily_data,
                                 L.daily_irr_spat, Loc)

    # --- series concatenees (bandes de mode + grid tracking) ---
    annees = sorted(PV_central.production.keys())
    mode_all = (pd.concat([PV_central.mode_per_year[y] for y in annees])
                if PV_central.mode_per_year else None)
    tilt_all = pd.concat([PV_central.tiltY_per_year[y] for y in annees])
    true_all = (pd.concat([PV_central.true_angle_per_year[y] for y in annees])
                if PV_central.true_angle_per_year else None)
    elev_all = pd.concat([
        pd.Series((Sun_complete.sp_leapY if int(y) % 4 == 0
                   else Sun_complete.sp_nonleapY)['elevation'].to_numpy(),
                  index=WD.nyears_data[y].index) for y in annees])
    trace_df = pd.DataFrame({'tilt': tilt_all, 'true': true_all,
                             'mode': mode_all, 'elev': elev_all})

    # --- graphiques PAR pilotage (dossier 2) ---
    plot_pv_energy_integral(PV_central.production, mode_series=mode_all,
                            save_path=os.path.join(dossier_simu, 'pv_energy_integral.png'))
    plot_biomass_integral(agro_results, variable=var, unit=unite, mode_series=mode_all,
                          save_path=os.path.join(dossier_simu, 'biomass_integral.png'))

    # --- images 3D (optionnelles) ---
    if task['generer_images']:
        if task['save_structure']:
            save_park_structure(PV_3D.PV_central_PD,
                                os.path.join(task['root'], 'structure_parc.png'))
        # Carte de repartition spatiale de la biomasse : la biomasse s'ACCUMULE sur
        # la saison, donc la valeur de fin de saison a chaque point = biomasse totale
        # produite sur l'annee a cet endroit. vue='defaut' -> meme cadrage auto que
        # la fenetre interactive visualize_map (pas de zoom force).
        # Valeur finale par point, gere SIMPLE (derniere date) ET pySTICS (ndarray).
        # On prend l'annee qui contient la variable (pySTICS = 2eme annee, 1ere sautee).
        _vals_carte = None
        for _y in sorted(agro_results.keys()):
            _kind, _arr = _crop_array_at_year(agro_results, var, _y)
            if _kind != 'none':
                _vals_carte = _arr
        if _vals_carte is not None:
            save_variable_map(M.sourcepoints, _vals_carte,
                              PV_3D.PV_central_PD,
                              os.path.join(dossier_simu, 'carte_biomasse_annuelle.png'),
                              titre=f"{var} cumulee sur l'annee [{unite}] — {nom}")

    # --- traces de verification : CSV (dossier 3) + figures (dossier 2) ---
    for year in PV_central.tiltY_per_year:
        sp = (Sun_complete.sp_leapY if int(year) % 4 == 0 else Sun_complete.sp_nonleapY)
        jours_annee = [(f'{year}-{mmdd}', lab) for (mmdd, lab) in task['JOURS_TRACE']]
        export_tracking_trace(
            tilt_series=PV_central.tiltY_per_year[year],
            mode_series=PV_central.mode_per_year.get(year),
            true_angle_series=PV_central.true_angle_per_year.get(year),
            sun_positions_df=sp, label=f'{nom}_{year}', day=jours_annee,
            max_tilt_deg=controller.max_tilt_deg,
            csv_dir=task['csv_trace_dir'], fig_dir=dossier_simu)

    # --- sauvegarde pkl (dossier 4) ---
    save_simulation(nom, PV_central.production, agro_results, output_dir=task['pkl_dir'],
                    pilotage={'strategy_name': nom, 'strategy_file': chemin_yaml,
                              'tilt_per_year': PV_central.tiltY_per_year,
                              'mode_per_year': PV_central.mode_per_year,
                              'true_angle_per_year': PV_central.true_angle_per_year})

    # ============== [HUGO - PILOTAGE] PERF ==============
    # PASE parallelise le calcul du diffus avec joblib/loky, qui garde son pool de
    # processus VIVANT (timeout ~300s) apres usage. Dans un worker d'un pool externe,
    # ce pool "fantome" empeche le worker de se terminer -> deadlock a l'arret.
    # On force donc l'arret du pool loky avant de rendre la main.
    try:
        from joblib.externals.loky import get_reusable_executor
        get_reusable_executor().shutdown(wait=True)
    except Exception:
        pass

    duree = time.time() - t0
    print(f'  [worker] {nom} : termine en {duree:.1f}s (energie {energie_totale:.2f} MWh)', flush=True)
    res = {'label': nom, 'production': PV_central.production, 'agro_results': agro_results,
           'modes': PV_central.mode_per_year, 'tilt_all': tilt_all, 'true_all': true_all,
           'trace_df': trace_df, 'energie': energie_totale, 'duree': duree}
    if task['save_structure']:
        res['n_positions_soleil'] = len(Sun_samp.SP)
        res['n_points_zone'] = len(M.sourcepoints)
    return res


# ===========================================================================
#  ORCHESTRATION
# ===========================================================================
def main():
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp

    t_start = time.time()
    PASE_Logger()

    # --- 1) inputs ---
    print('\n=== 1) Chargement des inputs (parc commun a toutes les strategies) ===')
    Loc_1 = YAML_Inputs_provider(file=FICHIER_LOC, subpath='SCENARIOS').inputs
    AV_1 = YAML_Inputs_provider(file=FICHIER_AV, subpath='AV_CENTRAL').inputs
    PV_module_1 = YAML_Inputs_provider(
        file=FICHIER_PV_MODULE, subpath=os.path.join('HARDWARE', 'PV_MODULES')).inputs
    crop_config = YAML_Inputs_provider(
        file=FICHIER_CROP, subpath=os.path.join('CROPS', 'config')).inputs
    InputsEvaluator(Loc_1, AV_1)
    PV_params_dict = Inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs

    strategies_infos = infos_strategies(STRATEGIES)
    noms_pilotages = [s['name'] for s in strategies_infos]

    # garde-fou : noms de strategies uniques (sinon ecrasement silencieux)
    _vus = {}
    for s in strategies_infos:
        _vus.setdefault(s['name'], []).append(s['fichier'])
    _doublons = {n: f for n, f in _vus.items() if len(f) > 1}
    if _doublons:
        lignes = [f"    name '{n}' partage par : {', '.join(fs)}" for n, fs in _doublons.items()]
        raise ValueError(
            "[PILOTAGE] Des strategies ont le meme champ 'name:' (elles s'ecraseraient) :\n"
            + '\n'.join(lignes)
            + "\n  -> Corrige le champ 'name:' dans ces fichiers YAML pour qu'il soit unique.")
    print(f'  {len(strategies_infos)} politiques de pilotage : {", ".join(noms_pilotages)}')

    # --- 2) arborescence ---
    mots = MOTS_CLES or mots_cles_auto(Loc_1, PV_params_dict, strategies_infos,
                                       crop_config=crop_config)
    chemins = creer_arborescence_simu(BASE_DIR, mots, noms_pilotages)
    simu_nom = os.path.basename(chemins['root'])
    print(f'\n=== 2) Dossier de simulation : {simu_nom} ===')

    # --- 3) pre-processing partage : variant + meteo brute (cache) ---
    print('\n=== 3) Pre-processing partage (meteo brute) ===')
    om = OutputsManager(Loc_1['LocationName'], Loc_1['SimulationStartingYear'],
                        Loc_1['SimulationEndingYear'])
    om.setup_variant(loc=Loc_1, av=AV_1, pv_module=PV_module_1,
                     structure=dict(), crop_config=crop_config, source=__file__)
    cache_key = get_cache_key(Loc_1['Latitude'], Loc_1['Longitude'],
                              Loc_1['SimulationStartingYear'], Loc_1['SimulationEndingYear'])
    if Loc_1['WeatherDataOption'] == 1:
        raw_weather = om.load_or_fetch_weather(
            key=cache_key,
            fetch_fn=lambda: fetch_weather_from_pvgis(
                Loc_1['Latitude'], Loc_1['Longitude'],
                Loc_1['SimulationStartingYear'], Loc_1['SimulationEndingYear']))
    else:
        raw_weather = None
    duree_preproc = time.time() - t_start

    # --- repartition des coeurs : workers (externe) x joblib PASE (interne) ---
    n_cpu = os.cpu_count() or 1
    n_strat = len(STRATEGIES)
    if MULTIPROCESSING and n_strat > 1:
        execution = 'MULTIPROCESSING'
        n_workers = min(N_WORKERS or min(n_strat, n_cpu), n_strat)
        # chaque worker recoit une part equitable des coeurs pour son joblib interne
        inner_jobs = max(1, n_cpu // n_workers)
    else:
        execution, n_workers = 'SEQUENTIELLE', 1
        inner_jobs = n_cpu   # un seul run a la fois -> joblib interne prend tous les coeurs

    # --- construction des taches (une par strategie) ---
    option_2D = 1
    tasks = []
    for i, (chemin_yaml, s_info) in enumerate(zip(STRATEGIES, strategies_infos)):
        nom = s_info['name']
        tasks.append({
            'nom': nom, 'chemin_yaml': chemin_yaml,
            'Loc': Loc_1, 'AV': AV_1, 'PV_params': PV_params_dict, 'crop_config': crop_config,
            'raw_weather': raw_weather,
            'JOURS_TRACE': JOURS_TRACE, 'VARIABLE_CROP': VARIABLE_CROP, 'UNITE_CROP': UNITE_CROP,
            'option_2D': option_2D, 'inner_jobs': inner_jobs,
            'dossier_simu': chemins['par_pilotage_dirs'][nom],
            'csv_trace_dir': chemins['csv_trace'], 'pkl_dir': chemins['pkl'],
            'root': chemins['root'],
            'save_structure': (i == 0),   # la 1re tache capture l'image du parc
            'generer_images': GENERER_IMAGES_3D,
        })

    # --- 4) calcul des strategies (parallele ou sequentiel) ---
    if execution == 'MULTIPROCESSING':
        print(f'\n=== 4) Calcul des {n_strat} strategies EN PARALLELE '
              f'({n_workers} workers x {inner_jobs} coeurs/worker, sur {n_cpu} coeurs) ===')
        ctx = mp.get_context('spawn')   # 'spawn' : workers propres (VTK/Cocoa OK sur macOS)
        with ProcessPoolExecutor(max_workers=n_workers, mp_context=ctx) as ex:
            results = list(ex.map(run_one_strategy, tasks))  # ordre preserve
    else:
        print(f'\n=== 4) Calcul des {n_strat} strategies SEQUENTIELLEMENT ===')
        results = [run_one_strategy(t) for t in tasks]
    t_calcul_fini = time.time()

    # --- assemblage des resultats (ordre = STRATEGIES) ---
    simulations, resultats_avis, durees_strat = [], {}, {}
    perf_extra = {}
    for r in results:
        simulations.append({'label': r['label'], 'production': r['production'],
                            'agro_results': r['agro_results'], 'modes': r['modes'],
                            'tilt_all': r['tilt_all'], 'true_all': r['true_all'],
                            'trace_df': r['trace_df']})
        resultats_avis[r['label']] = {'energie_MWh': r['energie']}
        durees_strat[r['label']] = r['duree']
        if 'n_positions_soleil' in r:
            perf_extra['n_positions_soleil'] = r['n_positions_soleil']
            perf_extra['n_points_zone'] = r['n_points_zone']

    # --- 5) graphiques de comparaison (dossier 1) ---
    print('\n=== 5) Graphiques de comparaison ===')
    d_comp = chemins['comparaison']
    plot_comparison_overlay(simulations, variable=VARIABLE_CROP, unit=UNITE_CROP,
                            save_path=os.path.join(d_comp, 'comparison_overlay.png'))
    plot_comparison_grid(simulations, variable=VARIABLE_CROP, unit=UNITE_CROP,
                         save_path=os.path.join(d_comp, 'comparison_grid.png'))
    plot_comparison_bars(simulations, variable=VARIABLE_CROP, unit=UNITE_CROP,
                         save_path=os.path.join(d_comp, 'comparison_bars.png'))
    plot_comparison_combined(simulations, variable=VARIABLE_CROP, unit=UNITE_CROP,
                             save_path=os.path.join(d_comp, 'comparison_combined.png'))
    plot_comparison_ranking(simulations, variable=VARIABLE_CROP, unit=UNITE_CROP,
                            save_path=os.path.join(d_comp, 'comparison_ranking.png'))

    _an = str(Loc_1['SimulationStartingYear'])
    jours_full = [(f'{_an}-{mmdd}', saison) for (mmdd, saison) in JOURS_TRACE]
    traces_grid = [{'label': s['label'], 'trace_df': s['trace_df']} for s in simulations]
    plot_comparison_tracking_grid(
        traces_grid, jours=jours_full, max_tilt_deg=PV_params_dict.get('MaxTiltAngle', 90),
        save_path=os.path.join(d_comp, 'comparison_tracking_grid.png'))

    # valeur de culture finale par pilotage (SIMPLE ou pySTICS) pour le fichier d'avis
    for sim in simulations:
        dernieres = []
        for y in sim['agro_results']:
            v = _crop_final_mean(sim['agro_results'], VARIABLE_CROP, y)
            if v is not None:
                dernieres.append(v)
        if dernieres:
            resultats_avis[sim['label']]['biomasse_fin'] = sum(dernieres) / len(dernieres)

    # --- 6) documents (fiche inputs + avis + performance) ---
    print('\n=== 6) Generation des documents ===')
    ecrire_description_inputs(os.path.join(chemins['root'], 'INFOS_SIMULATION.md'),
                             Loc_1, AV_1, PV_module_1, crop_config, strategies_infos, simu_nom)
    ecrire_description_pdf(os.path.join(chemins['root'], 'INFOS_SIMULATION.pdf'),
                          Loc_1, AV_1, PV_module_1, crop_config, strategies_infos, simu_nom)
    ecrire_template_avis(os.path.join(chemins['root'], 'AVIS_SIMULATION.txt'),
                        simu_nom, strategies_infos, resultats=resultats_avis)

    duree_totale = time.time() - t_start
    if execution == 'SEQUENTIELLE':
        note_perf = (f'Sequentiel : 1 strategie a la fois, joblib interne (diffus) '
                     f'sur {inner_jobs} coeurs. Threads BLAS/OpenMP = 1/processus.')
    else:
        note_perf = (f'Parallele : {n_workers} workers x {inner_jobs} coeurs/worker (joblib '
                     f'interne). Threads BLAS/OpenMP = 1/processus. Les durees par '
                     f'strategie sont concurrentes ; le TOTAL est le temps reel (wall-clock).')
    ecrire_performance(
        os.path.join(chemins['root'], 'PERFORMANCE.txt'), simu_nom,
        infos={'execution': execution, 'n_workers': n_workers,
               'precision_soleil': Loc_1['PrecisionLevelOnSunPosition'],
               'n_positions_soleil': perf_extra.get('n_positions_soleil'),
               'n_points_zone': perf_extra.get('n_points_zone'),
               'strategies': noms_pilotages,
               'duree_preproc': duree_preproc,
               'durees_par_strategie': durees_strat,
               'duree_graphes': time.time() - t_calcul_fini,
               'duree_totale': duree_totale, 'notes': note_perf})

    print('\n' + '=' * 70)
    print(f'  SIMULATION TERMINEE en {duree_totale:.1f} s ({execution}, {n_workers} worker(s))')
    print(f'  -> {chemins["root"]}')
    print('=' * 70)
    for nom, r in resultats_avis.items():
        e = r.get('energie_MWh'); b = r.get('biomasse_fin')
        b_txt = f'{b:.1f}' if b is not None else '-'
        print(f'  - {nom:<40} energie={e:7.2f} MWh   biomasse_fin={b_txt}')


# 'spawn' re-importe ce module dans chaque worker : la garde __main__ empeche de
# relancer l'orchestration en boucle. INDISPENSABLE pour le multiprocessing.
if __name__ == '__main__':
    main()

# ============== [HUGO - PILOTAGE] FIN DU FICHIER ==============
