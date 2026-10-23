# ============== [HUGO - PILOTAGE] DEBUT AJOUT (FICHIER ENTIEREMENT NOUVEAU) ==============
#
# Captures d'ecran 3D (rendu OFF-SCREEN, sans ouvrir de fenetre) pour documenter
# une simulation :
#   - save_park_structure()  : image de la structure du parc agrivoltaique
#   - save_variable_map()     : carte de repartition d'une variable au sol (ex.
#                               biomasse de fin de saison) sous les panneaux
#
# Utilise PyVista en mode off_screen -> screenshot PNG, adapte au lancement en
# batch (aucune interaction). Toute erreur de rendu est capturee et signalee sans
# interrompre la simulation.
#
# Auteur : Hugo (stage pilotage agrivoltaïque) — 2026

import os

import numpy as np
import pyvista as pv


def _representative_geometry(geometry):
    """Renvoie une PolyData representative : si `geometry` est une liste (cas
    tracking : un maillage par position solaire), on prend un element median
    (tilt "typique") ; sinon on renvoie l'objet tel quel."""
    if isinstance(geometry, list):
        if not geometry:
            return None
        return geometry[len(geometry) // 2]
    return geometry


def _add_ground(plotter, scene, margin=8.0, color='forestgreen'):
    """Ajoute un rectangle de sol vert sous la scene."""
    xmin, xmax, ymin, ymax, _, _ = scene.bounds
    xmin, xmax = xmin - margin, xmax + margin
    ymin, ymax = ymin - margin, ymax + margin
    pts = np.array([[xmin, ymax, 0], [xmax, ymax, 0],
                    [xmin, ymin, 0], [xmax, ymin, 0]])
    faces = np.hstack([[3, 0, 1, 2], [3, 1, 2, 3]])
    plotter.add_mesh(pv.PolyData(pts, faces), color=color, opacity=0.6)


# ============== [HUGO - PILOTAGE] PERF/NETTETE ==============
# Resolution et supersampling des captures 3D. Augmenter WINDOW_SIZE et/ou
# SCREENSHOT_SCALE pour des images plus nettes (fichiers plus lourds).
WINDOW_SIZE = (1920, 1280)     # resolution de rendu (px)
SCREENSHOT_SCALE = 2           # supersampling : image finale = window * scale


def _screenshot_net(pl, save_path):
    """Anti-aliasing + supersampling -> capture nette, puis fermeture du plotter."""
    try:
        pl.enable_anti_aliasing('ssaa')   # super-sampling anti-aliasing (plus net)
    except Exception:
        pass
    pl.screenshot(save_path, scale=SCREENSHOT_SCALE)
    pl.close()
# ============== [HUGO - PILOTAGE] FIN ==============


def save_park_structure(geometry, save_path, window_size=WINDOW_SIZE,
                        titre='Structure du parc agrivoltaïque'):
    """Sauvegarde une image 3D de la structure du parc PV (off-screen).

    Parameters
    ----------
    geometry : pyvista.PolyData or list of PolyData
        PV_Configuration_3D.PV_central_PD (liste si tracking).
    save_path : str
        Chemin du PNG de sortie.
    """
    try:
        scene = _representative_geometry(geometry)
        if scene is None or getattr(scene, 'n_points', 0) == 0:
            print('[scene_screenshot] Géométrie vide, image parc ignorée')
            return None
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        pl = pv.Plotter(off_screen=True, window_size=window_size)
        # show_edges + lissage -> panneaux mieux definis (image plus nette)
        pl.add_mesh(scene, color='#1b1b1b', show_edges=True, edge_color='#444444',
                    line_width=1, smooth_shading=True)
        _add_ground(pl, scene)
        pl.add_axes(zlabel='Z (ZENITH)', xlabel='X (EST)', ylabel='Y (NORD)')
        pl.set_background('white')
        pl.add_text(titre, font_size=12, color='black')
        pl.camera_position = 'iso'
        pl.camera.zoom(1.25)
        _screenshot_net(pl, save_path)
        print(f'[scene_screenshot] Structure parc -> {save_path}')
        return save_path
    except Exception as e:
        print(f'[scene_screenshot] ATTENTION : capture structure parc échouée ({type(e).__name__}: {e})')
        return None


def save_variable_map(interest_points, values, geometry, save_path, titre='',
                      window_size=WINDOW_SIZE, vue='defaut'):
    """Sauvegarde une carte 3D de repartition d'une variable au sol (off-screen).

    Parameters
    ----------
    interest_points : ndarray (n, 3)
        Coordonnees des points d'interet au sol (Mesh.sourcepoints).
    values : ndarray (n,)
        Valeur de la variable a chaque point (ex. biomasse cumulee sur l'annee).
    geometry : pyvista.PolyData or list
        Geometrie des panneaux (contexte visuel).
    save_path : str
    titre : str
        Titre / legende (ex. 'Biomasse cumulee sur l'annee [g/m²]').
    vue : 'defaut' | 'dessus' | 'iso'
        Angle de camera. 'defaut' (recommande) = cadrage AUTOMATIQUE de PyVista,
        identique a la vue proposee a l'ouverture de la fenetre interactive
        (visualize_map). 'dessus' = vue de haut. 'iso' = vue isometrique.
    """
    try:
        scene = _representative_geometry(geometry)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        values = np.asarray(values, dtype=float)
        pl = pv.Plotter(off_screen=True, window_size=window_size)
        if scene is not None and getattr(scene, 'n_points', 0) > 0:
            pl.add_mesh(scene, color='#1b1b1b', opacity=0.55)
        vmin, vmax = float(np.nanmin(values)), float(np.nanmax(values))
        if vmin == vmax:
            vmax = vmin + 1e-9
        cloud = pv.PolyData(np.asarray(interest_points, dtype=float))
        pl.add_mesh(cloud, scalars=values, point_size=14, render_points_as_spheres=True,
                    lighting=False, clim=[vmin, vmax], cmap='viridis',
                    scalar_bar_args={'title': titre or 'Variable au sol'})
        pl.add_axes(zlabel='Z (ZENITH)', xlabel='X (EST)', ylabel='Y (NORD)')
        pl.set_background('white')
        if titre:
            pl.add_text(titre, font_size=11, color='black')
        # 'defaut' : on NE touche PAS a la camera -> PyVista cadre automatiquement
        # toute la scene (meme vue qu'a l'ouverture de la fenetre interactive).
        if vue == 'dessus':
            pl.view_xy()
        elif vue == 'iso':
            pl.camera_position = 'iso'
        pl.reset_camera()   # cadrage auto sur toute la scene (pas de zoom force)
        _screenshot_net(pl, save_path)
        print(f'[scene_screenshot] Carte variable -> {save_path}')
        return save_path
    except Exception as e:
        print(f'[scene_screenshot] ATTENTION : capture carte variable échouée ({type(e).__name__}: {e})')
        return None


def derniere_date_variable(agro_results, year, variable):
    """Renvoie la derniere date disponible (str) pour `variable` de l'annee `year`
    dans agro_results, ou None. Sert a choisir la carte de FIN de saison."""
    yd = agro_results.get(str(year), agro_results.get(year, {}))
    if variable not in yd:
        return None
    dates = list(yd[variable].keys())
    if not dates:
        return None
    return sorted(dates, key=lambda d: str(d))[-1]

# ============== [HUGO - PILOTAGE] FIN AJOUT ==============
