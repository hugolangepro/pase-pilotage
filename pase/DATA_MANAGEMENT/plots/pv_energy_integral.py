import matplotlib
# [HUGO - PILOTAGE] ne pas ecraser un backend 'Agg' deja force (mode batch)
if matplotlib.get_backend().lower() != 'agg':
    try:
        matplotlib.use('MacOSX')
    except Exception:
        pass
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os


def plot_pv_energy_integral(production, years=None, save_path=None,
                            mode_series=None):
    """
    Plot the cumulative PV energy production (integral of P_central over time).

    # ============== [HUGO - PILOTAGE] ==============
    # Si mode_series est fourni (pd.Series indexee par datetime des modes de
    # pilotage), on colore le fond par mode (tracking/anti-tracking/fixe) avec le
    # meme code couleur que les traces par jour -> on voit visuellement quand la
    # strategie freine la production (bandes rouges = anti-tracking).

    Each hourly timestep of P_central is in MW; summing over 1-hour steps yields MWh directly.

    Parameters
    ----------
    production : dict
        PV_Production.production — year strings as keys, hourly DataFrames as values.
        Each DataFrame must have a 'P_central' column (MW) and a datetime index.
    years : list of str, optional
        Subset of years to plot. Defaults to all available years.
    save_path : str, optional
        File path to save the figure (e.g. 'OUTPUTS/GRAPHS/pv_energy_integral.png').
        If None the figure is only displayed.

    Example
    -------
    from pase.DATA_MANAGEMENT.plots.pv_energy_integral import plot_pv_energy_integral
    plot_pv_energy_integral(PV_central.production)
    """
    if years is None:
        years = sorted(production.keys())

    fig, ax = plt.subplots(figsize=(12, 5))

    # ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
    mode_handles = {}
    if mode_series is not None:
        from pase.DATA_MANAGEMENT.plots.tracking_trace import draw_mode_bands
        mode_handles = draw_mode_bands(ax, mode_series)
    # ============== [HUGO - PILOTAGE] FIN AJOUT ==============

    for year in years:
        df = production[year]
        cumulative_mwh = df["P_central"].cumsum()
        ax.plot(df.index, cumulative_mwh, linewidth=2, label=str(year))

    # ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
    if mode_handles:
        ax.add_artist(ax.legend(handles=list(mode_handles.values()),
                                loc='lower right', fontsize=8, title='Pilotage'))
    # ============== [HUGO - PILOTAGE] FIN AJOUT ==============

    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative energy (MWh)")
    ax.set_title("Cumulative PV energy production")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", labelrotation=45)
    ax.legend()
    ax.grid(True)
    plt.tight_layout()

    if save_path:
        dir_name = os.path.dirname(save_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        fig.savefig(save_path)

    plt.show()
