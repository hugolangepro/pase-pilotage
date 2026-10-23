# ============== [HUGO - PILOTAGE] FICHIER NOUVEAU (script de verification) ==============
# Test unitaire du module de pilotage (sans simulation complete).
# Lancer avec l'env PASE 2.0 (python 3.12) depuis la racine du repo :
#   python tests/PHOTOVOLTAICS/test_pilotage_unitaire.py
"""Test unitaire du module de pilotage (sans simulation complète)."""
import os
import sys
import numpy as np
import pandas as pd

# Racine du repo derivee du chemin du fichier -> test portable (pas de chemin en dur)
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, BASE)
from pase.PHOTOVOLTAICS.pilotage import PilotageStrategy, TrackingController

ok = 0

# ---------- 1. Chargement des 3 stratégies YAML ----------
for f in ['strategie_tracking_pur', 'strategie_antitrack_pur', 'strategie_antitrack_printemps']:
    s = PilotageStrategy.from_yaml(f'{BASE}/INPUTS/PILOTAGE/{f}.yaml')
    print(f'OK chargement {f} -> name={s.name}, default={s.default_mode}, {len(s.rules)} regles')
    ok += 1

# ---------- 2. Résolution du planning ----------
# Stratégie mixte définie EN DUR ici (indépendante des fichiers YAML editables) :
# anti-tracking au printemps + tracking 11h-14h l'été + anti le reste de l'été.
strat = PilotageStrategy('test_mixte', 'tracking', [
    {'name': 'printemps', 'date_start': '04-01', 'date_end': '05-15', 'mode': 'anti_tracking'},
    {'name': 'midi_ete', 'date_start': '06-01', 'date_end': '08-31',
     'hour_start': 11, 'hour_end': 14, 'mode': 'tracking'},
    {'name': 'reste_ete', 'date_start': '06-01', 'date_end': '08-31', 'mode': 'anti_tracking'},
])
idx = pd.date_range('2020-01-01', '2020-12-31 23:00', freq='1h', tz='Etc/GMT+0')
modes, fixed = strat.resolve(idx)

def mode_at(ts):
    return modes[idx.get_loc(pd.Timestamp(ts, tz='Etc/GMT+0'))]

assert mode_at('2020-01-10 12:00') == 'tracking', "janvier -> default tracking"
assert mode_at('2020-04-10 12:00') == 'anti_tracking', "10 avril -> anti_tracking (regle printemps)"
assert mode_at('2020-05-15 08:00') == 'anti_tracking', "15 mai inclus -> anti_tracking"
assert mode_at('2020-05-16 08:00') == 'tracking', "16 mai -> default"
assert mode_at('2020-06-15 12:00') == 'tracking', "15 juin 12h -> tracking (11h-14h)"
assert mode_at('2020-06-15 13:00') == 'tracking', "15 juin 13h -> tracking"
assert mode_at('2020-06-15 14:00') == 'anti_tracking', "15 juin 14h -> anti (hour_end exclu)"
assert mode_at('2020-06-15 09:00') == 'anti_tracking', "15 juin 9h -> anti (reste journee ete)"
assert mode_at('2020-09-10 12:00') == 'tracking', "septembre -> default"
print('OK resolution du planning (9 assertions dates/heures)')
ok += 1

# Fenetre a cheval sur le nouvel an + mode fixed
s2 = PilotageStrategy('test', 'tracking',
                      [{'date_start': '12-01', 'date_end': '02-28', 'mode': 'fixed', 'fixed_angle': 15}])
m2, f2 = s2.resolve(idx)
i_jan = idx.get_loc(pd.Timestamp('2020-01-15 10:00', tz='Etc/GMT+0'))
i_jul = idx.get_loc(pd.Timestamp('2020-07-15 10:00', tz='Etc/GMT+0'))
assert m2[i_jan] == 'fixed' and f2[i_jan] == 15.0
assert m2[i_jul] == 'tracking' and np.isnan(f2[i_jul])
print('OK fenetre a cheval nouvel an + mode fixed')
ok += 1

# ---------- 3. Math du contrôleur ----------
# Vecteurs solaires synthétiques : soleil balayant le plan Est-Zenith-Ouest
elev = np.deg2rad(np.array([10, 30, 60, 89, 60, 30, 10], dtype=float))
az_deg = np.array([90, 90, 90, 90, 270, 270, 270], dtype=float)  # Est le matin, Ouest l'aprem
sun_vect = np.zeros((7, 3))
sun_vect[:, 0] = np.cos(elev) * np.sin(np.deg2rad(az_deg))   # X = Est
sun_vect[:, 1] = np.cos(elev) * np.cos(np.deg2rad(az_deg))   # Y = Nord
sun_vect[:, 2] = np.sin(elev)                                 # Z = Zenith
dt7 = pd.date_range('2020-06-15 07:00', periods=7, freq='1h', tz='Etc/GMT+0')

# --- tracking pur, GCR très faible (pas de backtracking), azimut 0
strat_track = PilotageStrategy('t', 'tracking', [])
c = TrackingController(strat_track, azimut_deg=0, GCR_x=0.01, max_tilt_deg=90)
res = c.compute_tilt(sun_vect, dt7)
expected_true = np.array([80, 60, 30, 1, -30, -60, -80], dtype=float)  # 90 - elevation, signe Est+/Ouest-
assert np.allclose(res['true_angle_deg'], expected_true, atol=1e-6), res['true_angle_deg']
assert np.allclose(res['tilt_deg'], expected_true, atol=1e-6), "tracking sans backtracking = angle vrai"
print('OK tracking : tilt = angle vrai (signe + a l Est, - a l Ouest)')
ok += 1

# --- anti-tracking : |tilt - angle_vrai| == 90 exactement, resultat dans (-90, 90]
strat_anti = PilotageStrategy('a', 'anti_tracking', [])
c2 = TrackingController(strat_anti, azimut_deg=0, GCR_x=0.01, max_tilt_deg=90)
res2 = c2.compute_tilt(sun_vect, dt7)
assert np.allclose(np.abs(res2['tilt_deg'] - res2['true_angle_deg']), 90, atol=1e-9)
assert np.all(np.abs(res2['tilt_deg']) <= 90)
# captation directe nulle : normale du panneau (sin(tilt), 0, cos(tilt)) . soleil == 0
normal = np.stack([np.sin(np.deg2rad(res2['tilt_deg'])),
                   np.zeros(7),
                   np.cos(np.deg2rad(res2['tilt_deg']))], axis=1)
cosang = np.sum(normal * sun_vect, axis=1)
assert np.allclose(cosang, 0, atol=1e-9), f"captation directe non nulle : {cosang}"
print('OK anti-tracking : perpendiculaire exact, captation directe nulle')
ok += 1

# --- clamp MaxTiltAngle
c3 = TrackingController(strat_anti, azimut_deg=0, GCR_x=0.01, max_tilt_deg=60)
res3 = c3.compute_tilt(sun_vect, dt7)
assert np.all(np.abs(res3['tilt_deg']) <= 60 + 1e-9)
print('OK clamp : |tilt| <= MaxTiltAngle=60')
ok += 1

# --- backtracking : GCR realiste, soleil bas -> correction non nulle en tracking
c4 = TrackingController(strat_track, azimut_deg=0, GCR_x=0.53, max_tilt_deg=90)
res4 = c4.compute_tilt(sun_vect, dt7)
low_sun = [0, 6]  # elevation 10 deg
assert np.all(np.abs(res4['tilt_deg'][low_sun]) < np.abs(res4['true_angle_deg'][low_sun])), \
    "backtracking doit reduire l angle quand le soleil est bas"
print('OK backtracking : angle reduit quand soleil bas (GCR=0.53)')
ok += 1

# --- azimut de la centrale pris en compte (90 deg = axe vers l Est)
c5 = TrackingController(strat_track, azimut_deg=90, GCR_x=0.01, max_tilt_deg=90)
res5 = c5.compute_tilt(sun_vect, dt7)
# soleil plein Est elev 10 -> dans repere centrale tourne de 90deg, x_cc = -y_monde... verif numerique simple :
sv_cc = res5['sun_vect_cc']
az = np.pi / 2
assert np.allclose(sv_cc[:, 0], sun_vect[:, 0] * np.cos(az) - sun_vect[:, 1] * np.sin(az), atol=1e-12)
print('OK rotation azimut de la centrale (en radians, bug historique evite)')
ok += 1

# --- erreurs de validation
try:
    PilotageStrategy('bad', 'tracking', [{'mode': 'nimporte'}])
    raise SystemExit('ERREUR: mode invalide accepte')
except ValueError:
    print('OK validation : mode invalide rejete')
    ok += 1
try:
    PilotageStrategy('bad', 'tracking', [{'mode': 'fixed'}])
    raise SystemExit('ERREUR: fixed sans fixed_angle accepte')
except ValueError:
    print('OK validation : fixed sans fixed_angle rejete')
    ok += 1
try:
    PilotageStrategy('bad', 'tracking', [{'mode': 'tracking', 'date_start': '04-01'}])
    raise SystemExit('ERREUR: date_start seul accepte')
except ValueError:
    print('OK validation : date_start sans date_end rejete')
    ok += 1

print(f'\n=== {ok + 9} verifications passees, tout est OK ===')
