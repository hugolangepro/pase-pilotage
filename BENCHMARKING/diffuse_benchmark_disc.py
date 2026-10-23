#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Bouvry Arnaud (abouvry@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.
""""
Benchmark the diffuse irradiance map
"""
from itertools import product
import math
import numpy as np
import pandas as pd
import pyvista as pyV

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.benchmarking import export_benchmark, sign_commit_hash
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky

PASE_Logger()

VERBOSE = True
DEBUG = False
PLOT = False
SAVE = False
EMPTY_SCENE = False

pyV.global_theme.allow_empty_mesh = True

# Configure the scene
# Placeholder
disc_height = 1
disc_center = (0, 0, disc_height)
disc_direction = (0, 0, 1)
disc_radius = np.sqrt(1/np.pi)
disc_thickness = 0.001
if EMPTY_SCENE:
    disc = pyV.PolyData()
    analytical_f = 1
else:
    disc = pyV.Cylinder(center=disc_center, radius=disc_radius,
                    height=disc_thickness,
                    direction=disc_direction).triangulate()

    theta_0 = np.arctan(disc_radius/disc_height)
    analytical_f = 1 - (np.sin(theta_0))**2

# Initiation of the mesh object containing points of interest to compute light
M = Mesh()

# Add sensors to the scene
step = disc_radius
start = -disc_radius
stop = disc_radius

x_sensors = np.arange(start, stop+step, step=step)
y_sensors = np.arange(start, stop+step, step=step)

for y, x in product(y_sensors, x_sensors):
    M.add_triangular_probe(position=(x, y, 0), normal=(0, 0, 1), area=0.01)

# Initialize and run light ray casting model (direct and diffuse) with points of interest and scene


MFs = [1, 2, 4, 6, 8]
results_indices = ['point ID', 0, 1, 2, 3, 4, 5, 6, 7, 8, 'Relative error center point [0-1]', 'COV corners', 'COV midpoints', 'Test result']
results = []
results_cols = ['point ID']

for MF in MFs:
    results_cols.append(f'MF: {MF}')

    discrete_sky = ReinhartSky(MF=MF).reinhart_patches

    L = Ray_casting_scene(mesh=M, geometry=disc, discrete_sky=discrete_sky)

    L.diffuse_mask = L.get_diffuse_mask(L.geometry)

    L.get_diffuse_weights_map()

    L.get_diffuse_shaded_weights_map()

    if PLOT:
        L.visualize_diffuse_light_map(0)

    L.diffuse_shaded_weights_map = L.diffuse_shaded_weights_map.sum(axis=1)

    print(f'{MF=}')
    if VERBOSE:
        print(L.diffuse_shaded_weights_map[0:3])
        print(L.diffuse_shaded_weights_map[3:6])
        print(L.diffuse_shaded_weights_map[6:9])

    # Check value at center
    center_id = 4
    center_computed_value = L.diffuse_shaded_weights_map[center_id]
    print(f'Center point computed value = {center_computed_value}')
    print(f'Center point expected value = {analytical_f}')
    rel_error_center_value = (1 - center_computed_value / analytical_f)  # [-]
    print(f'Relative error on center value = {rel_error_center_value:.3g}')

    # Analyze corners
    corners_ids = [0, 2, 6, 8]
    print(10 * '-')
    print("Corners' values:")
    if VERBOSE:
        print(L.diffuse_shaded_weights_map[corners_ids])
    print('coef of var =', L.diffuse_shaded_weights_map[corners_ids].std() / L.diffuse_shaded_weights_map[corners_ids].mean())
    cov_corners = L.diffuse_shaded_weights_map[corners_ids].std() / L.diffuse_shaded_weights_map[corners_ids].mean()

    # Analyze midpoints
    midpoints_ids = [1, 3, 5, 7]
    print(10 * '-')
    print("Midpoints' values:")
    if VERBOSE:
        print(L.diffuse_shaded_weights_map[midpoints_ids])
    print('coef of var =', L.diffuse_shaded_weights_map[midpoints_ids].std() / L.diffuse_shaded_weights_map[midpoints_ids].mean())
    cov_midpoints = L.diffuse_shaded_weights_map[midpoints_ids].std() / L.diffuse_shaded_weights_map[midpoints_ids].mean()


    TOL_STRICT = 0.01
    TOL_LOOSE  = 0.05

    center_ok_strict  = np.isclose(rel_error_center_value, 0, atol=TOL_STRICT)
    center_ok_loose   = np.isclose(rel_error_center_value, 0, atol=TOL_LOOSE)
    corners_ok_strict  = math.isclose(cov_corners,   0, abs_tol=TOL_STRICT)
    corners_ok_loose   = math.isclose(cov_corners,   0, abs_tol=TOL_LOOSE)
    midpoints_ok_strict = math.isclose(cov_midpoints, 0, abs_tol=TOL_STRICT)
    midpoints_ok_loose  = math.isclose(cov_midpoints, 0, abs_tol=TOL_LOOSE)

    print(20*'=')
    if center_ok_strict and corners_ok_strict and midpoints_ok_strict:
        result = 'passed'
        print('Test passed !')
    elif center_ok_loose and corners_ok_loose and midpoints_ok_loose:
        result = 'borderline'
        failed_criteria = []
        if not center_ok_strict:
            failed_criteria.append(f'center rel. error ({rel_error_center_value:.3g}) > {TOL_STRICT}')
        if not corners_ok_strict:
            failed_criteria.append(f'COV corners ({cov_corners:.3g}) > {TOL_STRICT}')
        if not midpoints_ok_strict:
            failed_criteria.append(f'COV midpoints ({cov_midpoints:.3g}) > {TOL_STRICT}')
        print('Test borderline. Criteria outside strict tolerance: ' + '; '.join(failed_criteria))
    else:
        result = 'FAILED'
        failed_criteria = []
        if not center_ok_loose:
            failed_criteria.append(f'center rel. error ({rel_error_center_value:.3g}) > {TOL_LOOSE}')
        if not corners_ok_loose:
            failed_criteria.append(f'COV corners ({cov_corners:.3g}) > {TOL_LOOSE}')
        if not midpoints_ok_loose:
            failed_criteria.append(f'COV midpoints ({cov_midpoints:.3g}) > {TOL_LOOSE}')
        print('Test FAILED. Failed criteria: ' + '; '.join(failed_criteria))
        
    results.append([L.diffuse_shaded_weights_map[0], L.diffuse_shaded_weights_map[1], L.diffuse_shaded_weights_map[2],
                    L.diffuse_shaded_weights_map[3], L.diffuse_shaded_weights_map[4], L.diffuse_shaded_weights_map[5],
                    L.diffuse_shaded_weights_map[6], L.diffuse_shaded_weights_map[7], L.diffuse_shaded_weights_map[8],
                    rel_error_center_value,
                    cov_corners, cov_midpoints,
                    result])

    # Absolute irradiance check — catches the /N bug and sky_integral normalization bug.
    # For a uniform sky (type 5), an unshaded sensor recovers DHI * analytical_f.
    # The view factor checks above only verify relative geometry; this verifies absolute calibration.
    DHI_ref = 1.0  # W/m²
    df_irr = pd.DataFrame({'DHI': [DHI_ref], 'azimuth': [180.0],
                           'elevation': [45.0], 'CIE Sky Type': [5]})
    irr_map = L.compute_daily_diff_irradiation(df_irr, n_freq=1)  # calls get_diffuse_shaded_weights_map internally
    center_irr_Wh = float(irr_map[center_id] / 3600 * 1e6)
    irr_rel_error = abs(center_irr_Wh / (DHI_ref * analytical_f) - 1)
    irr_ok = math.isclose(irr_rel_error, 0, abs_tol=TOL_LOOSE)
    print(f'Center absolute irradiance: {center_irr_Wh:.4f} W·h/m²'
          f' (expected ≈{DHI_ref * analytical_f:.4f})')
    print(f'Irradiance relative error: {irr_rel_error:.3g}'
          f' (tol={TOL_LOOSE}) → {"OK" if irr_ok else "FAILED"}')

    print('')

print('Computation is over')
df = pd.DataFrame(results).T
df.columns = results_cols[1:]
df.set_index(pd.Series(results_indices[1:]), inplace=True)

# debug 3D view
if DEBUG:
    labels = dict(zlabel='Z (ZENITH)', xlabel='X (EAST)', ylabel='Y (NORTH)')

    plotter = pyV.Plotter()

    plotter.add_mesh(L.geometry, color='black', opacity=0.5)

    ground = np.array([[-20, 20, 0],
                       [20, 20, 0],
                       [-20, -20, 0],
                       [20, -20, 0]])

    ground_m = np.hstack([[3, 0, 1, 2],
                          [3, 1, 2, 3], ])

    grnd = pyV.PolyData(ground, ground_m)

    plotter.add_mesh(grnd, color='green', opacity=0.5)

    plotter.add_axes(**labels)

    spatialized_variable = np.array(L.diffuse_shaded_weights_map, dtype=np.float32)
    lgd_title = 'Diffuse map'
    plotter.add_mesh(L.sourcepoints[:,:],
                     scalars=spatialized_variable,
                     point_size=10,
                     lighting=False,
                     show_edges=False,
                     scalar_bar_args={"title": lgd_title},
                     clim=[spatialized_variable.min(),
                           spatialized_variable.max()])

    # Add vertical lines
    for y, x in product(y_sensors, x_sensors):
        points = np.array([[x, y, 0], [x, y, 1]])

        actor = plotter.add_lines(points, color='purple', width=3)

    plotter.show()

if SAVE:
    fpath = export_benchmark(df,
                             fname_prefix='diffuse_benchmark_disc_',
                             mode='x')

    # Sign with commit metadata
    sign_commit_hash(fpath)
