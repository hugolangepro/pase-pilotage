# ============== [HUGO - PILOTAGE] DEBUT AJOUT (FICHIER ENTIEREMENT NOUVEAU) ==============
#
# Génération de la "trace documentaire" d'une simulation de comparaison de
# politiques de pilotage :
#   - arborescence de sortie SIMU_<N>_<mots-cles>/ (numéro auto-incrémenté)
#     avec des sous-dossiers clairs (graphes de comparaison, graphes par
#     pilotage, CSV de trace, fichiers pkl) ;
#   - un document descriptif des inputs (INFOS_SIMULATION.md) : les infos
#     importantes en avant, puis TOUS les inputs détaillés à la suite ;
#   - un fichier d'avis à remplir (AVIS_SIMULATION.txt).
#
# Utilisé par run_comparaison_pilotage.py.
#
# Auteur : Hugo (stage pilotage agrivoltaïque) — 2026

import datetime
import os
import platform
import re

from pase.PHOTOVOLTAICS.pilotage import PilotageStrategy

# Noms des sous-dossiers de l'arborescence de sortie (modifiables ici)
SOUS_DOSSIERS = {
    'comparaison': '1 - graphiques de comparaison',
    'par_pilotage': '2 - graphiques par pilotage',
    'csv_trace': '3 - csv trace tracking',
    'pkl': '4 - fichiers pkl',
}


# --------------------------------------------------------------------------- #
#  Arborescence SIMU_<N>_<mots-cles>/
# --------------------------------------------------------------------------- #
def prochain_numero_simu(base_dir):
    """Renvoie le prochain numéro de simulation (max existant + 1)."""
    if not os.path.isdir(base_dir):
        return 1
    nums = []
    for name in os.listdir(base_dir):
        m = re.match(r'SIMU_(\d+)', name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def mots_cles_auto(loc, pv_params, strategies_infos, crop_config=None):
    """Construit des mots-clés pertinents à partir des infos importantes.

    Inclut : lieu, année(s), nombre de panneaux, modèle de culture, nombre de
    politiques de pilotage et MaxTiltAngle.
    """
    an1 = loc.get('SimulationStartingYear')
    an2 = loc.get('SimulationEndingYear')
    annees = f'{an1}' if an1 == an2 else f'{an1}-{an2}'
    lieu = str(loc.get('LocationName', 'lieu')).strip().replace(' ', '')
    n_strat = len(strategies_infos)
    max_tilt = pv_params.get('MaxTiltAngle', 90)
    n_panels = (pv_params.get('NumberOfPanelsX', 1) * pv_params.get('NumberOfPanelsY', 1)
                * pv_params.get('NumberOfPVBlocksX', 1) * pv_params.get('NumberOfPVBlocksY', 1))
    crop = ''
    if crop_config is not None:
        crop = f'_{crop_config.get("CropModel", "")}'
    return (f'{lieu}_{annees}_{n_panels}pan{crop}'
            f'_{n_strat}pilotages_maxtilt{int(max_tilt)}')


def creer_arborescence_simu(base_dir, mots_cles, noms_pilotages):
    """Crée SIMU_<N>_<mots-cles>/ et ses sous-dossiers.

    Returns
    -------
    dict : {'root', 'numero', 'comparaison', 'par_pilotage', 'csv_trace', 'pkl',
            'par_pilotage_dirs': {nom_pilotage: chemin}}
    """
    numero = prochain_numero_simu(base_dir)
    safe = re.sub(r'[^0-9A-Za-z_\-]', '', mots_cles.replace(' ', '_'))
    root = os.path.join(base_dir, f'SIMU_{numero}_{safe}')
    os.makedirs(root, exist_ok=True)

    chemins = {'root': root, 'numero': numero}
    for cle, nom in SOUS_DOSSIERS.items():
        d = os.path.join(root, nom)
        os.makedirs(d, exist_ok=True)
        chemins[cle] = d

    # un sous-dossier par politique de pilotage dans "2 - graphiques par pilotage"
    chemins['par_pilotage_dirs'] = {}
    for nom in noms_pilotages:
        d = os.path.join(chemins['par_pilotage'], nom)
        os.makedirs(d, exist_ok=True)
        chemins['par_pilotage_dirs'][nom] = d

    return chemins


# --------------------------------------------------------------------------- #
#  Formatage des stratégies de pilotage
# --------------------------------------------------------------------------- #
def _fmt_regle(regle):
    """Résumé lisible d'une règle de pilotage."""
    bouts = []
    if 'date_start' in regle:
        bouts.append(f"du {regle['date_start']} au {regle['date_end']}")
    if 'hour_start' in regle:
        bouts.append(f"de {regle['hour_start']}h à {regle['hour_end']}h")
    periode = ', '.join(bouts) if bouts else "toute l'année"
    mode = regle.get('mode', '?')
    if mode == 'fixed':
        mode = f"fixed ({regle.get('fixed_angle', '?')}°)"
    nom = regle.get('name', '')
    prefixe = f"[{nom}] " if nom else ""
    return f"{prefixe}{periode} → {mode}"


def infos_strategies(chemins_yaml):
    """Charge chaque stratégie et renvoie une liste de dicts descriptifs."""
    infos = []
    for chemin in chemins_yaml:
        strat = PilotageStrategy.from_yaml(chemin)
        with open(chemin, 'r') as f:
            brut = f.read()
        infos.append({
            'name': strat.name,
            'description': strat.description,
            'default_mode': strat.default_mode,
            'rules': strat.rules,
            'fichier': chemin,
            'yaml_brut': brut,
        })
    return infos


# --------------------------------------------------------------------------- #
#  Document descriptif des inputs
#
#  Source UNIQUE de contenu : _blocs_description() construit une liste de "blocs"
#  (titre, puce, dict, code...). Deux writers la rendent ensuite :
#    - ecrire_description_inputs() -> fichier Markdown (.md)
#    - ecrire_description_pdf()     -> fichier PDF (.pdf, via matplotlib)
#  Ainsi les deux versions ne peuvent pas diverger.
# --------------------------------------------------------------------------- #
def _blocs_description(loc, av, pv_module, crop_config, strategies_infos, simu_nom):
    """Construit la liste de blocs decrivant la simulation.

    Chaque bloc est un tuple :
      ('h1'|'h2'|'h3', texte)      -> titre
      ('bullet', texte)            -> puce niveau 1 (peut contenir **gras**)
      ('bullet2', texte)          -> puce niveau 2
      ('text', texte)              -> ligne simple
      ('sep',)                     -> separateur horizontal
      ('dict', titre, dict)        -> tableau cle/valeur complet
      ('code', titre, texte)       -> bloc de code (yaml brut)
    """
    n_panels = (av.get('NumberOfPanelsX', 1) * av.get('NumberOfPanelsY', 1)
                * av.get('NumberOfPVBlocksX', 1) * av.get('NumberOfPVBlocksY', 1))
    p_crete = pv_module.get('Panel_Peak_Power', 0)
    p_installee_kwc = n_panels * p_crete / 1000.0
    surf_panneau = pv_module.get('PanelDimensionX', 0) * pv_module.get('PanelDimensionY', 0)
    surf_pv_totale = n_panels * surf_panneau
    try:
        gcr_x = (pv_module.get('PanelDimensionX', 0) * av.get('NumberOfPanelsX', 1)
                 / av.get('RepetitionDistanceOfPVBlocksX', 1))
    except ZeroDivisionError:
        gcr_x = float('nan')
    nx = int(round((loc.get('Xmax_InterestZone', 0) - loc.get('Xmin_InterestZone', 0))
                   / loc.get('dX_InterestZone', 1))) + 1
    ny = int(round((loc.get('Ymax_InterestZone', 0) - loc.get('Ymin_InterestZone', 0))
                   / loc.get('dY_InterestZone', 1))) + 1
    n_points_zone = nx * ny
    an1, an2 = loc.get('SimulationStartingYear'), loc.get('SimulationEndingYear')
    annees = f'{an1}' if an1 == an2 else f'{an1} à {an2}'
    niveaux_soleil = {1: '1 (jour moyen/mois)', 2: '2 (jour moyen/semaine)',
                      3: '3 (chaque jour)'}

    B = []
    B.append(('h1', 'Fiche de simulation'))
    B.append(('subtitle', simu_nom))
    B.append(('text', f'Généré le {datetime.datetime.now():%Y-%m-%d %H:%M}'))
    B.append(('sep',))
    B.append(('h2', '1. Résumé (infos importantes)'))

    B.append(('h3', 'Localisation & période'))
    B.append(('bullet', f'**Lieu** : {loc.get("LocationName")} '
                        f'(lat {loc.get("Latitude")}, lon {loc.get("Longitude")}, '
                        f'alt {loc.get("Altitude")} m)'))
    B.append(('bullet', f'**Fuseau horaire** : {loc.get("TimeZone")}'))
    B.append(('bullet', f'**Années simulées** : {annees}'))
    B.append(('bullet', f'**Source météo** : '
                        f'{"PVGIS" if loc.get("WeatherDataOption") == 1 else "fichier CSV"}'))

    B.append(('h3', 'Structure du parc PV'))
    B.append(('bullet', f'**Nombre total de panneaux** : {n_panels}'))
    B.append(('bullet', f'**Blocs** : {av.get("NumberOfPVBlocksX")} (X) × '
                        f'{av.get("NumberOfPVBlocksY")} (Y)'))
    B.append(('bullet', f'**Panneaux par bloc** : {av.get("NumberOfPanelsX")} (X) × '
                        f'{av.get("NumberOfPanelsY")} (Y)'))
    B.append(('bullet', f'**Distance entre blocs** : {av.get("RepetitionDistanceOfPVBlocksX")} m (X) / '
                        f'{av.get("RepetitionDistanceOfPVBlocksY")} m (Y)'))
    B.append(('bullet', f'**Distance entre panneaux** : {av.get("RepetitionDistanceOfPanelsX")} m (X) / '
                        f'{av.get("RepetitionDistanceOfPanelsY")} m (Y)'))
    B.append(('bullet', f'**Azimut de la centrale** : {av.get("CentralAzimut")}° '
                        f'(0=N, 90=E, 180=S, 270=O)'))
    B.append(('bullet', f'**Hauteur de l\'axe** : {av.get("Height")} m — '
                        f'**Charnière (Hinge)** : {av.get("Hinge")}'))
    B.append(('bullet', f'**Axe de rotation (tracking)** : '
                        f'{"oui" if av.get("RotationAxisNumber") == 1 else "non (tilt fixe)"} '
                        f'— **TiltY fixe** : {av.get("TiltY")}°'))
    B.append(('bullet', f'**Angle max de pilotage (MaxTiltAngle)** : {av.get("MaxTiltAngle", 90)}° '
                        f'(90 = sans limite)'))
    B.append(('bullet', f'**GCR (X)** : {gcr_x:.3f}'))

    B.append(('h3', 'Module PV & puissance installée'))
    B.append(('bullet', f'**Dimensions panneau** : {pv_module.get("PanelDimensionX")} × '
                        f'{pv_module.get("PanelDimensionY")} m (surface {surf_panneau:.3f} m²)'))
    B.append(('bullet', f'**Puissance crête / panneau** : {p_crete} Wc'))
    B.append(('bullet', f'**Puissance installée totale** : {p_installee_kwc:.2f} kWc'))
    B.append(('bullet', f'**Surface PV totale** : {surf_pv_totale:.2f} m²'))
    B.append(('bullet', f'**Bifacial** : {pv_module.get("Bifaciality")} '
                        f'(facteur {pv_module.get("Bifaciality_factor")})'))

    B.append(('h3', "Zone d'intérêt (sol / culture)"))
    B.append(('bullet', f'**Emprise X** : {loc.get("Xmin_InterestZone")} → '
                        f'{loc.get("Xmax_InterestZone")} m (pas {loc.get("dX_InterestZone")} m)'))
    B.append(('bullet', f'**Emprise Y** : {loc.get("Ymin_InterestZone")} → '
                        f'{loc.get("Ymax_InterestZone")} m (pas {loc.get("dY_InterestZone")} m)'))
    B.append(('bullet', f'**Grille** : {nx} × {ny} = **{n_points_zone} points**'))
    B.append(('bullet', f'**Orientation** : {loc.get("InterestZoneOrientationMode")} '
                        f'(angle custom {loc.get("InterestZoneCustomAngle")}°)'))

    B.append(('h3', 'Modèles utilisés'))
    B.append(('bullet', f'**Modèle de culture** : {crop_config.get("CropModel")}'))
    B.append(('bullet', f'**Discrétisation ciel** : {loc.get("SkyDiscretizationScheme")} '
                        f'(MF={loc.get("MF")})'))
    B.append(('bullet', f'**Ciel diffus** : {loc.get("DiffuseSkyType")}'))
    B.append(('bullet', f'**Précision position solaire** : '
                        f'{niveaux_soleil.get(loc.get("PrecisionLevelOnSunPosition"), loc.get("PrecisionLevelOnSunPosition"))}'))

    B.append(('h3', 'Politiques de pilotage comparées'))
    for i, s in enumerate(strategies_infos, 1):
        B.append(('bullet', f'**{i}. {s["name"]}** — '
                            f'{s["description"] or "(pas de description)"}'))
        B.append(('bullet2', f'Mode par défaut : {s["default_mode"]}'))
        if s['rules']:
            B.append(('bullet2', 'Règles (la première qui matche gagne) :'))
            for r in s['rules']:
                B.append(('bullet2', f'  • {_fmt_regle(r)}'))
        else:
            B.append(('bullet2', "Aucune règle (mode par défaut appliqué toute l'année)"))

    B.append(('sep',))
    B.append(('h2', '2. Détail complet des inputs'))
    B.append(('text', '(Toutes les valeurs brutes, pour vérification ultérieure.)'))
    B.append(('dict', 'SCENARIO / Localisation', loc))
    B.append(('dict', 'PARC PV / AV_CENTRAL', av))
    B.append(('dict', 'MODULE PV', pv_module))
    B.append(('dict', 'MODELE DE CULTURE (crop config)', crop_config))

    B.append(('h3', 'Fichiers YAML de stratégie de pilotage (contenu brut)'))
    for s in strategies_infos:
        B.append(('code', f'{s["name"]} — {s["fichier"]}', s['yaml_brut'].rstrip()))

    return B


def ecrire_description_inputs(chemin_md, loc, av, pv_module, crop_config,
                             strategies_infos, simu_nom):
    """Écrit le document descriptif des inputs en Markdown (.md)."""
    blocs = _blocs_description(loc, av, pv_module, crop_config,
                              strategies_infos, simu_nom)
    L = []
    for b in blocs:
        kind = b[0]
        if kind == 'h1':
            L += [f'# {b[1]}', '']
        elif kind == 'subtitle':
            L += [f'**{b[1]}**', '']
        elif kind == 'h2':
            L += [f'## {b[1]}', '']
        elif kind == 'h3':
            L += ['', f'### {b[1]}', '']
        elif kind == 'bullet':
            L.append(f'- {b[1]}')
        elif kind == 'bullet2':
            L.append(f'    - {b[1]}')
        elif kind == 'text':
            L += [f'*{b[1]}*', '']
        elif kind == 'sep':
            L += ['', '---', '']
        elif kind == 'dict':
            L += [f'### {b[1]}', '', '| Paramètre | Valeur |', '|---|---|']
            for k in b[2]:
                L.append(f'| {k} | {b[2][k]} |')
            L.append('')
        elif kind == 'code':
            L += [f'#### {b[1]}', '', '```yaml', b[2], '```', '']

    with open(chemin_md, 'w') as f:
        f.write('\n'.join(L))
    print(f'[simulation_report] Fiche inputs (md)  -> {chemin_md}')
    return chemin_md


def ecrire_description_pdf(chemin_pdf, loc, av, pv_module, crop_config,
                          strategies_infos, simu_nom):
    """Écrit le MEME contenu que la fiche .md sous forme de PDF lisible.

    Rendu via matplotlib (PdfPages) -> aucune dépendance supplémentaire à
    installer. Pagination automatique au format A4 portrait.
    """
    import textwrap
    import matplotlib
    matplotlib.use('Agg', force=True)
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    blocs = _blocs_description(loc, av, pv_module, crop_config,
                              strategies_infos, simu_nom)

    # Geometrie de page (pouces, A4 portrait) et marges en coordonnees figure
    PAGE_W, PAGE_H = 8.27, 11.69
    X_MARGIN, X_INDENT, X_INDENT2 = 0.06, 0.10, 0.14
    Y_TOP, Y_BOTTOM = 0.95, 0.06
    LINE = 0.0175          # hauteur d'une ligne (fraction de page)

    def strip_md(s):
        return s.replace('**', '').replace('`', '')

    pdf = PdfPages(chemin_pdf)
    state = {'fig': None, 'y': 0.0}

    def nouvelle_page():
        if state['fig'] is not None:
            pdf.savefig(state['fig'])
            plt.close(state['fig'])
        fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        state['fig'] = fig
        state['y'] = Y_TOP

    def place(texte, x, dy_before, dy_after, size, weight='normal',
              color='black', family='sans-serif', wrap=None):
        """Ecrit 'texte' (possiblement multi-lignes apres wrap) et avance y."""
        state['y'] -= dy_before
        lignes = [texte]
        if wrap:
            lignes = textwrap.wrap(texte, wrap) or ['']
            # indentation suspendue pour les lignes suivantes d'une puce
        for j, ligne in enumerate(lignes):
            if state['y'] < Y_BOTTOM:
                nouvelle_page()
            xx = x if j == 0 else x + 0.012
            state['fig'].text(xx, state['y'], ligne, fontsize=size,
                              fontweight=weight, color=color, family=family,
                              ha='left', va='top')
            state['y'] -= LINE
        state['y'] -= dy_after

    def trait():
        if state['y'] < Y_BOTTOM + 0.02:
            nouvelle_page()
        state['y'] -= 0.008
        state['fig'].add_artist(plt.Line2D(
            [X_MARGIN, 1 - X_MARGIN], [state['y'], state['y']],
            color='#bbbbbb', linewidth=0.8, transform=state['fig'].transFigure))
        state['y'] -= 0.012

    nouvelle_page()
    for b in blocs:
        kind = b[0]
        if state['y'] < Y_BOTTOM + 0.03:
            nouvelle_page()
        if kind == 'h1':
            place(strip_md(b[1]), X_MARGIN, 0.0, 0.004, 17, 'bold', wrap=42)
        elif kind == 'subtitle':
            place(strip_md(b[1]), X_MARGIN, 0.0, 0.008, 10.5, 'bold',
                  color='#444444', wrap=80)
        elif kind == 'h2':
            place(strip_md(b[1]), X_MARGIN, 0.018, 0.006, 13, 'bold',
                  color='#1a3e6e', wrap=80)
        elif kind == 'h3':
            place(strip_md(b[1]), X_MARGIN, 0.012, 0.004, 11, 'bold',
                  color='#2a5d3a', wrap=85)
        elif kind == 'bullet':
            place('• ' + strip_md(b[1]), X_INDENT, 0.0, 0.0, 9, wrap=95)
        elif kind == 'bullet2':
            place('– ' + strip_md(b[1]), X_INDENT2, 0.0, 0.0, 9, wrap=92)
        elif kind == 'text':
            place(strip_md(b[1]), X_MARGIN, 0.0, 0.004, 8.5, 'normal',
                  color='#555555', wrap=100)
        elif kind == 'sep':
            trait()
        elif kind == 'dict':
            place(b[1], X_MARGIN, 0.010, 0.004, 11, 'bold', color='#2a5d3a')
            largeur_cle = max((len(str(k)) for k in b[2]), default=10)
            for k in b[2]:
                ligne = f'{str(k):<{largeur_cle}} : {b[2][k]}'
                place(ligne, X_INDENT, 0.0, 0.0, 7.5, family='monospace', wrap=105)
        elif kind == 'code':
            place(b[1], X_MARGIN, 0.010, 0.004, 9, 'bold', color='#2a5d3a')
            for ligne_code in b[2].splitlines():
                place(ligne_code if ligne_code else ' ', X_INDENT, 0.0, 0.0,
                      7, family='monospace', wrap=110)

    pdf.savefig(state['fig'])
    plt.close(state['fig'])
    pdf.close()
    print(f'[simulation_report] Fiche inputs (pdf) -> {chemin_pdf}')
    return chemin_pdf


# --------------------------------------------------------------------------- #
#  Fichier d'avis à remplir
# --------------------------------------------------------------------------- #
def ecrire_template_avis(chemin_txt, simu_nom, strategies_infos, resultats=None):
    """Écrit un fichier texte d'avis à remplir par l'utilisateur.

    resultats : dict optionnel {nom_pilotage: {'energie_MWh': ..., 'biomasse_fin': ...}}
                pour pré-remplir un petit tableau de résultats.
    """
    L = []
    L.append('=' * 70)
    L.append(f'AVIS SUR LA SIMULATION : {simu_nom}')
    L.append('=' * 70)
    L.append('')
    L.append(f'Date de la simulation : {datetime.datetime.now():%Y-%m-%d %H:%M}')
    L.append('')
    L.append('Politiques de pilotage comparées :')
    for i, s in enumerate(strategies_infos, 1):
        L.append(f'  {i}. {s["name"]} — {s["description"] or ""}')
    L.append('')

    if resultats:
        L.append('-' * 70)
        L.append('RESULTATS (pre-remplis automatiquement)')
        L.append('-' * 70)
        L.append(f'{"Pilotage":<35}{"Energie [MWh]":>16}{"Biomasse fin":>16}')
        for nom, r in resultats.items():
            e = r.get('energie_MWh')
            b = r.get('biomasse_fin')
            e_s = f'{e:.2f}' if e is not None else '-'
            b_s = f'{b:.1f}' if b is not None else '-'
            L.append(f'{nom:<35}{e_s:>16}{b_s:>16}')
        L.append('')

    L.append('-' * 70)
    L.append('MON AVIS (a remplir)')
    L.append('-' * 70)
    L.append('')
    L.append('# Objectif de cette simulation :')
    L.append('   ...')
    L.append('')
    L.append('# Observations sur les resultats :')
    L.append('   - Energie : ...')
    L.append('   - Agricole (biomasse/rendement) : ...')
    L.append('   - Compromis energie/agricole : ...')
    L.append('')
    L.append('# La politique de pilotage la plus interessante ici, et pourquoi :')
    L.append('   ...')
    L.append('')
    L.append('# Problemes / doutes sur la config (parc, zone, meteo...) :')
    L.append('   ...')
    L.append('')
    L.append('# Prochaine etape / a tester ensuite :')
    L.append('   ...')
    L.append('')

    with open(chemin_txt, 'w') as f:
        f.write('\n'.join(L))
    print(f'[simulation_report] Template avis -> {chemin_txt}')
    return chemin_txt


# --------------------------------------------------------------------------- #
#  Fichier de performance (documentation des temps de calcul)
# --------------------------------------------------------------------------- #
def ecrire_performance(chemin_txt, simu_nom, infos):
    """Écrit un fichier documentant les performances de la simulation.

    But : garder une trace des durées et de la stratégie d'exécution
    (séquentielle / multiprocessing) pour suivre l'effet des optimisations au fil
    des simulations et diagnostiquer d'éventuels problèmes.

    Parameters
    ----------
    infos : dict, avec (toutes optionnelles) :
        'execution'        : str  ('SEQUENTIELLE' / 'MULTIPROCESSING')
        'n_workers'        : int
        'n_positions_soleil': int
        'n_points_zone'    : int
        'precision_soleil' : int
        'strategies'       : list[str]
        'duree_preproc'    : float (s)
        'durees_par_strategie' : dict {nom: secondes}
        'duree_graphes'    : float (s)
        'duree_totale'     : float (s)
        'notes'            : str
    """
    def fmt(s):
        if s is None:
            return '-'
        return f'{s:6.1f} s' if s < 90 else f'{s:6.1f} s ({s/60:.1f} min)'

    L = []
    L.append('=' * 70)
    L.append(f'PERFORMANCE — {simu_nom}')
    L.append('=' * 70)
    L.append('')
    L.append(f'Date            : {datetime.datetime.now():%Y-%m-%d %H:%M}')
    L.append(f'Machine         : {platform.system()} {platform.machine()} — '
             f'{os.cpu_count()} CPU logiques')
    L.append(f'Python          : {platform.python_version()}')
    L.append(f'Exécution       : {infos.get("execution", "SEQUENTIELLE")} '
             f'({infos.get("n_workers", 1)} worker(s))')
    L.append('')
    L.append('-' * 70)
    L.append('Paramètres influant sur le temps de calcul')
    L.append('-' * 70)
    L.append(f'PrecisionLevelOnSunPosition : {infos.get("precision_soleil", "-")} '
             f'-> {infos.get("n_positions_soleil", "-")} positions solaires (ray casting)')
    L.append(f"Points d'intérêt (zone)     : {infos.get('n_points_zone', '-')}")
    L.append(f'Nombre de stratégies        : {len(infos.get("strategies", []))}')
    L.append('')
    L.append('-' * 70)
    L.append('Durées')
    L.append('-' * 70)
    L.append(f'Pré-processing partagé : {fmt(infos.get("duree_preproc"))}')
    durees = infos.get('durees_par_strategie', {})
    if durees:
        L.append('Par stratégie (géométrie + ray casting + production + culture) :')
        larg = max((len(n) for n in durees), default=10)
        for nom, d in durees.items():
            L.append(f'    {nom:<{larg}} : {fmt(d)}')
    L.append(f'Graphes + images + docs : {fmt(infos.get("duree_graphes"))}')
    L.append('-' * 40)
    L.append(f'TOTAL : {fmt(infos.get("duree_totale"))}')
    L.append('')
    L.append('-' * 70)
    L.append('Notes (optimisations testées, changements de perf, problèmes...)')
    L.append('-' * 70)
    L.append(infos.get('notes', '') or '   ...')
    L.append('')

    with open(chemin_txt, 'w') as f:
        f.write('\n'.join(L))
    print(f'[simulation_report] Performance -> {chemin_txt}')
    return chemin_txt

# ============== [HUGO - PILOTAGE] FIN AJOUT ==============
