#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Authors : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import pyvista as pyV
import numpy as np


def compute_ground_extent(scene, margin: float = 10.0):
    """
    Compute a visually sensible ground extent from the scene geometry bounds.

    Parameters
    ----------
    scene : pyvista.PolyData or pyvista.MultiBlock
        Scene geometry (PV panels, structures, …).
    margin : float
        Extra padding around the bounding box, in meters. Default: 10.0.

    Returns
    -------
    x_min, x_max, y_min, y_max : float
        Ground rectangle corners.
    """
    xmin, xmax, ymin, ymax, _, _ = scene.bounds
    return xmin - margin, xmax + margin, ymin - margin, ymax + margin


def open_pyvista_3D_visualization(interest_points, spatialized_variable, scene, lgd_title, extra_mesh=None):
    """
    
    Function to open a 3D visualization window of the scene with a specific spatialized variable plotted.

    Parameters
    ----------
    interest_points : Array of float (n, 3) with n the number of interest points
        The (n, 3) array listing the coordinates of the interest points where results of spatialized models are calculted.
    spatialized_variable : Array of float (n,) with n the number of interest points
        The (n,) array listing the spatialized results at each interest point.
    scene : pyvista.core.pointset.PolyData (or pyvista MultiBlock)
        A PolyData (or list of PolyData object) containing geometrical information about the 3D objects of the scene.
    lgd_title : string
        Legend title describing the spatialized variable visualized

    Returns
    -------
    None, just open a pyvista visualization window. You have to close the window to keep the code running.

    """
    
    labels = dict(zlabel='Z (ZENITH)', xlabel='X (EAST)', ylabel='Y (NORTH)')
    
    plotter = pyV.Plotter()

    try:
        geom_panels = scene.polydata_by_property({'Type': ['PV']},
                                                extract_surface=True)
        geom_struct = scene.polydata_by_property({'Type': ['Structure block']},
                                                extract_surface=True)
        plotter.add_mesh(geom_panels, color='black')

        if geom_struct.user_dict['Material'].lower() == 'metal':
            struct_color = 'grey'
        elif geom_struct.user_dict['Material'].lower() == 'wood':
            struct_color = 'brown'
        plotter.add_mesh(geom_struct, color=struct_color)
    except Exception as _e:
        print(f'No structure found: {_e}')
        plotter.add_mesh(scene, color='black')


    x_min, x_max, y_min, y_max = compute_ground_extent(scene)
    ground = np.array([[x_min, y_max, 0],
                       [x_max, y_max, 0],
                       [x_min, y_min, 0],
                       [x_max, y_min, 0]])

    ground_m = np.hstack([[3, 0, 1, 2],    
                          [3, 1, 2, 3],])

    grnd = pyV.PolyData(ground, ground_m)
    
    plotter.add_mesh(grnd, color='green')
    
    plotter.add_axes(**labels)
    
    plotter.set_background('white')

    if extra_mesh is not None:
         plotter.add_mesh(extra_mesh, color='black')

    plotter.add_mesh(interest_points,
                     scalars=spatialized_variable,
                     point_size=10,
                     lighting=False,
                     show_edges=False,
                     scalar_bar_args={"title": lgd_title},
                     clim=[spatialized_variable.min(), 
                           spatialized_variable.max()])
    
    plotter.show()