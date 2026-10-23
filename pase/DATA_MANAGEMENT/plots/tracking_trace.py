# ============== [HUGO - PILOTAGE] DEBUT AJOUT (FICHIER ENTIEREMENT NOUVEAU) ==============
#
# Trace de vérification du pilotage des trackers :
#   - CSV horodaté (année complète) : position du soleil, angle de tracking vrai,
#     tilt réellement appliqué, mode actif (tracking / anti_tracking / fixed)
#   - Figure matplotlib sur une journée choisie : tilt appliqué vs angle de
#     tracking vrai vs élévation solaire, avec bandes colorées par mode.
#
# Permet de vérifier heure par heure ce que fait l'algorithme de pilotage.
#
# NB : la trace est construite côté PRODUCTION (résolution horaire, année
# complète). Les maillages 3D côté géométrie n'existent qu'aux positions
# solaires échantillonnées (PrecisionLevelOnSunPosition) mais utilisent
# exactement le même TrackingController, donc les mêmes angles.
#
# Auteur : Hugo (stage pilotage agrivoltaïque) — 2026

import os

import matplotlib
# ============== [HUGO - PILOTAGE] DEBUT MODIF ==============
# Ne pas ecraser un backend non-interactif deja choisi (ex. 'Agg' en mode batch) :
# sinon un import paresseux de ce module (draw_mode_bands appele depuis les autres
# graphes) rebasculerait sur MacOSX au runtime et plt.show() bloquerait.
if matplotlib.get_backend().lower() != 'agg':
    try:
        matplotlib.use('MacOSX')
    except Exception:
        pass
# ============== [HUGO - PILOTAGE] FIN MODIF ==============
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Couleurs des bandes de mode sur la figure (code couleur PARTAGE par tous les
# graphes : traces par jour, integrales PV/biomasse, comparaison grid...)
MODE_COLORS = {'tracking': '#2ca02c',       # vert
               'anti_tracking': '#d62728',  # rouge
               'fixed': '#1f77b4',          # bleu
               'hybrid': '#9467bd'}         # violet -> jour melangeant plusieurs modes

# Libelle lisible des modes pour les legendes
MODE_LABELS = {'tracking': 'tracking',
               'anti_tracking': 'anti-tracking',
               'fixed': 'tilt fixe',
               'hybrid': 'hybride (tracking + anti-tracking le meme jour)'}


def _classifier_par_jour(mode_series):
    """Classe chaque instant selon le mode DOMINANT de sa journee, ou 'hybrid'
    si la journee melange plusieurs modes (ex. tracking le midi + anti le reste).

    Retourne une pd.Series (meme index) de classes dans
    {tracking, anti_tracking, fixed, hybrid}.
    """
    jours = mode_series.index.normalize()               # minuit de chaque jour
    par_jour = pd.Series(mode_series.to_numpy(), index=jours)
    nuniq = par_jour.groupby(level=0).transform('nunique')
    premier = par_jour.groupby(level=0).transform('first')
    classe = np.where(nuniq.to_numpy() > 1, 'hybrid', premier.to_numpy())
    return pd.Series(classe, index=mode_series.index)


def draw_mode_bands(ax, mode_series, alpha=0.12, per_day=True):
    """Dessine des bandes verticales colorees par mode de pilotage sur l'axe
    temporel de `ax`, en regroupant les instants consecutifs de meme classe.

    Meme code couleur que les traces par jour (MODE_COLORS) -> permet de voir
    d'un coup d'oeil QUAND une strategie est en tracking / anti-tracking / fixe /
    hybride, ce qui justifie visuellement les inflexions des courbes d'integrale.

    Parameters
    ----------
    ax : matplotlib Axes (axe x = temps/datetime)
    mode_series : pd.Series indexee par datetime (valeurs = 'tracking'/'anti_tracking'/'fixed')
    per_day : bool
        Si True (defaut), on classe par JOUR : un jour qui melange plusieurs modes
        (ex. tracking 11h-14h + anti le reste) est colore en 'hybrid' plutot qu'en
        fines rayures -> beaucoup plus lisible sur une vue annuelle.
        Si False, on colore chaque instant par son mode reel (utile en vue intra-jour).

    Returns
    -------
    dict {classe: Patch} : handles de legende pour les classes presentes.
    """
    from matplotlib.patches import Patch
    if mode_series is None or len(mode_series) == 0:
        return {}
    serie = _classifier_par_jour(mode_series) if per_day else mode_series
    idx = serie.index
    vals = serie.to_numpy()
    n = len(vals)
    handles = {}
    start = 0
    for i in range(1, n + 1):
        if i == n or vals[i] != vals[start]:
            m = vals[start]
            x0 = idx[start]
            # bord droit = debut du run suivant (bandes jointives), sinon +1 pas
            if i < n:
                x1 = idx[i]
            else:
                x1 = idx[n - 1] + (idx[n - 1] - idx[n - 2] if n > 1 else 0)
            color = MODE_COLORS.get(m, '#999999')
            ax.axvspan(x0, x1, color=color, alpha=alpha, linewidth=0)
            if m not in handles:
                handles[m] = Patch(facecolor=color, alpha=min(alpha + 0.18, 1.0),
                                   label=MODE_LABELS.get(m, m))
            start = i
    return handles


def _normalize_days(day):
    """Normalise l'argument `day` en liste de (date, label).

    Accepte : None, une date str, un tuple (date, label), ou une LISTE d'items
    (chaque item etant une date str ou un tuple (date, label)).
    Convention : un tuple = UN jour labellise ; une liste = PLUSIEURS jours.
    """
    if day is None:
        return []
    if isinstance(day, str):
        return [(day, None)]
    if isinstance(day, tuple):
        return [(day[0], day[1] if len(day) > 1 else None)]
    out = []
    for it in day:
        if isinstance(it, str):
            out.append((it, None))
        else:
            out.append((it[0], it[1] if len(it) > 1 else None))
    return out


def export_tracking_trace(tilt_series, mode_series, true_angle_series,
                          sun_positions_df,
                          label,
                          day=None,
                          max_tilt_deg=90,
                          csv_dir='OUTPUTS',
                          fig_dir='OUTPUTS/GRAPHS',
                          show=False):
    """
    Exporte la trace du pilotage : CSV (période complète) + figure (journée).

    Parameters
    ----------
    tilt_series : pd.Series
        Tilt appliqué (degrés), index datetime — PV_Production.tiltY_per_year[year].
    mode_series : pd.Series or None
        Mode actif à chaque instant — PV_Production.mode_per_year[year].
        None si la simulation a tourné sans contrôleur de pilotage.
    true_angle_series : pd.Series or None
        Angle de tracking vrai (degrés) — PV_Production.true_angle_per_year[year].
    sun_positions_df : pd.DataFrame
        Positions solaires horaires avec colonnes 'elevation' et 'azimuth' —
        Sun_positions.sp_leapY ou sp_nonleapY selon l'année (même longueur que
        tilt_series ; l'alignement se fait par position, l'index de sp_* étant
        une année template).
    label : str
        Nom de la stratégie/simulation (utilisé dans les noms de fichiers).
    day : optional
        Jour(s) à tracer sur des figures. Formats acceptés :
          - une date 'YYYY-MM-DD'
          - un tuple (date, label)  ex. ('2020-07-15', 'ete')
          - une liste d'items, chacun étant une date str OU un tuple (date, label)
        Le label (ex. saison) apparaît dans le titre ET le nom du fichier PNG.
        Une figure est générée par jour. Si None, pas de figure (le CSV contient
        de toute façon toute la période).
    max_tilt_deg : float
        Limite MaxTiltAngle, tracée en pointillés sur la figure.
    csv_dir, fig_dir : str
        Dossiers de sortie (créés si nécessaire).
    show : bool
        Afficher la figure à l'écran (après sauvegarde).

    Returns
    -------
    (csv_path, fig_paths) : tuple
        csv_path : str, chemin du CSV.
        fig_paths : list of str, chemins des figures générées (vide si day=None).
    """
    if len(sun_positions_df) != len(tilt_series):
        raise ValueError(
            f"[PILOTAGE] Longueurs incohérentes : {len(tilt_series)} pas de temps "
            f"de tilt vs {len(sun_positions_df)} positions solaires")

    # ----------------- construction du tableau de trace -----------------
    trace = pd.DataFrame({
        'sun_elevation': sun_positions_df['elevation'].to_numpy(),
        'sun_azimuth': sun_positions_df['azimuth'].to_numpy(),
        'true_tracking_angle': (true_angle_series.to_numpy()
                                if true_angle_series is not None else np.nan),
        'applied_panel_tilt': tilt_series.to_numpy(),
        'mode': (mode_series.to_numpy()
                 if mode_series is not None else 'tracking_historique'),
    }, index=tilt_series.index)
    trace.index.name = 'datetime'

    # ----------------- export CSV (période complète) -----------------
    os.makedirs(csv_dir, exist_ok=True)
    safe_label = label.replace(' ', '_').replace('/', '-')
    csv_path = os.path.join(csv_dir, f'tracking_trace_{safe_label}.csv')
    trace.to_csv(csv_path, float_format='%.3f')
    print(f'[tracking_trace] CSV -> {csv_path}')

    # ----------------- figure(s) : une par jour demandé -----------------
    fig_paths = []
    jours = _normalize_days(day)
    if jours:
        os.makedirs(fig_dir, exist_ok=True)
        for date_str, saison in jours:
            fig_path = _plot_one_day(trace, date_str, saison, label, safe_label,
                                     has_true_angle=true_angle_series is not None,
                                     max_tilt_deg=max_tilt_deg,
                                     fig_dir=fig_dir, show=show)
            if fig_path is not None:
                fig_paths.append(fig_path)

    return csv_path, fig_paths


def _plot_one_day(trace, day, saison, label, safe_label, has_true_angle,
                  max_tilt_deg, fig_dir, show):
    """Trace la figure de vérification pour UN jour ('YYYY-MM-DD').

    `saison` est un mot-clé optionnel (ex. 'ete') ajouté au titre ET au nom du
    fichier. Retourne le chemin du PNG (ou None si le jour est absent de la trace
    — averti mais non bloquant pour ne pas interrompre l'export des autres jours)."""
    if day not in trace.index.strftime('%Y-%m-%d'):
        print(f'[tracking_trace] ATTENTION : aucune donnée pour le jour {day}, figure ignorée')
        return None

    day_trace = trace.loc[day]

    fig, ax = plt.subplots(figsize=(13, 6))
    hours = day_trace.index.hour + day_trace.index.minute / 60.0

    # Bandes de fond colorées par mode actif
    modes = day_trace['mode'].to_numpy()
    step = np.median(np.diff(hours)) if len(hours) > 1 else 1.0
    seen_modes = []
    for h, m in zip(hours, modes):
        color = MODE_COLORS.get(m, '#999999')
        lbl = f'mode : {m}' if m not in seen_modes else None
        ax.axvspan(h - step / 2, h + step / 2, color=color, alpha=0.12, label=lbl)
        if m not in seen_modes:
            seen_modes.append(m)

    # Courbes d'angles (axe gauche)
    ax.plot(hours, day_trace['applied_panel_tilt'], 'o-', color='black',
            linewidth=2, label='Tilt appliqué au panneau (°)')
    if has_true_angle:
        ax.plot(hours, day_trace['true_tracking_angle'], 's--',
                color='#ff7f0e', linewidth=1.5, label='Angle de tracking vrai (°)')
    ax.axhline(max_tilt_deg, color='grey', linestyle=':', linewidth=1)
    ax.axhline(-max_tilt_deg, color='grey', linestyle=':', linewidth=1,
               label=f'±MaxTiltAngle ({max_tilt_deg}°)')

    ax.set_xlabel('Heure de la journée')
    ax.set_ylabel('Angle du panneau (°)')
    ax.set_ylim(-100, 100)
    ax.set_xlim(0, 24)
    ax.grid(True, alpha=0.4)

    # Élévation solaire (axe droit)
    ax2 = ax.twinx()
    ax2.plot(hours, day_trace['sun_elevation'], '-', color='#1f77b4',
             linewidth=1.5, alpha=0.8, label='Élévation solaire (°)')
    ax2.set_ylabel('Élévation solaire (°)', color='#1f77b4')
    ax2.set_ylim(-10, 90)

    # Légende combinée des deux axes
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=9)

    # Titre et nom de fichier incluent le mot-cle de saison si fourni
    titre_jour = f'{saison} ({day})' if saison else day
    suffixe_fichier = f'{saison}_{day}' if saison else day
    ax.set_title(f'Pilotage des panneaux — {label} — {titre_jour}')
    plt.tight_layout()

    fig_path = os.path.join(fig_dir, f'tracking_trace_{safe_label}_{suffixe_fichier}.png')
    fig.savefig(fig_path, dpi=150)   # savefig AVANT show (backend MacOSX)
    print(f'[tracking_trace] Figure -> {fig_path}')

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig_path

# ============== [HUGO - PILOTAGE] FIN AJOUT ==============
