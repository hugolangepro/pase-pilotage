import datetime
import matplotlib
# [HUGO - PILOTAGE] ne pas ecraser un backend 'Agg' deja force (mode batch)
if matplotlib.get_backend().lower() != 'agg':
    try:
        matplotlib.use('MacOSX')
    except Exception:
        pass
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import numpy as np
import os


# ─── Private helpers ──────────────────────────────────────────────────────────

def _pv_cumulative(production, year):
    """(datetime_index, cumulative MWh array) for one year."""
    df = production[str(year)]
    return df.index, df["P_central"].cumsum().values


# ============== [HUGO - PILOTAGE] ==============
# Deux structures de sortie de culture cohabitent :
#   - SIMPLE   : agro[annee][variable] = {date_str: array_spatial}  (serie journaliere)
#   - pySTICS  : agro[annee][variable] = array_spatial              (valeur finale par point)
# Les helpers ci-dessous gerent les DEUX -> les graphes marchent quel que soit le modele.

def _crop_array_at_year(agro_results, variable, year):
    """Renvoie (kind, array_spatial_finale) pour l'annee : kind='series' (SIMPLE, on prend
    la derniere date), 'final' (pySTICS, valeur finale directe) ou 'none' (variable absente)."""
    year_dict = agro_results.get(str(year), agro_results.get(year, {}))
    if variable not in year_dict:
        return 'none', None
    data = year_dict[variable]
    if isinstance(data, dict):            # SIMPLE : serie {date: array}
        if not data:
            return 'none', None
        last_date = sorted(data.keys(), key=lambda d: str(d))[-1]
        return 'series', np.asarray(data[last_date], dtype=float)
    return 'final', np.asarray(data, dtype=float)   # pySTICS : ndarray


def _crop_final_mean(agro_results, variable, year):
    """Moyenne spatiale de la valeur FINALE de la variable (fin de saison / rendement final).
    Marche pour SIMPLE (derniere date) comme pour pySTICS (valeur directe). None si absente."""
    kind, arr = _crop_array_at_year(agro_results, variable, year)
    if kind == 'none' or arr is None or arr.size == 0:
        return None
    return float(np.nanmean(arr))


def _biomass_curve(agro_results, variable, year):
    """(dates triees, moyennes spatiales) pour une variable EN SERIE (SIMPLE).
    Pour une variable sans serie temporelle (pySTICS) -> ([], []) : pas de courbe."""
    year_dict = agro_results.get(str(year), agro_results.get(year, {}))
    if variable not in year_dict or not isinstance(year_dict[variable], dict):
        return [], []
    dates, means = [], []
    for date_str, spatial_array in year_dict[variable].items():
        try:
            dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
        dates.append(dt)
        means.append(np.mean(spatial_array))
    if not dates:
        return [], []
    pairs = sorted(zip(dates, means), key=lambda x: x[0])
    dates, means = zip(*pairs)
    return list(dates), list(means)


def _first_common_year(simulations):
    sets = [set(s["production"].keys()) for s in simulations]
    common = sorted(sets[0].intersection(*sets[1:]))
    if not common:
        raise ValueError("No common year found across all simulations.")
    return common[0]


def _fmt_axis(ax, label_y, title):
    ax.set_ylabel(label_y)
    ax.set_title(title)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", labelrotation=45)
    ax.legend()
    ax.grid(True)


def _save(fig, save_path):
    if save_path:
        d = os.path.dirname(save_path)
        if d:
            os.makedirs(d, exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight")


# ─── Option 1 ─────────────────────────────────────────────────────────────────

def plot_comparison_overlay(simulations, variable="Biomass", unit="g/m²",
                            year=None, save_path=None):
    """
    Option 1 — Superimpose all simulations on two shared axes (energy / biomass).

    Parameters
    ----------
    simulations : list of dict
        Each dict: {'label': str, 'production': dict, 'agro_results': dict}
    variable : str
        Crop variable to plot. Default 'Biomass'.
    unit : str
        Y-axis unit for the crop variable.
    year : str or int, optional
        Year to display. Defaults to the first year common to all simulations.
    save_path : str, optional
        Path to save the figure.

    Example
    -------
    from pase.DATA_MANAGEMENT.plots.plot_comparison_graphs import plot_comparison_overlay

    simulations = [
        {'label': 'Tilt 20°', 'production': PV1.production, 'agro_results': results1},
        {'label': 'Tilt 35°', 'production': PV2.production, 'agro_results': results2},
    ]
    plot_comparison_overlay(simulations)
    """
    if year is None:
        year = _first_common_year(simulations)

    fig, (ax_pv, ax_bm) = plt.subplots(2, 1, figsize=(12, 8))

    for i, sim in enumerate(simulations):
        lbl = sim["label"]
        times, energy = _pv_cumulative(sim["production"], year)
        ax_pv.plot(times, energy, linewidth=2, label=lbl, color=f"C{i}")

        dates, means = _biomass_curve(sim["agro_results"], variable, year)
        if dates:
            ax_bm.plot(dates, means, linewidth=2, label=lbl, color=f"C{i}")

    _fmt_axis(ax_pv, "Cumulative energy (MWh)", f"PV energy production — {year}")
    _fmt_axis(ax_bm, f"{variable} ({unit})", f"{variable} — {year}")
    plt.tight_layout()
    _save(fig, save_path)
    plt.show()


# ─── Option 2 ─────────────────────────────────────────────────────────────────

def plot_comparison_grid(simulations, variable="Biomass", unit="g/m²",
                         year=None, save_path=None):
    """
    Option 2 — 2 × N grid: one column per simulation, rows = energy / biomass.

    All columns share the same Y scale (sharey='row') for easy visual comparison.

    Parameters
    ----------
    simulations : list of dict
        Each dict: {'label': str, 'production': dict, 'agro_results': dict}
    variable : str
        Crop variable to plot.
    unit : str
        Y-axis unit for the crop variable.
    year : str or int, optional
        Year to display. Defaults to the first common year.
    save_path : str, optional
        Path to save the figure.
    """
    if year is None:
        year = _first_common_year(simulations)

    n = len(simulations)
    fig, axes = plt.subplots(2, n, figsize=(5 * n, 8), sharey="row")
    if n == 1:
        axes = axes.reshape(2, 1)

    # ============== [HUGO - PILOTAGE] ==============
    # Bandes de mode de pilotage (meme code couleur que les traces par jour) sur
    # chaque colonne -> on visualise, par strategie, quand le tracking/anti-tracking
    # est actif, ce qui justifie la forme des courbes.
    from pase.DATA_MANAGEMENT.plots.tracking_trace import draw_mode_bands
    mode_handles_global = {}

    for col, sim in enumerate(simulations):
        color = f"C{col}"
        mode_series = sim.get("modes", {}).get(str(year)) if sim.get("modes") else None

        times, energy = _pv_cumulative(sim["production"], year)
        axes[0, col].plot(times, energy, linewidth=2, color=color)
        if mode_series is not None:
            mode_handles_global.update(draw_mode_bands(axes[0, col], mode_series))
        axes[0, col].set_title(sim["label"])
        axes[0, col].xaxis.set_major_locator(mdates.MonthLocator())
        axes[0, col].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        axes[0, col].tick_params(axis="x", labelrotation=45)
        axes[0, col].grid(True)

        dates, means = _biomass_curve(sim["agro_results"], variable, year)
        if dates:
            axes[1, col].plot(dates, means, linewidth=2, color=color)
        if mode_series is not None and dates:
            xlim = axes[1, col].get_xlim()
            draw_mode_bands(axes[1, col], mode_series)
            axes[1, col].set_xlim(xlim)
        axes[1, col].xaxis.set_major_locator(mdates.MonthLocator())
        axes[1, col].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        axes[1, col].tick_params(axis="x", labelrotation=45)
        axes[1, col].grid(True)

    if mode_handles_global:
        axes[0, -1].legend(handles=list(mode_handles_global.values()),
                           loc='lower right', fontsize=8, title='Pilotage')

    axes[0, 0].set_ylabel("Cumulative energy (MWh)")
    axes[1, 0].set_ylabel(f"{variable} ({unit})")
    fig.suptitle(f"Simulation comparison — {year}", fontsize=14)
    plt.tight_layout()
    _save(fig, save_path)
    plt.show()


# ─── Option 3 ─────────────────────────────────────────────────────────────────

def plot_comparison_bars(simulations, variable="Biomass", unit="g/m²",
                         save_path=None):
    """
    Option 3 — Bar chart of annual totals: one bar per simulation.

    PV: mean annual energy (MWh/year) averaged across all simulated years.
    Biomass: mean end-of-season value averaged across all simulated years.

    Parameters
    ----------
    simulations : list of dict
        Each dict: {'label': str, 'production': dict, 'agro_results': dict}
    variable : str
        Crop variable to summarise.
    unit : str
        Y-axis unit for the crop variable.
    save_path : str, optional
        Path to save the figure.
    """
    labels = [s["label"] for s in simulations]
    pv_means, bm_means = [], []

    for sim in simulations:
        yearly_pv = [sim["production"][y]["P_central"].sum()
                     for y in sim["production"]]
        pv_means.append(np.mean(yearly_pv))

        yearly_bm = []
        for y in sim["agro_results"]:
            _, means = _biomass_curve(sim["agro_results"], variable, y)
            if means:
                yearly_bm.append(means[-1])
        bm_means.append(np.mean(yearly_bm) if yearly_bm else 0)

    x = np.arange(len(labels))
    colors = [f"C{i}" for i in range(len(labels))]

    fig, (ax_pv, ax_bm) = plt.subplots(1, 2, figsize=(12, 5))

    bars = ax_pv.bar(x, pv_means, color=colors, width=0.6)
    ax_pv.set_xticks(x)
    ax_pv.set_xticklabels(labels, rotation=20, ha="right")
    ax_pv.set_ylabel("Mean annual energy (MWh/year)")
    ax_pv.set_title("Total PV energy production")
    ax_pv.bar_label(bars, fmt="%.1f", padding=3)
    ax_pv.grid(axis="y")

    bars = ax_bm.bar(x, bm_means, color=colors, width=0.6)
    ax_bm.set_xticks(x)
    ax_bm.set_xticklabels(labels, rotation=20, ha="right")
    ax_bm.set_ylabel(f"Mean end-of-season {variable} ({unit})")
    ax_bm.set_title(f"End-of-season {variable}")
    ax_bm.bar_label(bars, fmt="%.1f", padding=3)
    ax_bm.grid(axis="y")

    plt.tight_layout()
    _save(fig, save_path)
    plt.show()


# ─── Option 1 + 3 combined ────────────────────────────────────────────────────

def plot_comparison_combined(simulations, variable="Biomass", unit="g/m²",
                             year=None, save_path=None):
    """
    Combined view: Option 1 (curves) on top + Option 3 (bar totals) on bottom.

    Layout
    ------
    Row 0 : Cumulative PV energy curves  (all sims overlaid, full width)
    Row 1 : Cumulative biomass curves    (all sims overlaid, full width)
    Row 2 : PV bar chart  |  Biomass bar chart

    Parameters
    ----------
    simulations : list of dict
        Each dict: {'label': str, 'production': dict, 'agro_results': dict}
    variable : str
        Crop variable to plot/summarise.
    unit : str
        Y-axis unit for the crop variable.
    year : str or int, optional
        Year shown in the curve panels. Defaults to the first common year.
    save_path : str, optional
        Path to save the figure.
    """
    if year is None:
        year = _first_common_year(simulations)

    labels = [s["label"] for s in simulations]
    colors = [f"C{i}" for i in range(len(simulations))]

    fig = plt.figure(figsize=(14, 13))
    gs = gridspec.GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1], hspace=0.5)

    ax_pv_curve = fig.add_subplot(gs[0, :])
    ax_bm_curve = fig.add_subplot(gs[1, :])
    ax_pv_bar   = fig.add_subplot(gs[2, 0])
    ax_bm_bar   = fig.add_subplot(gs[2, 1])

    pv_means, bm_means = [], []

    for i, sim in enumerate(simulations):
        lbl, color = sim["label"], colors[i]

        times, energy = _pv_cumulative(sim["production"], year)
        ax_pv_curve.plot(times, energy, linewidth=2, label=lbl, color=color)

        dates, means = _biomass_curve(sim["agro_results"], variable, year)
        if dates:
            ax_bm_curve.plot(dates, means, linewidth=2, label=lbl, color=color)

        yearly_pv = [sim["production"][y]["P_central"].sum()
                     for y in sim["production"]]
        pv_means.append(np.mean(yearly_pv))

        yearly_bm = []
        for y in sim["agro_results"]:
            _, m = _biomass_curve(sim["agro_results"], variable, y)
            if m:
                yearly_bm.append(m[-1])
        bm_means.append(np.mean(yearly_bm) if yearly_bm else 0)

    _fmt_axis(ax_pv_curve, "Cumulative energy (MWh)", f"PV energy production — {year}")
    _fmt_axis(ax_bm_curve, f"{variable} ({unit})", f"{variable} — {year}")

    x = np.arange(len(labels))
    bars = ax_pv_bar.bar(x, pv_means, color=colors, width=0.6)
    ax_pv_bar.set_xticks(x)
    ax_pv_bar.set_xticklabels(labels, rotation=20, ha="right")
    ax_pv_bar.set_ylabel("Mean annual energy (MWh/year)")
    ax_pv_bar.set_title("Annual totals — PV")
    ax_pv_bar.bar_label(bars, fmt="%.1f", padding=3)
    ax_pv_bar.grid(axis="y")

    bars = ax_bm_bar.bar(x, bm_means, color=colors, width=0.6)
    ax_bm_bar.set_xticks(x)
    ax_bm_bar.set_xticklabels(labels, rotation=20, ha="right")
    ax_bm_bar.set_ylabel(f"Mean end-of-season {variable} ({unit})")
    ax_bm_bar.set_title(f"Annual totals — {variable}")
    ax_bm_bar.bar_label(bars, fmt="%.1f", padding=3)
    ax_bm_bar.grid(axis="y")

    fig.suptitle("Simulation comparison", fontsize=15, y=1.01)
    _save(fig, save_path)
    plt.show()


# ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
# ─── Classement (ranking) des pilotages : énergie PV vs biomasse ──────────────

def _perf_par_pilotage(simulations, variable):
    """Renvoie (labels, energie_moy [MWh/an], biomasse_fin_moy) par simulation."""
    labels, energies, biomasses = [], [], []
    for sim in simulations:
        labels.append(sim["label"])
        yearly_pv = [sim["production"][y]["P_central"].sum() for y in sim["production"]]
        energies.append(float(np.mean(yearly_pv)) if yearly_pv else 0.0)
        # valeur finale (SIMPLE : derniere date ; pySTICS : valeur finale directe)
        yearly_bm = []
        for y in sim["agro_results"]:
            v = _crop_final_mean(sim["agro_results"], variable, y)
            if v is not None:
                yearly_bm.append(v)
        biomasses.append(float(np.mean(yearly_bm)) if yearly_bm else 0.0)
    return labels, energies, biomasses


def plot_comparison_ranking(simulations, variable="Biomass", unit="g/m²", save_path=None):
    """Classement visuel des pilotages : meilleurs pour l'ENERGIE PV vs meilleurs
    pour la BIOMASSE, avec des lignes reliant chaque pilotage entre les deux
    classements (bump chart) -> on voit d'un coup d'oeil l'ordre et l'arbitrage
    energie/agricole (un pilotage 1er en energie peut etre dernier en biomasse).

    Parameters
    ----------
    simulations : list of dict {'label', 'production', 'agro_results'}
    variable : str
        Variable de culture pour le classement biomasse.
    unit : str
    save_path : str, optional
    """
    labels, energies, biomasses = _perf_par_pilotage(simulations, variable)
    n = len(labels)
    colors = [f"C{i}" for i in range(n)]

    # rangs (1 = meilleur) ; ordre decroissant
    ordre_e = sorted(range(n), key=lambda i: energies[i], reverse=True)
    ordre_b = sorted(range(n), key=lambda i: biomasses[i], reverse=True)
    rang_e = {idx: r + 1 for r, idx in enumerate(ordre_e)}
    rang_b = {idx: r + 1 for r, idx in enumerate(ordre_b)}

    fig, ax = plt.subplots(figsize=(11, 0.9 * n + 2.5))
    x_e, x_b = 0.0, 1.0
    for i in range(n):
        ye, yb = rang_e[i], rang_b[i]
        ax.plot([x_e, x_b], [ye, yb], '-', color=colors[i], linewidth=2.5,
                marker='o', markersize=11, zorder=2)
        # etiquettes : nom + valeur a chaque extremite
        ax.annotate(f'{rang_e[i]}. {labels[i]}\n{energies[i]:.2f} MWh',
                    (x_e, ye), xytext=(-12, 0), textcoords='offset points',
                    ha='right', va='center', fontsize=9, color=colors[i])
        ax.annotate(f'{rang_b[i]}. {labels[i]}\n{biomasses[i]:.1f} {unit}',
                    (x_b, yb), xytext=(12, 0), textcoords='offset points',
                    ha='left', va='center', fontsize=9, color=colors[i])

    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(n + 0.6, 0.4)          # rang 1 en haut
    ax.set_xticks([x_e, x_b])
    ax.set_xticklabels(['MEILLEURS EN\nÉNERGIE PV', 'MEILLEURS EN\nBIOMASSE'],
                       fontweight='bold')
    ax.set_yticks(range(1, n + 1))
    ax.set_ylabel('Rang (1 = meilleur)')
    ax.set_title('Classement des pilotages — énergie PV vs biomasse')
    for spine in ('top', 'right', 'left'):
        ax.spines[spine].set_visible(False)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    _save(fig, save_path)
    plt.show()
    return save_path


# ─── GRID des traces de pilotage : lignes = saisons, colonnes = pilotages ──────

def _cellule_trace(ax, jour_df, max_tilt_deg):
    """Trace, dans un sous-graphe, la trace de pilotage d'un jour :
    bandes de mode (par heure) + tilt applique + angle vrai + elevation solaire.
    Retourne l'ensemble des modes rencontres (pour la legende globale)."""
    from pase.DATA_MANAGEMENT.plots.tracking_trace import MODE_COLORS
    hours = jour_df.index.hour + jour_df.index.minute / 60.0
    modes = jour_df['mode'].to_numpy() if 'mode' in jour_df else np.array([None] * len(jour_df))
    step = np.median(np.diff(hours)) if len(hours) > 1 else 1.0
    modes_vus = set()
    for h, m in zip(hours, modes):
        ax.axvspan(h - step / 2, h + step / 2,
                   color=MODE_COLORS.get(m, '#999999'), alpha=0.13, linewidth=0)
        modes_vus.add(m)
    ax.plot(hours, jour_df['tilt'].to_numpy(), 'o-', color='black',
            linewidth=1.6, markersize=3)
    if 'true' in jour_df and jour_df['true'].notna().any():
        ax.plot(hours, jour_df['true'].to_numpy(), '--', color='#ff7f0e', linewidth=1.2)
    if 'elev' in jour_df and jour_df['elev'].notna().any():
        ax.plot(hours, jour_df['elev'].to_numpy(), '-', color='#1f77b4',
                linewidth=1.1, alpha=0.7)
    ax.axhline(max_tilt_deg, color='grey', linestyle=':', linewidth=0.8)
    ax.axhline(-max_tilt_deg, color='grey', linestyle=':', linewidth=0.8)
    ax.set_xlim(0, 24)
    ax.set_ylim(-100, 100)
    ax.grid(True, alpha=0.3)
    return modes_vus


def plot_comparison_tracking_grid(traces_grid, jours, max_tilt_deg=90, save_path=None):
    """Grille des traces de pilotage : une LIGNE par jour (saison), une COLONNE par
    pilotage. Chaque cellule reprend la trace de la journee (tilt applique, angle de
    tracking vrai, elevation solaire, bandes de mode) — l'equivalent des figures du
    dossier "2 - graphiques par pilotage", rassemblees comme comparison_grid.png.

    Parameters
    ----------
    traces_grid : list of dict
        Un dict par pilotage : {'label': str,
                                'trace_df': pd.DataFrame index datetime avec colonnes
                                            'tilt', 'true', 'mode', 'elev'}
    jours : list of (date 'YYYY-MM-DD', label saison)
    max_tilt_deg : float
    save_path : str, optional
    """
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    from pase.DATA_MANAGEMENT.plots.tracking_trace import MODE_COLORS, MODE_LABELS

    n_rows, n_cols = len(jours), len(traces_grid)
    if n_rows == 0 or n_cols == 0:
        return None
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.6 * n_cols, 2.8 * n_rows),
                             sharex=True, sharey=True, squeeze=False)

    modes_globaux = set()
    for i, (date_str, saison) in enumerate(jours):
        for j, tr in enumerate(traces_grid):
            ax = axes[i][j]
            df = tr['trace_df']
            try:
                jour_df = df.loc[date_str]
            except KeyError:
                ax.text(0.5, 0.5, 'pas de données', ha='center', va='center',
                        transform=ax.transAxes, fontsize=8, color='grey')
                continue
            if len(jour_df) == 0:
                continue
            modes_globaux |= _cellule_trace(ax, jour_df, max_tilt_deg)
            if i == 0:
                ax.set_title(tr['label'], fontsize=10)
            if j == 0:
                ax.set_ylabel(f'{saison}\n({date_str[5:]})\ntilt (°)', fontsize=9)

    for j in range(n_cols):
        axes[-1][j].set_xlabel("heure")

    # légende globale
    handles = [Line2D([0], [0], color='black', marker='o', markersize=4, label='tilt appliqué (°)'),
               Line2D([0], [0], color='#ff7f0e', linestyle='--', label='angle de tracking vrai (°)'),
               Line2D([0], [0], color='#1f77b4', alpha=0.7, label='élévation solaire (°)')]
    for m in modes_globaux:
        if m in MODE_COLORS:
            handles.append(Patch(facecolor=MODE_COLORS[m], alpha=0.3,
                                 label=MODE_LABELS.get(m, m)))
    fig.legend(handles=handles, loc='upper center', ncol=len(handles),
               fontsize=8, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle('Traces de pilotage — lignes = saisons, colonnes = pilotages',
                 fontsize=13, y=1.02)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    _save(fig, save_path)
    plt.show()
    return save_path
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============
