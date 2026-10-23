import glob
import os
import pickle


# ============== [HUGO - PILOTAGE] DEBUT MODIF ==============
# Ajout du paramètre optionnel `pilotage` : dictionnaire décrivant la stratégie
# de pilotage utilisée + les séries de tilt/mode, sauvegardé dans le pickle pour
# pouvoir retracer/comparer les stratégies a posteriori. Rétro-compatible :
# les anciens pickles n'ont simplement pas la clé 'pilotage'.
# ============== [HUGO - PILOTAGE] FIN MODIF ==============
def save_simulation(label, production, agro_results, output_dir='OUTPUTS/simulations',
                    pilotage=None):
    """
    Save one simulation's results to disk so it can be reloaded for comparison
    without re-running the full simulation.

    Parameters
    ----------
    label : str
        Human-readable name for this simulation (e.g. 'Tilt 20°', 'Tracking 1ax').
        Used as filename and as legend label in comparison plots.
    production : dict
        PV_Production.production — year strings as keys, hourly DataFrames as values.
    agro_results : dict
        Output of run_crop_simu — year strings as keys, variable dicts as values.
    output_dir : str
        Directory where the file is saved. Created if it does not exist.

    Returns
    -------
    str
        Path to the saved file.

    Example
    -------
    from pase.DATA_MANAGEMENT.simulation_results import save_simulation

    save_simulation('Tilt 20°', PV_central.production, agro_results)
    """
    os.makedirs(output_dir, exist_ok=True)
    safe_label = (label.replace(' ', '_')
                       .replace('°', 'deg')
                       .replace('/', '-')
                       .replace('\\', '-'))
    path = os.path.join(output_dir, f'{safe_label}.pkl')
    data = {'label': label, 'production': production, 'agro_results': agro_results}
    # ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
    if pilotage is not None:
        data['pilotage'] = pilotage
    # ============== [HUGO - PILOTAGE] FIN AJOUT ==============
    with open(path, 'wb') as f:
        pickle.dump(data, f)
    print(f'[save_simulation] "{label}" → {path}')
    return path


def load_simulation(path):
    """
    Load one simulation from a .pkl file saved by save_simulation.

    Parameters
    ----------
    path : str
        Path to the .pkl file.

    Returns
    -------
    dict
        {'label': str, 'production': dict, 'agro_results': dict}
    """
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_all_simulations(output_dir='OUTPUTS/simulations'):
    """
    Load every .pkl file found in output_dir, sorted alphabetically.

    Parameters
    ----------
    output_dir : str
        Directory that contains the .pkl files.

    Returns
    -------
    list of dict
        List of {'label', 'production', 'agro_results'} dicts, ready to pass
        directly to any plot_comparison_* function.

    Example
    -------
    from pase.DATA_MANAGEMENT.simulation_results import load_all_simulations

    simulations = load_all_simulations()
    """
    paths = sorted(glob.glob(os.path.join(output_dir, '*.pkl')))
    if not paths:
        raise FileNotFoundError(f'No .pkl files found in {output_dir}')
    simulations = []
    for p in paths:
        sim = load_simulation(p)
        sim['label'] = os.path.splitext(os.path.basename(p))[0]
        simulations.append(sim)
    print(f'[load_all_simulations] {len(simulations)} simulation(s) loaded from {output_dir}')
    for s in simulations:
        print(f'  · {s["label"]}')
    return simulations
