# ============== [HUGO - PILOTAGE] DEBUT AJOUT (FICHIER ENTIEREMENT NOUVEAU) ==============
#
# Module de pilotage des trackers PV : tracking / anti-tracking / tilt fixe.
#
# Ce module centralise le calcul de l'angle d'inclinaison des panneaux, qui était
# jusqu'ici implémenté deux fois dans PASE (avec des limites différentes) :
#   - pase/PHOTOVOLTAICS/configuration.py  (côté géométrie 3D / ray casting, clamp ±60°)
#   - pase/PHOTOVOLTAICS/production.py     (côté production électrique, angles > ±90° mis à 0)
#
# Deux classes :
#   - PilotageStrategy   : charge un fichier YAML de stratégie (INPUTS/PILOTAGE/*.yaml)
#                          et résout le mode de pilotage actif à chaque instant.
#   - TrackingController : calcule la série d'angles d'inclinaison (tilt) à partir des
#                          vecteurs solaires + du mode actif, avec clamp à ±MaxTiltAngle.
#
# Modes disponibles :
#   - 'tracking'      : suivi du soleil (angle vrai + correction backtracking) — identique
#                       à l'algorithme historique de PASE.
#   - 'anti_tracking' : panneau "en tranche" face au soleil (tilt = angle vrai ± 90°),
#                       captation directe nulle, lumière maximale au sol. SANS backtracking.
#   - 'fixed'         : angle fixe défini dans la règle (paramètre fixed_angle).
#
# Format YAML de stratégie :
#   name: ma_strategie
#   default_mode: tracking          # mode appliqué hors de toute règle
#   rules:                          # la PREMIERE règle qui matche gagne
#     - name: antitrack_printemps   # optionnel
#       date_start: "04-01"         # MM-DD inclusif, indépendant de l'année (optionnel)
#       date_end: "05-15"           # MM-DD inclusif ; wrap autorisé (ex. 12-01 -> 02-28)
#       hour_start: 11              # heure de début incluse (optionnel)
#       hour_end: 14                # heure de fin EXCLUE ; wrap autorisé (ex. 22 -> 5)
#       mode: anti_tracking         # tracking | anti_tracking | fixed
#       fixed_angle: 0              # requis uniquement si mode == fixed (degrés)
#
# Auteur : Hugo (stage pilotage agrivoltaïque) — 2026

import logging

import numpy as np
import yaml

logger = logging.getLogger(__name__)

MODES_VALIDES = ('tracking', 'anti_tracking', 'fixed')


class PilotageStrategy:
    """Stratégie de pilotage : planning temporel des modes tracking/anti-tracking/fixe."""

    def __init__(self, name, default_mode='tracking', rules=None, description=''):
        self.name = name
        self.description = description
        self.default_mode = default_mode
        self.rules = rules if rules is not None else []
        self._validate()

    # ------------------------------------------------------------------ #
    @classmethod
    def from_yaml(cls, path):
        """Charge une stratégie depuis un fichier YAML (format documenté en tête de module).

        NB : on utilise yaml.safe_load directement (et non YAML_Inputs_provider) car le
        format {Value, Type, Limit} de PASE est prévu pour des scalaires indépendants,
        pas pour une liste de règles hétérogènes.
        """
        with open(path, 'r') as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError(f"[PILOTAGE] Fichier de stratégie invalide : {path}")
        return cls(name=raw.get('name', 'sans_nom'),
                   default_mode=raw.get('default_mode', 'tracking'),
                   rules=raw.get('rules') or [],
                   description=raw.get('description', ''))

    # ------------------------------------------------------------------ #
    def _validate(self):
        if self.default_mode not in ('tracking', 'anti_tracking'):
            raise ValueError(
                f"[PILOTAGE] default_mode invalide '{self.default_mode}' "
                f"(attendu : 'tracking' ou 'anti_tracking')")

        for i, rule in enumerate(self.rules):
            ctx = f"[PILOTAGE] Stratégie '{self.name}', règle #{i+1} ({rule.get('name', 'sans nom')})"
            if not isinstance(rule, dict):
                raise ValueError(f"{ctx} : chaque règle doit être un dictionnaire YAML")
            mode = rule.get('mode')
            if mode not in MODES_VALIDES:
                raise ValueError(f"{ctx} : mode invalide '{mode}' (attendu : {MODES_VALIDES})")
            if mode == 'fixed' and 'fixed_angle' not in rule:
                raise ValueError(f"{ctx} : mode 'fixed' requiert le paramètre fixed_angle (degrés)")
            # dates : les deux bornes ou aucune
            has_ds, has_de = 'date_start' in rule, 'date_end' in rule
            if has_ds != has_de:
                raise ValueError(f"{ctx} : date_start et date_end doivent être fournis ensemble")
            if has_ds:
                for key in ('date_start', 'date_end'):
                    self._parse_mmdd(rule[key], ctx)
            # heures : les deux bornes ou aucune
            has_hs, has_he = 'hour_start' in rule, 'hour_end' in rule
            if has_hs != has_he:
                raise ValueError(f"{ctx} : hour_start et hour_end doivent être fournis ensemble")
            if has_hs:
                for key in ('hour_start', 'hour_end'):
                    h = rule[key]
                    if not isinstance(h, (int, float)) or not (0 <= h <= 24):
                        raise ValueError(f"{ctx} : {key}={h} invalide (attendu : nombre entre 0 et 24)")

        logger.info(f"[PILOTAGE] Stratégie '{self.name}' chargée : "
                    f"default_mode={self.default_mode}, {len(self.rules)} règle(s)")

    @staticmethod
    def _parse_mmdd(value, ctx=''):
        """'MM-DD' -> clé entière MM*100+DD (comparaison vectorisée facile)."""
        try:
            mm, dd = str(value).split('-')
            mm, dd = int(mm), int(dd)
            assert 1 <= mm <= 12 and 1 <= dd <= 31
        except (ValueError, AssertionError):
            raise ValueError(f"{ctx} : date '{value}' invalide (format attendu : 'MM-DD')")
        return mm * 100 + dd

    # ------------------------------------------------------------------ #
    def resolve(self, datetime_index):
        """Résout le mode actif pour chaque instant de datetime_index.

        Parameters
        ----------
        datetime_index : pd.DatetimeIndex
            Instants de la simulation (l'année est ignorée : règles year-agnostic).

        Returns
        -------
        modes : np.ndarray (dtype=object)
            Mode actif à chaque instant ('tracking', 'anti_tracking' ou 'fixed').
        fixed_angles : np.ndarray (float)
            Angle (degrés) pour les instants en mode 'fixed', NaN ailleurs.
        """
        n = len(datetime_index)
        # clé MM*100+DD de chaque instant + heure décimale
        mmdd = np.asarray(datetime_index.month) * 100 + np.asarray(datetime_index.day)
        hours = np.asarray(datetime_index.hour) + np.asarray(datetime_index.minute) / 60.0

        modes = np.full(n, self.default_mode, dtype=object)
        fixed_angles = np.full(n, np.nan)
        assigned = np.zeros(n, dtype=bool)  # première règle qui matche gagne

        for rule in self.rules:
            mask = ~assigned

            if 'date_start' in rule:
                ds = self._parse_mmdd(rule['date_start'])
                de = self._parse_mmdd(rule['date_end'])
                if ds <= de:
                    mask &= (mmdd >= ds) & (mmdd <= de)
                else:  # fenêtre à cheval sur le nouvel an (ex. 12-01 -> 02-28)
                    mask &= (mmdd >= ds) | (mmdd <= de)

            if 'hour_start' in rule:
                hs, he = rule['hour_start'], rule['hour_end']
                if hs <= he:
                    mask &= (hours >= hs) & (hours < he)
                else:  # fenêtre horaire à cheval sur minuit (ex. 22 -> 5)
                    mask &= (hours >= hs) | (hours < he)

            modes[mask] = rule['mode']
            if rule['mode'] == 'fixed':
                fixed_angles[mask] = float(rule['fixed_angle'])
            assigned |= mask

        return modes, fixed_angles


class TrackingController:
    """Calcule la série d'angles d'inclinaison des panneaux selon une PilotageStrategy.

    Utilisé par les DEUX chemins de calcul de PASE :
      - PV_Configuration_3D (géométrie 3D, positions solaires échantillonnées)
      - PV_Production       (production électrique, résolution horaire)
    ce qui garantit des angles STRICTEMENT identiques des deux côtés.
    """

    def __init__(self, strategy, azimut_deg, GCR_x, max_tilt_deg=90.0,
                 soil_angle=0.0, hinge='Center', height=None, span_x=None):
        """
        Parameters
        ----------
        strategy : PilotageStrategy
        azimut_deg : float
            CentralAzimut en degrés (converti en radians ici — corrige au passage le
            bug historique de configuration.py qui passait des degrés à cos/sin).
        GCR_x : float
            Ground coverage ratio selon X (PanelDimensionX*NumberOfPanelsX/RepetitionDistanceOfPVBlocksX).
        max_tilt_deg : float
            Limite mécanique |tilt| <= max_tilt_deg. 90 = pas de limite.
        soil_angle : float
            Pente du terrain (radians), utilisée par la correction backtracking
            (0 par défaut, comme dans production.py).
        hinge, height, span_x :
            Optionnels — uniquement pour le warning de garde au sol (Hinge=Center).
        """
        self.strategy = strategy
        self.azimut = azimut_deg * np.pi / 180
        self.GCR_x = GCR_x
        self.max_tilt_deg = float(max_tilt_deg)
        self.soil_angle = soil_angle

        # Warning garde au sol : le check statique de Inputs_aggregator utilise le TiltY
        # du YAML, pas le tilt dynamique -> on vérifie ici avec la limite max réelle.
        if (height is not None and span_x is not None
                and str(hinge).lower() == 'center'):
            clearance = height - span_x / 2 * np.sin(np.deg2rad(self.max_tilt_deg))
            if clearance <= 0:
                logger.warning(
                    f"[PILOTAGE] Garde au sol potentiellement négative : avec "
                    f"MaxTiltAngle={self.max_tilt_deg}° et Hinge=Center, le bord bas des "
                    f"panneaux descendrait à {clearance:.3f} m (Height={height}, span_x={span_x}). "
                    f"Réduire MaxTiltAngle ou augmenter Height.")

    @classmethod
    def from_inputs(cls, strategy, pv_params_dict):
        """Construit le contrôleur depuis le dictionnaire d'inputs agrégé de PASE."""
        span_x = ((pv_params_dict['NumberOfPanelsX'] - 1)
                  * pv_params_dict['RepetitionDistanceOfPanelsX']
                  + pv_params_dict['PanelDimensionX'])
        GCR_x = (pv_params_dict['PanelDimensionX'] * pv_params_dict['NumberOfPanelsX']
                 / pv_params_dict['RepetitionDistanceOfPVBlocksX'])
        return cls(strategy,
                   azimut_deg=pv_params_dict['CentralAzimut'],
                   GCR_x=GCR_x,
                   max_tilt_deg=pv_params_dict.get('MaxTiltAngle', 90),
                   hinge=pv_params_dict.get('Hinge', 'Center'),
                   height=pv_params_dict.get('Height'),
                   span_x=span_x)

    # ------------------------------------------------------------------ #
    def compute_tilt(self, sun_vect, datetime_index):
        """Calcule le tilt appliqué à chaque instant.

        Parameters
        ----------
        sun_vect : np.ndarray (N, 3)
            Vecteurs solaires unitaires {X=Est, Y=Nord, Z=Zénith} (repère monde).
        datetime_index : pd.DatetimeIndex (longueur N)
            Instants correspondants (pour résoudre le mode de pilotage).

        Returns
        -------
        dict avec des arrays alignés de longueur N :
            'tilt_deg'       : tilt appliqué (degrés), clampé à ±MaxTiltAngle
            'mode'           : mode actif à chaque instant
            'true_angle_deg' : angle de tracking vrai (sans backtracking ni clamp)
            'sun_vect_cc'    : vecteurs solaires dans le repère de la centrale
        """
        if len(datetime_index) != len(sun_vect):
            raise ValueError(
                f"[PILOTAGE] Longueurs incohérentes : {len(sun_vect)} vecteurs solaires "
                f"vs {len(datetime_index)} instants")

        # 1) Vecteur soleil dans le repère de la centrale (rotation d'azimut)
        sun_vect_cc = np.zeros_like(sun_vect, dtype=float)
        sun_vect_cc[:, 0] = (sun_vect[:, 0] * np.cos(self.azimut)
                             - sun_vect[:, 1] * np.sin(self.azimut))
        sun_vect_cc[:, 1] = (sun_vect[:, 0] * np.sin(self.azimut)
                             + sun_vect[:, 1] * np.cos(self.azimut))
        sun_vect_cc[:, 2] = sun_vect[:, 2]

        # 2) Angle de tracking vrai : le panneau est perpendiculaire au soleil
        #    (projection dans le plan X-Z de la centrale). Dans (-90°, 90°) le jour.
        true_angle = np.arctan2(sun_vect_cc[:, 0], sun_vect_cc[:, 2])  # radians

        # 3) Résolution du mode actif à chaque instant
        modes, fixed_angles = self.strategy.resolve(datetime_index)

        # 4) Angle par mode
        # --- tracking : angle vrai + correction backtracking (algorithme historique PASE)
        tracking_tilt = true_angle + self._backtracking_correction(true_angle)

        # --- anti-tracking : perpendiculaire au tracking vrai -> le plan du panneau
        #     contient le rayon solaire, captation directe nulle. SANS backtracking.
        #     Ramené dans (-90°, 90°] : +90° si angle vrai <= 0, -90° sinon.
        anti_tilt = np.where(true_angle > 0,
                             true_angle - np.pi / 2,
                             true_angle + np.pi / 2)

        tilt = np.where(modes == 'anti_tracking', anti_tilt, tracking_tilt)
        is_fixed = (modes == 'fixed')
        if np.any(is_fixed):
            tilt = np.where(is_fixed, np.deg2rad(fixed_angles), tilt)

        # 5) Clamp final à ±MaxTiltAngle (vrai clamp — corrige le bug historique de
        #    production.py qui mettait à 0 les angles hors limites)
        max_tilt_rad = np.deg2rad(self.max_tilt_deg)
        tilt = np.clip(tilt, -max_tilt_rad, max_tilt_rad)

        return {'tilt_deg': tilt * 180 / np.pi,
                'mode': modes,
                'true_angle_deg': true_angle * 180 / np.pi,
                'sun_vect_cc': sun_vect_cc}

    # ------------------------------------------------------------------ #
    def _backtracking_correction(self, true_angle):
        """Correction backtracking (évite l'ombrage mutuel entre rangées).

        Reprise à l'identique de PV_Production.get_backT_corr_angle
        (pase/PHOTOVOLTAICS/production.py), version avec pente du terrain (soil_angle).
        """
        one = np.ones(len(true_angle))
        soil_angle = self.soil_angle * one
        value = np.abs(np.cos(true_angle - self.soil_angle)
                       / (self.GCR_x * np.cos(self.soil_angle)))

        backT_corr_angle = np.zeros(len(true_angle))
        backT_corr_angle[value >= 1] = 0
        backT_corr_angle[value < 1] = -np.sign(true_angle[value < 1]) * np.arccos(
            np.abs(np.cos(true_angle[value < 1] - soil_angle[value < 1]))
            / (self.GCR_x * np.cos(soil_angle[value < 1])))

        return backT_corr_angle

# ============== [HUGO - PILOTAGE] FIN AJOUT ==============
