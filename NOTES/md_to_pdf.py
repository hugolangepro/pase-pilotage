#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convertit un fichier Markdown en PDF lisible, sans dependance supplementaire.

Rendu via matplotlib (PdfPages), meme approche que
pase/DATA_MANAGEMENT/simulation_report.py : aucun pandoc / LaTeX / navigateur
a installer. Format A4 portrait, pagination automatique.

Gere : titres (#, ##, ###), paragraphes, listes a puces et numerotees, tableaux,
blocs de code, citations (>), traits horizontaux, et le gras/code inline.

Usage :
    python NOTES/md_to_pdf.py GUIDE_UTILISATION.md
    python NOTES/md_to_pdf.py entree.md sortie.pdf
"""
import os
import re
import sys
import textwrap

import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# --- Geometrie de page (pouces, A4 portrait) et marges en coordonnees figure --
PAGE_W, PAGE_H = 8.27, 11.69
X_MARGIN = 0.07
Y_TOP, Y_BOTTOM = 0.94, 0.07
LINE = 0.0165                  # hauteur d'une ligne, en fraction de page

COL_TITRE = '#1a3a5c'
COL_GRIS = '#555555'
COL_TRAIT = '#bbbbbb'
COL_CODE_BG = '#f2f2f2'
COL_QUOTE = '#2a6099'


# --------------------------------------------------------------------------- #
#  Nettoyage du balisage inline
# --------------------------------------------------------------------------- #
def inline(s):
    """Retire le balisage Markdown inline qu'on ne sait pas rendre."""
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)   # [texte](lien) -> texte
    s = re.sub(r'<sup>(.*?)</sup>', r'\1', s)        # exposants HTML
    s = re.sub(r'<[^>]+>', '', s)                    # tout autre tag HTML
    s = s.replace('**', '').replace('`', '')
    s = re.sub(r'(?<!\w)\*(\S(?:.*?\S)?)\*(?!\w)', r'\1', s)   # *italique* -> italique
    s = s.replace('&nbsp;', ' ').replace('&gt;', '>').replace('&lt;', '<')
    return s.strip()


# --------------------------------------------------------------------------- #
#  Parsing : Markdown -> liste de blocs (type, contenu)
# --------------------------------------------------------------------------- #
def parse(md):
    blocs = []
    lignes = md.splitlines()
    i = 0
    para = []

    def vider_para():
        if para:
            blocs.append(('p', ' '.join(para)))
            para.clear()

    while i < len(lignes):
        ligne = lignes[i]
        nu = ligne.strip()

        # --- bloc de code delimite par ``` ---
        if nu.startswith('```'):
            vider_para()
            i += 1
            code = []
            while i < len(lignes) and not lignes[i].strip().startswith('```'):
                code.append(lignes[i])
                i += 1
            blocs.append(('code', code))
            i += 1
            continue

        # --- tableau : au moins 2 lignes commencant par | ---
        if nu.startswith('|') and i + 1 < len(lignes) \
                and re.match(r'^\|[\s:|-]+\|$', lignes[i + 1].strip()):
            vider_para()
            entete = [c.strip() for c in nu.strip('|').split('|')]
            i += 2
            corps = []
            while i < len(lignes) and lignes[i].strip().startswith('|'):
                corps.append([c.strip() for c in lignes[i].strip().strip('|').split('|')])
                i += 1
            blocs.append(('table', (entete, corps)))
            continue

        # --- titres ---
        if nu.startswith('### '):
            vider_para(); blocs.append(('h3', nu[4:])); i += 1; continue
        if nu.startswith('## '):
            vider_para(); blocs.append(('h2', nu[3:])); i += 1; continue
        if nu.startswith('# '):
            vider_para(); blocs.append(('h1', nu[2:])); i += 1; continue

        # --- trait horizontal ---
        if nu in ('---', '***', '___'):
            vider_para(); blocs.append(('hr', None)); i += 1; continue

        # --- citation ---
        if nu.startswith('>'):
            vider_para()
            quote = []
            while i < len(lignes) and lignes[i].strip().startswith('>'):
                quote.append(lignes[i].strip().lstrip('>').strip())
                i += 1
            blocs.append(('quote', ' '.join(q for q in quote if q)))
            continue

        # --- listes ---
        m_puce = re.match(r'^[-*]\s+(.*)$', nu)
        m_num = re.match(r'^(\d+)\.\s+(.*)$', nu)
        if m_puce:
            vider_para(); blocs.append(('li', ['•', m_puce.group(1)])); i += 1; continue
        if m_num:
            vider_para(); blocs.append(('li', [m_num.group(1) + '.', m_num.group(2)]))
            i += 1; continue

        # --- ligne vide -> fin de paragraphe ---
        if not nu:
            vider_para(); i += 1; continue

        # --- suite indentee d'une puce : rattachee a l'item courant ---
        # (sinon la 2e ligne d'une puce repartirait a la marge, comme un paragraphe)
        if (ligne[:1].isspace() and not para and blocs and blocs[-1][0] == 'li'):
            blocs[-1][1][1] += ' ' + nu
            i += 1
            continue

        para.append(nu)
        i += 1

    vider_para()
    return blocs


# --------------------------------------------------------------------------- #
#  Rendu
# --------------------------------------------------------------------------- #
class Rendu:
    def __init__(self, chemin_pdf):
        self.pdf = PdfPages(chemin_pdf)
        self.fig = None
        self.y = 0.0
        self.nouvelle_page()

    def nouvelle_page(self):
        if self.fig is not None:
            self.pdf.savefig(self.fig)
            plt.close(self.fig)
        self.fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.y = Y_TOP

    def place_ligne(self, texte, x, size, weight='normal', color='black',
                    family='sans-serif', bbox=None):
        if self.y < Y_BOTTOM:
            self.nouvelle_page()
        self.fig.text(x, self.y, texte, fontsize=size, fontweight=weight,
                      color=color, family=family, ha='left', va='top', bbox=bbox)
        self.y -= LINE * (size / 9.5)

    def para(self, texte, x, size, weight='normal', color='black', wrap=95,
             family='sans-serif', hang=0.0):
        for j, l in enumerate(textwrap.wrap(texte, wrap) or ['']):
            self.place_ligne(l, x if j == 0 else x + hang, size, weight, color, family)

    def trait(self, couleur=COL_TRAIT, epaisseur=0.8):
        if self.y < Y_BOTTOM + 0.02:
            self.nouvelle_page()
        self.fig.add_artist(plt.Line2D([X_MARGIN, 1 - X_MARGIN], [self.y, self.y],
                                       color=couleur, linewidth=epaisseur,
                                       transform=self.fig.transFigure))
        self.y -= 0.012

    def table(self, entete, corps):
        """Tableau : largeurs de colonnes proportionnelles au contenu."""
        ncol = len(entete)
        # Largeur de reference par colonne. On plafonne l'influence des cellules
        # tres longues (elles seront wrappees) mais jamais en dessous du mot le
        # plus long : sinon un identifiant comme "antitrack_printemps_et_..." se
        # ferait couper en plein milieu.
        larg = []
        for c in range(ncol):
            cellules = [inline(entete[c])] + [inline(r[c]) for r in corps if c < len(r)]
            if not cellules:
                larg.append(10)
                continue
            plus_long_mot = max((len(m) for cel in cellules for m in cel.split()),
                                default=10)
            larg.append(max(plus_long_mot, min(max(len(x) for x in cellules), 40)))
        total = sum(larg) or 1
        dispo = 1 - 2 * X_MARGIN
        # chaque colonne recoit au moins 12 % de la largeur
        frac = [max(0.12, w / total) for w in larg]
        frac = [f / sum(frac) for f in frac]
        xs, acc = [], X_MARGIN
        for f in frac:
            xs.append(acc)
            acc += f * dispo
        # nb de caracteres tenant dans chaque colonne (~105 car. sur la largeur utile)
        chars = [max(8, int(f * dispo * 105)) for f in frac]

        if self.y < Y_BOTTOM + 0.06:
            self.nouvelle_page()
        self.y -= 0.006

        def rangee(cells, weight, color='black', size=8.2):
            lignes_wrap = [textwrap.wrap(inline(c), chars[k]) or ['']
                           for k, c in enumerate(cells[:ncol])]
            hauteur = max(len(w) for w in lignes_wrap)
            if self.y - hauteur * LINE * 0.92 < Y_BOTTOM:
                self.nouvelle_page()
            y0 = self.y
            for k, wlines in enumerate(lignes_wrap):
                yy = y0
                for l in wlines:
                    self.fig.text(xs[k], yy, l, fontsize=size, fontweight=weight,
                                  color=color, ha='left', va='top')
                    yy -= LINE * 0.92
            self.y = y0 - hauteur * LINE * 0.92

        rangee(entete, 'bold', COL_TITRE)
        self.trait(COL_TRAIT, 0.6)
        for r in corps:
            rangee(r, 'normal')
        self.y -= 0.008

    def fermer(self):
        if self.fig is not None:
            self.pdf.savefig(self.fig)
            plt.close(self.fig)
        self.pdf.close()


def rendre(blocs, chemin_pdf):
    r = Rendu(chemin_pdf)
    for kind, contenu in blocs:
        if kind == 'h1':
            r.y -= 0.010
            r.para(inline(contenu), X_MARGIN, 17, 'bold', COL_TITRE, wrap=48)
            r.y -= 0.008
            r.trait(COL_TITRE, 1.2)
        elif kind == 'h2':
            if r.y < Y_BOTTOM + 0.10:
                r.nouvelle_page()
            r.y -= 0.016
            r.para(inline(contenu), X_MARGIN, 13, 'bold', COL_TITRE, wrap=62)
            r.y -= 0.006
        elif kind == 'h3':
            r.y -= 0.012
            r.para(inline(contenu), X_MARGIN, 10.5, 'bold', color='#333333', wrap=78)
            r.y -= 0.004
        elif kind == 'p':
            r.para(inline(contenu), X_MARGIN, 9.5, wrap=98)
            r.y -= 0.007
        elif kind == 'li':
            marque, texte = contenu
            r.para(f'{marque} {inline(texte)}', X_MARGIN + 0.015, 9.5,
                   wrap=94, hang=0.012)
            r.y -= 0.003
        elif kind == 'quote':
            r.y -= 0.004
            r.para(inline(contenu), X_MARGIN + 0.02, 9, color=COL_QUOTE, wrap=92)
            r.y -= 0.007
        elif kind == 'code':
            r.y -= 0.005
            for l in contenu:
                r.place_ligne('  ' + l.rstrip(), X_MARGIN + 0.01, 8.5,
                              family='monospace', color='#222222',
                              bbox=dict(facecolor=COL_CODE_BG, edgecolor='none',
                                        pad=1.6))
            r.y -= 0.009
        elif kind == 'table':
            r.table(*contenu)
        elif kind == 'hr':
            r.y -= 0.004
            r.trait()
    r.fermer()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.pdf'
    with open(src, encoding='utf-8') as f:
        blocs = parse(f.read())
    rendre(blocs, dst)
    print(f'PDF ecrit : {dst} ({os.path.getsize(dst) // 1024} Ko)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
