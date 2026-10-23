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
import numpy as np
import os


def plot_biomass_integral(agro_results, variable="Biomass", unit="g/m²", years=None,
                          save_path=None, mode_series=None):
    """
    Plot the accumulated crop variable (biomass or yield) over the growing season.

    # ============== [HUGO - PILOTAGE] ==============
    # Si mode_series est fourni (pd.Series datetime des modes de pilotage), on
    # colore le fond par mode avec le meme code couleur que les traces par jour
    # -> on voit visuellement pendant quelles periodes la strategie laisse plus
    # de lumiere au sol (bandes rouges = anti-tracking).

    The SIMPLE crop model accumulates biomass at each daily step, so the plotted curve
    directly represents the integral over the season. The spatial mean across all grid
    points is computed for each date.

    Parameters
    ----------
    agro_results : dict
        Output of run_crop_simu — year strings as keys, variable dicts as values.
        Structure: agro_results[year][variable][date_str] = spatial_array (numpy).
    variable : str
        Crop variable to plot. One of: 'Biomass', 'Biomass_rate', 'Dry_yield',
        'Fresh_yield', 'LAI', 'Height'. Default 'Biomass'.
    unit : str
        Y-axis unit label. Default 'g/m²'.
    years : list of str, optional
        Subset of years to plot. Defaults to all available years.
    save_path : str, optional
        File path to save the figure (e.g. 'OUTPUTS/GRAPHS/biomass_integral.png').
        If None the figure is only displayed.

    Example
    -------
    from pase.DATA_MANAGEMENT.plots.biomass_integral import plot_biomass_integral
    plot_biomass_integral(agro_results)
    plot_biomass_integral(agro_results, variable='Fresh_yield', unit='g/m²')
    """
    if years is None:
        years = sorted(agro_results.keys())

    fig, ax = plt.subplots(figsize=(12, 5))

    for year in years:
        year_dict = agro_results[year]
        if variable not in year_dict:
            print(f"Variable '{variable}' not found in year {year}, skipping.")
            continue

        var_dict = year_dict[variable]
        # ============== [HUGO - PILOTAGE] ==============
        # pySTICS : la variable est un ndarray (valeur finale par point, pas de serie).
        # -> on trace la valeur finale moyenne comme ligne horizontale annotee.
        if not isinstance(var_dict, dict):
            val = float(np.nanmean(np.asarray(var_dict, dtype=float)))
            ax.axhline(val, linewidth=2, label=f'{year} (valeur finale {val:.2f})')
            ax.annotate(f'{val:.2f}', xy=(0.98, val), xycoords=('axes fraction', 'data'),
                        ha='right', va='bottom', fontsize=9)
            continue
        # ============== FIN ==============
        dates, means = [], []
        for date_str, spatial_array in var_dict.items():
            try:
                dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
            dates.append(dt)
            means.append(np.mean(spatial_array))

        if not dates:
            continue

        pairs = sorted(zip(dates, means), key=lambda x: x[0])
        dates, means = zip(*pairs)

        ax.plot(dates, means, linewidth=2, label=str(year))

    # ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
    # Bandes de mode APRES les courbes, en figeant le xlim sur la saison
    # (les modes couvrent l'annee entiere, on ne veut pas etirer l'axe).
    mode_handles = {}
    if mode_series is not None:
        from pase.DATA_MANAGEMENT.plots.tracking_trace import draw_mode_bands
        xlim = ax.get_xlim()
        mode_handles = draw_mode_bands(ax, mode_series)
        ax.set_xlim(xlim)
    # ============== [HUGO - PILOTAGE] FIN AJOUT ==============

    ax.set_xlabel("Date")
    ax.set_ylabel(f"{variable} ({unit})")
    ax.set_title(f"Cumulative {variable} over the growing season")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", labelrotation=45)
    ax.legend()
    # ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
    if mode_handles:
        ax.add_artist(ax.legend(handles=list(mode_handles.values()),
                                loc='lower right', fontsize=8, title='Pilotage'))
    # ============== [HUGO - PILOTAGE] FIN AJOUT ==============
    ax.grid(True)
    plt.tight_layout()

    if save_path:
        dir_name = os.path.dirname(save_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        fig.savefig(save_path)

    plt.show()
