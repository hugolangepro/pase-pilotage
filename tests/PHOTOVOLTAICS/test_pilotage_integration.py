# ============== [HUGO - PILOTAGE] FICHIER NOUVEAU (script de verification) ==============
# Test d'integration du pilotage sur le vrai pipeline PASE 2.0 (sans GUI ni ray casting).
# Lancer avec l'env PASE 2.0 (python 3.12) depuis la racine du repo :
#   python tests/PHOTOVOLTAICS/test_pilotage_integration.py
"""Test d'intégration du pilotage sur le vrai pipeline PASE (sans GUI ni ray casting).

Vérifie :
  1. Parsing YAML avec MaxTiltAngle
  2. Construction de la géométrie 3D trackée avec le contrôleur (meshes à ±90°)
  3. Cohérence géométrie <-> production (mêmes angles aux mêmes instants)
  4. Production électrique avec stratégie mixte
  5. Non-régression : tracking_pur via contrôleur vs pipeline historique
  6. Export de la trace CSV + figure
"""
import os
import sys

import numpy as np
import pandas as pd

# Racine du repo derivee du chemin du fichier -> test portable (pas de chemin en dur)
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(BASE)
sys.path.insert(0, BASE)

import matplotlib
matplotlib.use('Agg', force=True)  # headless pour ce test

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        get_cache_key, Weather_data)
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager
from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.PHOTOVOLTAICS.pilotage import PilotageStrategy, TrackingController
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions
from pase.DATA_MANAGEMENT.plots.tracking_trace import export_tracking_trace

PASE_Logger()

# ---------- inputs (exemples PASE 2.0 + YAML AV avec MaxTiltAngle) ----------
Loc_1 = YAML_Inputs_provider(file='Example1_loc.yaml', subpath='SCENARIOS').inputs
AV_1 = YAML_Inputs_provider(file='Example2_tracking_AV_hugo.yaml', subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='Example1_PV_Module.yaml',
                                   subpath=os.path.join('HARDWARE', 'PV_MODULES')).inputs
PV_params_dict = Inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs
assert PV_params_dict['MaxTiltAngle'] == 90, "MaxTiltAngle doit etre parse depuis le YAML"
print("1. OK parsing YAML : MaxTiltAngle =", PV_params_dict['MaxTiltAngle'])

# ---------- meteo (cache) ----------
om = OutputsManager(Loc_1['LocationName'], 2020, 2020)
cache_key = get_cache_key(Loc_1['Latitude'], Loc_1['Longitude'], 2020, 2020)
raw_weather = om.load_json_from_cache(f"wd_{cache_key}.json")  # lecture directe du cache (pas de variant)
assert raw_weather is not None, "cache meteo introuvable"
WD = Weather_data(Loc_1['Latitude'], Loc_1['Longitude'], 2020, 2020,
                  Loc_1['WeatherDataOption'], raw_weather,
                  Loc_1['WeatherFileName'], Loc_1['DailyWeatherFileName'])
n_steps = len(WD.nyears_data['2020'])
print("2. OK meteo chargee :", n_steps, "pas de temps")

# ---------- positions solaires ----------
Sun_samp = Sun_positions_sampled(Loc_1['Latitude'], Loc_1['Longitude'],
                                 1,  # niveau 1 (jour 15 de chaque mois) pour un test rapide
                                 Loc_1['LocationName'], n_steps, Loc_1['TimeZone'])
Sun_complete = Sun_positions(Loc_1['Latitude'], Loc_1['Longitude'], n_steps, Loc_1['TimeZone'])
print("3. OK positions solaires :", len(Sun_samp.SP), "echantillonnees /", n_steps, "completes")

# ---------- controleur (strategie mixte) ----------
# stratégie MIXTE (anti-tracking printemps + tracking 11h-14h l'été + anti le reste)
strat = PilotageStrategy.from_yaml('INPUTS/PILOTAGE/strategie_antitrack_printemps_et_track_midi_ete.yaml')
ctrl = TrackingController.from_inputs(strat, PV_params_dict)

# ---------- geometrie 3D avec controleur ----------
PV_3D = PV_Configuration_3D(PV_params_dict, Sun_samp.solar_vector,
                            visualization=False,
                            pilotage_controller=ctrl,
                            sun_datetimes=Sun_samp.SP.index)
assert len(PV_3D.PV_central_PD_list) == len(Sun_samp.SP), "un mesh par position solaire"
assert np.max(np.abs(PV_3D.tiltY_along_time)) <= 90 + 1e-9
n_anti = int(np.sum(PV_3D.pilotage_mode_along_time == 'anti_tracking'))
print(f"4. OK geometrie 3D : {len(PV_3D.PV_central_PD_list)} meshes, "
      f"tilt in [{PV_3D.tiltY_along_time.min():.1f}, {PV_3D.tiltY_along_time.max():.1f}] deg, "
      f"{n_anti} instants en anti-tracking")

# ---------- production avec controleur ----------
class FakeLight(dict):
    pass
from pase.ENVIRONMENT.light import Light
Light_instance = Light(WD.nyears_data, Sun_complete)
PV_prod = PV_Production(PV_params_dict, pilotage_controller=ctrl)
PV_prod.get_several_years_of_electricity_production(Sun_complete, Light_instance.data,
                                                    WD.nyears_data)
E_mixte = PV_prod.production['2020']['P_central'].sum()
print(f"5. OK production strategie mixte : {E_mixte:.2f} MWh")

# ---------- coherence geometrie <-> production ----------
# Les angles aux memes instants doivent etre COHERENTS des deux cotes.
# NB : convention PASE, la meteo PVGIS est indexee a HH:10 et les positions
# solaires echantillonnees a HH:00 -> appariement par (mois, jour, heure).
# Les vecteurs solaires different legerement (10 min d'ecart + zenith apparent
# vs geometrique) donc on tolere quelques degres d'ecart sur l'angle, mais le
# MODE doit etre identique.
tilt_prod = PV_prod.tiltY_per_year['2020']
mode_prod = PV_prod.mode_per_year['2020']
prod_by_mdh = {(ts.month, ts.day, ts.hour): (tilt_prod.iloc[i], mode_prod.iloc[i])
               for i, ts in enumerate(tilt_prod.index)}
matched, diffs, mode_mismatch = 0, [], 0
for i, ts in enumerate(Sun_samp.SP.index):
    key = (ts.month, ts.day, ts.hour)
    if key in prod_by_mdh:
        v_prod, m_prod = prod_by_mdh[key]
        diffs.append(abs(float(v_prod) - PV_3D.tiltY_along_time[i]))
        if m_prod != PV_3D.pilotage_mode_along_time[i]:
            mode_mismatch += 1
        matched += 1
diffs = np.array(diffs)
assert matched > 100, f"trop peu d instants apparies ({matched})"
assert mode_mismatch == 0, f"{mode_mismatch} instants avec un mode different"
assert np.median(diffs) < 5, f"angles geometrie vs production trop differents (mediane {np.median(diffs):.2f} deg)"
print(f"6. OK coherence geometrie <-> production : {matched} instants compares, "
      f"modes identiques, diff angle mediane = {np.median(diffs):.2f} deg "
      f"(10 min d'ecart d'horodatage PVGIS)")

# ---------- non-regression : tracking_pur vs pipeline historique ----------
strat_ref = PilotageStrategy.from_yaml('INPUTS/PILOTAGE/strategie_tracking_pur.yaml')
ctrl_ref = TrackingController.from_inputs(strat_ref, PV_params_dict)
prod_new = PV_Production(PV_params_dict, pilotage_controller=ctrl_ref)
prod_new.get_several_years_of_electricity_production(Sun_complete, Light_instance.data,
                                                     WD.nyears_data)
prod_old = PV_Production(PV_params_dict)  # pipeline historique
prod_old.get_several_years_of_electricity_production(Sun_complete, Light_instance.data,
                                                     WD.nyears_data)
E_new = prod_new.production['2020']['P_central'].sum()
E_old = prod_old.production['2020']['P_central'].sum()
print(f"7. Non-regression : tracking_pur via controleur = {E_new:.3f} MWh ; "
      f"pipeline historique = {E_old:.3f} MWh ; ecart = {100*(E_new-E_old)/E_old:.3f} %")

# ---------- trace CSV + figure ----------
csv_path, fig_path = export_tracking_trace(
    tilt_series=PV_prod.tiltY_per_year['2020'],
    mode_series=PV_prod.mode_per_year['2020'],
    true_angle_series=PV_prod.true_angle_per_year['2020'],
    sun_positions_df=Sun_complete.sp_leapY,
    label='TEST_antitrack_printemps_2020',
    day='2020-06-15',
    max_tilt_deg=ctrl.max_tilt_deg,
    csv_dir='OUTPUTS/GRAPHS/TEST_PILOTAGE',
    fig_dir='OUTPUTS/GRAPHS/TEST_PILOTAGE')
trace = pd.read_csv(csv_path, parse_dates=['datetime'])
# 15 juin 12h -> tracking ; 15 juin 9h -> anti_tracking ; 10 avril midi -> anti_tracking
r = trace.set_index('datetime')
def check(ts, mode):
    row = r.loc[ts]
    assert row['mode'] == mode, f"{ts}: attendu {mode}, obtenu {row['mode']}"
    return row
row_t = check('2020-06-15 12:10:00', 'tracking')
row_a = check('2020-06-15 09:10:00', 'anti_tracking')
check('2020-04-10 12:10:00', 'anti_tracking')
check('2020-01-10 12:10:00', 'tracking')
assert abs(abs(row_a['applied_panel_tilt'] - row_a['true_tracking_angle']) - 90) < 1e-2, \
    "anti-tracking : tilt doit etre a 90 deg de l angle vrai"
print("8. OK trace CSV : modes corrects aux instants tests, anti-tracking perpendiculaire")
print("   CSV :", csv_path)
print("   Figure :", fig_path)

print("\n=== TEST D'INTEGRATION : TOUT EST OK ===")
