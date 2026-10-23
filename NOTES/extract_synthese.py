"""Extrait une table de synthese de tous les runs SIMU_* avant nettoyage.

Lit INFOS_SIMULATION.md / AVIS_SIMULATION.txt / PERFORMANCE.txt de chaque run
et produit NOTES/SYNTHESE_RESULTATS.md (quelques Ko) qui condense la valeur
scientifique des ~1,1 Go de resultats.
"""
import os
import re

BASE = '/Users/hugolange/Desktop/pase_pilotage'
RUNS_DIR = os.path.join(BASE, 'OUTPUTS', 'COMPARAISONS_PILOTAGE')
OUT = os.path.join(BASE, 'NOTES', 'SYNTHESE_RESULTATS.md')

# Runs conserves en entier apres nettoyage (les autres ne subsistent que par ce document)
CONSERVES = {2, 5, 10, 11, 14, 16}

# Runs supprimes le 2026-07-31 : donnees relevees avant suppression.
# 'res' vide = table chiffree non recuperee (seule l'amplitude est connue).
ARCHIVE = [
    dict(n=1, date='2026-07-20 11:25', lieu='Gembloux', annees='2020', pan='4',
         culture='simple', pts='255', py='-', ampl='-73 % / +3 %',
         note='Premier run, 3 pilotages seulement (pas de strategie mixte).',
         res=[('tracking_pur', '2.25', '1574.0'), ('antitrack_pur', '0.60', '1624.6'),
              ('antitrack_printemps', '1.89', '1577.7')]),
    dict(n=3, date='2026-07-20 16:31', lieu='Gembloux', annees='2020', pan='4',
         culture='simple', pts='81', py='3.10.20', ampl='-73 % / +10 %',
         note='Zone d\'interet reduite a 81 points (test de sensibilite).',
         res=[('tracking_pur', '2.25', '1452.6'), ('antitrack_pur', '0.60', '1611.1'),
              ('antitrack_printemps', '1.89', '1464.1'),
              ('antitrack_printemps_et_track_midi_ete', '1.51', '1541.5')]),
    dict(n=4, date='2026-07-20 23:55', lieu='Gembloux', annees='2020', pan='4',
         culture='simple', pts='81', py='3.10.20', ampl='-73 % / +10 %',
         note='Test du multiprocessing — resultats identiques a SIMU_3.', res=[]),
    dict(n=6, date='2026-07-21 00:29', lieu='Gembloux', annees='2020', pan='12',
         culture='simple', pts='81', py='3.10.20', ampl='-73 % / +18 %',
         note='Resultats identiques a SIMU_5 (conserve).', res=[]),
    dict(n=7, date='2026-07-21 10:06', lieu='Chanco', annees='2021', pan='12',
         culture='simple', pts='289', py='3.10.20', ampl='-76 % / +26 %',
         note='**Seule perte reelle** : configuration unique (Chanco 2021), '
              'table chiffree non recuperee avant suppression.', res=[]),
    dict(n=8, date='2026-07-21 11:33', lieu='Chamonix_Mont_Blanc', annees='2020', pan='12',
         culture='simple', pts='1701', py='3.10.20', ampl='-70 % / +4 %',
         note='Climat montagnard : le gain de biomasse de l\'anti-tracking s\'effondre (+4 %).',
         res=[('tracking_pur', '6.69', '774.7'), ('antitrack_pur', '2.00', '802.3'),
              ('antitrack_printemps', '5.84', '771.5'),
              ('antitrack_printemps_et_track_midi_ete', '4.85', '785.0')]),
    dict(n=9, date='2026-07-21 16:02', lieu='Lampernisse', annees='2020', pan='12',
         culture='simple', pts='1701', py='3.10.20', ampl='-74 % / +5 %',
         note='Resultats identiques a SIMU_10 (conserve).', res=[]),
    dict(n=12, date='2026-07-27 11:59', lieu='Gembloux', annees='2020', pan='4',
         culture='simple', pts='42', py='3.10.20', ampl='-73 % / +24 %',
         note='Meme config que SIMU_11 mais relance en python 3.10 (ancienne pile).', res=[]),
    dict(n=13, date='2026-07-27 15:00', lieu='Werbomont', annees='2005 a 2006', pan='4',
         culture='pystics', pts='6', py='3.12.13', ampl='-',
         note='Table de resultats deja illisible avant suppression. '
              'Meme config que SIMU_14 (conserve), lance 35 min plus tot.', res=[]),
    dict(n=15, date='2026-07-31 09:48', lieu='Werbomont', annees='2005 a 2006', pan='4',
         culture='pystics', pts='-', py='-', ampl='-',
         note='Run avorte (dossier vide, 0 octet).', res=[]),
]


def champ(texte, motif, defaut='?'):
    m = re.search(motif, texte, re.M)
    return m.group(1).strip() if m else defaut


def lire(chemin):
    if not os.path.isfile(chemin):
        return ''
    with open(chemin, encoding='utf-8') as f:
        return f.read()


def parse_infos(txt):
    """Configuration du run depuis INFOS_SIMULATION.md."""
    grille = champ(txt, r'\*\*Grille\*\*\s*:\s*(.+?)\s*$', '?')
    pts = champ(grille, r'=\s*\*\*(\d+)\s*points\*\*', '?') if grille != '?' else '?'
    return {
        'lieu': champ(txt, r'\*\*Lieu\*\*\s*:\s*(.+?)\s*\('),
        'coord': champ(txt, r'\*\*Lieu\*\*\s*:\s*.+?\((.+?)\)'),
        'annees': champ(txt, r'\*\*Années simulées\*\*\s*:\s*(.+?)\s*$'),
        'panneaux': champ(txt, r'\*\*Nombre total de panneaux\*\*\s*:\s*(\d+)'),
        'puissance': champ(txt, r'\*\*Puissance installée totale\*\*\s*:\s*(.+?)\s*$'),
        'azimut': champ(txt, r'\*\*Azimut de la centrale\*\*\s*:\s*(\d+)'),
        'gcr': champ(txt, r'\*\*GCR \(X\)\*\*\s*:\s*([\d.]+)'),
        'maxtilt': champ(txt, r'MaxTiltAngle\)\*\*\s*:\s*(\d+)'),
        'culture': champ(txt, r'\*\*Modèle de culture\*\*\s*:\s*(.+?)\s*$'),
        'points': pts,
        'precision': champ(txt, r'\*\*Précision position solaire\*\*\s*:\s*(\d+)'),
    }


def parse_resultats(txt):
    """Table [(strategie, energie_MWh, biomasse)] depuis AVIS_SIMULATION.txt."""
    bloc = re.search(r'RESULTATS.*?-{10,}\n(.*?)\n\s*-{10,}', txt, re.S)
    if not bloc:
        return []
    res = []
    for ligne in bloc.group(1).splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith('Pilotage'):
            continue
        m = re.match(r'^(.+?)\s+([\d.]+)\s+([\d.]+)$', ligne)
        if m:
            res.append((m.group(1).strip(), m.group(2), m.group(3)))
    return res


def parse_avis(txt):
    """Texte libre reellement redige (hors gabarit)."""
    bloc = re.search(r'MON AVIS \(a remplir\)\s*\n-{10,}\n(.*)$', txt, re.S)
    if not bloc:
        return []
    garde = []
    for ligne in bloc.group(1).splitlines():
        s = ligne.strip()
        if not s or s.startswith('#') or s == '...':
            continue
        # Lignes de gabarit du type "- Energie : ..." ou "Objectif : ..."
        if re.match(r'^-?\s*[^:]{0,60}:\s*\.\.\.\s*$', s):
            continue
        garde.append(s.lstrip('- ').strip())
    return garde


def parse_perf(txt):
    return {
        'python': champ(txt, r'^Python\s*:\s*(.+?)\s*$'),
        'exec': champ(txt, r'^Exécution\s*:\s*(.+?)\s*$'),
        'total': champ(txt, r'^TOTAL\s*:\s*(.+?)\s*$'),
        'date': champ(txt, r'^Date\s*:\s*(.+?)\s*$'),
    }


def numero(nom):
    m = re.match(r'SIMU_(\d+)_', nom)
    return int(m.group(1)) if m else 0


def main():
    runs = sorted(
        (d for d in os.listdir(RUNS_DIR) if d.startswith('SIMU_')), key=numero
    )
    lignes = []
    A = lignes.append

    A('# Synthese des resultats de comparaison de pilotage')
    A('')
    A("*Synthese des 16 runs de comparaison de pilotage menes en juillet 2026. "
      "La section 2 est extraite automatiquement des runs encore presents dans "
      "`OUTPUTS/COMPARAISONS_PILOTAGE/` ; la section 3 archive les chiffres des runs "
      "supprimes le 2026-07-31 lors du nettoyage du disque (~816 Mo liberes). "
      "Ce document condense a lui seul la valeur scientifique de l'ensemble.*")
    A('')
    A('*Regenerable avec `python NOTES/extract_synthese.py`.*')
    A('')
    A('> **Attention environnement** : tous les runs n\'ont pas tourne sur la meme pile '
      'logicielle. Python **3.12** = env `pase20` (PASE 2.0, resultats de reference) ; '
      'Python **3.10** = ancien env `pase3`. D\'apres `NOTES/MIGRATION_PASE_2.0.md`, la 2.0 '
      'corrige plusieurs bugs d\'irradiance : **les biomasses ne sont pas comparables entre '
      'les deux piles** (l\'energie PV, elle, est identique).')
    A('')

    # ------------------------------------------------------------------ #
    A('## 1. Vue d\'ensemble')
    A('')
    A('| # | Date | Lieu | Annees | Pan. | Culture | Pts zone | Python | Conserve |')
    A('|---|---|---|---|---|---|---|---|---|')
    detail = []
    for run in runs:
        n = numero(run)
        infos = parse_infos(lire(os.path.join(RUNS_DIR, run, 'INFOS_SIMULATION.md')))
        perf = parse_perf(lire(os.path.join(RUNS_DIR, run, 'PERFORMANCE.txt')))
        avis_txt = lire(os.path.join(RUNS_DIR, run, 'AVIS_SIMULATION.txt'))
        res = parse_resultats(avis_txt)
        notes = parse_avis(avis_txt)
        py = perf['python'] if perf['python'] != '?' else '-'
        marque = '**oui**' if n in CONSERVES else 'non'
        if not res and not infos['lieu'].strip('?'):
            A(f'| {n} | - | *(run avorte, dossier vide)* | | | | | | non |')
            continue
        A(f"| {n} | {perf['date']} | {infos['lieu']} | {infos['annees']} | "
          f"{infos['panneaux']} | {infos['culture']} | {infos['points']} | {py} | {marque} |")
        detail.append((n, run, infos, perf, res, notes))

    # ------------------------------------------------------------------ #
    A('')
    A('## 2. Resultats par run')
    A('')
    for n, run, infos, perf, res, notes in detail:
        A(f'### SIMU_{n} — {infos["lieu"]} {infos["annees"]}, '
          f'{infos["panneaux"]} panneaux, culture `{infos["culture"]}`')
        A('')
        A(f'`{run}`')
        A('')
        A(f"- Config : azimut {infos['azimut']}°, GCR(X) {infos['gcr']}, "
          f"MaxTiltAngle {infos['maxtilt']}°, puissance {infos['puissance']}")
        A(f"- Zone : {infos['points']} points — precision position solaire : {infos['precision']}")
        A(f"- Execution : {perf['exec']}, python {perf['python']}, total {perf['total']}")
        A('')
        if res:
            A('| Pilotage | Energie [MWh] | Biomasse fin |')
            A('|---|---|---|')
            for nom, e, b in res:
                A(f'| {nom} | {e} | {b} |')
            # Arbitrage : ecart relatif du meilleur/pire
            try:
                energies = [float(e) for _, e, _ in res]
                biomasses = [float(b) for _, _, b in res]
                de = (max(energies) - min(energies)) / max(energies) * 100
                db = (max(biomasses) - min(biomasses)) / max(biomasses) * 100
                A('')
                A(f'*Amplitude entre pilotages : energie **-{de:.0f} %** au pire, '
                  f'biomasse **+{db:.0f} %** au mieux.*')
            except (ValueError, ZeroDivisionError):
                pass
        else:
            A('*(pas de resultats exploitables)*')
        if notes:
            A('')
            A('**Avis redige :**')
            for ligne in notes:
                A(f'> {ligne}')
        A('')

    # ------------------------------------------------------------------ #
    A('## 3. Runs supprimes (archive)')
    A('')
    A('*Ces 10 runs ont ete supprimes du disque le 2026-07-31 pour liberer ~816 Mo. '
      'Les chiffres ci-dessous sont tout ce qui en subsiste. La plupart sont des '
      'doublons de runs conserves ; les configurations reellement uniques sont '
      'signalees.*')
    A('')
    A('| # | Date | Lieu | Annees | Pan. | Culture | Pts | Python | Energie / Biomasse |')
    A('|---|---|---|---|---|---|---|---|---|')
    for r in ARCHIVE:
        A(f"| {r['n']} | {r['date']} | {r['lieu']} | {r['annees']} | {r['pan']} | "
          f"{r['culture']} | {r['pts']} | {r['py']} | {r['ampl']} |")
    A('')
    for r in ARCHIVE:
        A(f"**SIMU_{r['n']}** — {r['note']}")
        if r['res']:
            A('')
            A('| Pilotage | Energie [MWh] | Biomasse fin |')
            A('|---|---|---|')
            for nom, e, b in r['res']:
                A(f'| {nom} | {e} | {b} |')
        A('')

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lignes) + '\n')
    print(f'Ecrit : {OUT} ({os.path.getsize(OUT)} octets, '
          f'{len(detail)} runs sur disque + {len(ARCHIVE)} archives)')


if __name__ == '__main__':
    main()
