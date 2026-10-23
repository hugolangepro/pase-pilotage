# Tracking 1 axe dans PASE — Notes techniques

> Notes de travail — 2026-07-01  
> Fichiers concernés : `example_tracking_hugo.py`, `pase/PHOTOVOLTAICS/configuration.py`, `pase/ENVIRONMENT/light.py`

---

## 1. Vue d'ensemble du flux de simulation

Le fichier `example_tracking_hugo.py` orchestre une simulation agrivoltaïque complète avec tracking 1 axe. Les grandes étapes sont :

1. **Chargement des inputs YAML** (localisation, centrale PV, module PV, culture)
2. **Données météo** (PVGIS ou fichier CSV)
3. **Positions solaires** échantillonnées + complètes
4. **Géométrie 3D** des panneaux (avec calcul des angles de tracking)
5. **Ray casting** → cartes d'ombrage direct et diffus
6. **Production électrique** (modèle HDKR)
7. **Modèle de culture** (STICS ou simple)
8. **Visualisation et sauvegarde**

---

## 2. Activation du tracking

Dans le fichier YAML `INPUTS/AV_CENTRAL/Example2_tracking_AV_hugo.yaml` :

```yaml
RotationAxisNumber:
  Value: 1        # 0 = fixe, 1 = tracking 1 axe

CentralAzimut:
  Value: 90       # Orientation de l'axe (90° = Est → axe N-S)

TiltY:
  Value: 90       # Ignoré en mode tracking (forcé à 0° au départ)
```

Le `RotationAxisNumber: 1` est la clé qui active toute la logique de tracking.

---

## 3. Où l'angle est calculé — fichier principal

**Fichier : `pase/PHOTOVOLTAICS/configuration.py`**

Tout part du constructeur `PV_Configuration_3D.__init__` (ligne 1348) :

```python
if params_dict["RotationAxisNumber"] == 1:
    params_dict["TiltY"] = 0   # position de base = à plat

self.get_tiltY_along_time(sun_vector, azimut, GCR_x)

for tilt in self.tiltY_along_time:
    params_dict["TiltY"] = tilt
    PV_central = self.create_tilted_central(params_dict)  # snapshot 3D
    self.PV_central_PD_list.append(PV_central)
```

Il génère **une géométrie 3D par position solaire échantillonnée** et stocke la liste dans `PV_central_PD_list`. Le ray-casting utilise ensuite chaque snapshot.

---

## 4. Calcul de l'angle — `get_tiltY_along_time` (ligne 1584)

4 étapes en chaîne :

### a) Rotation du vecteur solaire dans le repère de la centrale (ligne 1594)

```python
sun_vect_CC[:,0] = sun_x * cos(azimut) - sun_y * sin(azimut)
sun_vect_CC[:,1] = sun_x * sin(azimut) + sun_y * cos(azimut)
sun_vect_CC[:,2] = sun_z  # inchangé
```

Le vecteur solaire (coordonnées globales N-E-Zénith) est réexprimé dans le repère propre à la centrale PV selon son azimut.

### b) Angle de tracking idéal / True-tracking angle (ligne 1610)

```python
true_tracking_angle = arctan2(sun_vect_CC[:,0], sun_vect_CC[:,2])
```

C'est l'angle qui permettrait au panneau de **faire face directement au soleil** dans le plan de rotation (XZ).

**Pourquoi `arctan2(sun_x, sun_z)` ?**

Le panneau tourne autour de l'axe Y (N-S). Au repos (θ=0), il est horizontal, sa normale pointe vers le zénith (+Z). Quand il tourne de θ, sa normale devient `(sin θ, 0, cos θ)`. Pour un tracking parfait :

```
tan θ = sun_x / sun_z   →   θ = arctan2(sun_x, sun_z)
```

Vue de côté dans le plan XZ :
```
Zénith (+Z)
    │         ☀ soleil
    │        /
    │       /  sun_z
    │      /
    │  θ  /
    │----/──────────────── (+X, Est)
         sun_x

θ = arctan2(sun_x, sun_z) = angle entre la verticale et le soleil dans ce plan
```

`arctan2` est préféré à `arctan` car il gère `sun_z = 0` (soleil au zénith) et distingue les quadrants matin/soir.

La composante `sun_y` (N-S) est **ignorée** car le tracker 1 axe ne contrôle pas cette direction.

### c) Correction de backtracking (ligne 1617)

```python
GCR_x = PanelDimensionX * NumberOfPanelsX / RepetitionDistanceOfPVBlocksX
value = |cos(θ)| / GCR_x

if value >= 1:
    correction = 0          # pas d'ombrage inter-rangées
else:
    correction = -sign(θ) * arccos(value)
```

Quand le GCR (Ground Coverage Ratio) est élevé, les rangées s'ombrent mutuellement en début/fin de journée. La correction **recule** légèrement le panneau par rapport à la position idéale pour que l'ombre d'une rangée soit exactement tangente à la rangée suivante (et ne la recouvre pas).

### d) Limitation de l'angle (ligne 1635)

```python
tiltY = clamp(tiltY, -π/3, +π/3)   # ±60°
```

Limite mécanique de la structure.

---

## 5. Intuition géométrique du backtracking

```
Vue de côté (plan XZ) — deux rangées adjacentes

        ☀  soleil bas (début de journée)

   ┌──────────┐         ┌──────────┐
   │ rangée 1 │         │ rangée 2 │
   └──────────┘         └──────────┘
         ↓ ombre trop longue sans correction
         
   → Le tracker "recule" légèrement (s'aplatit)
   → L'ombre s'arrête exactement au pied de la rangée 2
   → Aucune perte par ombrage inter-rangées
```

---

## 6. Chaîne d'appel complète

```
example_tracking_hugo.py
    │
    ├── Sun_positions_sampled(lat, lon, PrecisionLevel, ...)    [light.py:464]
    │       → calcule positions solaires (azimut, élévation) pour les jours représentatifs
    │       → self.solar_vector  (N positions × 3 composantes)
    │
    └── PV_Configuration_3D(PV_params_dict, Sun_positions_samp.solar_vector)
            │                                      [configuration.py:1348]
            │  RotationAxisNumber == 1 → TiltY forcé à 0
            │
            └── get_tiltY_along_time(sun_vector, azimut, GCR_x)   [ligne 1584]
                    ├── get_sun_vect_in_central_coord()   → repère de la centrale
                    ├── get_true_tracking_angle()         → arctan2 → angle idéal
                    ├── get_backT_corr_angle()            → correction inter-ombrage
                    └── get_limitated_angle()             → clamp ±60°
                            ↓
                    tiltY_along_time  [N angles, en degrés]
                            ↓
                for tilt in tiltY_along_time:
                    PV_central_PD_list.append( create_tilted_central(tilt) )
                    → 1 snapshot 3D par position solaire
```

---

## 7. Pas de temps de recalcul de l'angle

Le pas de temps résulte de **deux paramètres combinés** dans le YAML de localisation.

### Fréquence météo (`freq_deter`)

| Nb points/an | Fréquence | Pas de temps |
|---|---|---|
| 8760 | `1H` | **1 heure** |
| 35040 | `15min` | 15 minutes |
| 52560 | `10min` | 10 minutes |

### Niveau de précision solaire (`PrecisionLevelOnSunPosition`)

| Niveau | Jours retenus | Description |
|---|---|---|
| 1 | 12 jours | Le 15 de chaque mois |
| **2** | **52 jours** | **Chaque mercredi de l'année** ← config actuelle |
| 3 | 365 jours | Tous les jours |

### Configuration actuelle (`PrecisionLevelOnSunPosition: 2`, météo horaire)

- Angle recalculé **toutes les heures**, sur les **52 mercredis** représentatifs
- ≈ `52 × ~12h = ~624 positions solaires` → **~624 snapshots 3D** dans `PV_central_PD_list`
- Le ray-casting utilise un snapshot différent pour chaque position solaire

---

## 8. Lien avec le papier NREL

> Anderson, K. and Mikofski, M. (2020). *Slope-Aware Backtracking for Single-Axis Trackers*. NREL/TP-5K00-76626.

PASE implémente les **sections 3 et 4** du papier (cas terrain plat) :

| Papier NREL | PASE | Équivalence |
|---|---|---|
| Éq. 4 : rotation vecteur solaire | `get_sun_vect_in_central_coord` | ✅ avec `β_a = 0` |
| Éq. 5 : `θ_T = atan2(s'_x, s'_z)` | `get_true_tracking_angle` | ✅ identique |
| Éq. 14 : correction backtracking | `get_backT_corr_angle` | ✅ avec `β_c = 0` |
| Éq. 16 : `θ_B = θ_T + θ_c` | `get_corrected_tracking_angle` | ✅ identique |
| **Section 5 : pente de terrain** | ❌ **non implémenté** | — |

**Simplifications de PASE par rapport au papier :**
- `β_a = 0` : axe de rotation supposé horizontal (pas de dénivelé de l'axe)
- `β_c = 0` : pas de correction pour pente perpendiculaire à l'axe

Cela est explicitement reconnu dans le code :
```python
def get_sun_vect_in_central_coord(self, sun_vect, azimut):
    # Do not take into account the slope of the area and the slope of the
    # rotation axis (see the previous framework to complete)
```

**Conséquence pratique :** si la centrale agrivoltaïque est installée sur un terrain pentu perpendiculairement à l'axe de tracking, la correction de backtracking sera imprécise. Pour les terrains plats, l'implémentation est exacte.

---

## 9. Fichiers clés

| Fichier | Rôle |
|---|---|
| `example_tracking_hugo.py` | Script principal, orchestre la simulation |
| `INPUTS/AV_CENTRAL/Example2_tracking_AV_hugo.yaml` | Paramètres de la centrale (tracking ON/OFF, azimut, GCR…) |
| `INPUTS/SCENARIOS/Example1_loc_hugo.yaml` | Localisation, précision solaire, pas de temps |
| `pase/PHOTOVOLTAICS/configuration.py` | **Calcul des angles de tracking** (lignes 1584–1642) |
| `pase/ENVIRONMENT/light.py` | Calcul des positions solaires (`Sun_positions_sampled`) |
| `pase/PHOTOVOLTAICS/production.py` | Production électrique (modèle HDKR sur panneaux trackés) |
