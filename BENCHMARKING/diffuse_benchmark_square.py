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
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from pase.DATA_MANAGEMENT.weather_data_provider import Weather_data
from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization
from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.CROPS.run_crop_simulations import run_crop_simu, visualize_map_of_a_variable

PASE_Logger()

DEBUG = False
PLOT = True
SAVE = False

# Instantiation of the 3D PV central
PV_params_dict = {'PanelDimensionX': 1,
                  'PanelDimensionY': 1,
                  'PanelThickness': False,
                  'RepetitionDistanceOfPanelsX': 1,
                  'RepetitionDistanceOfPanelsY': 1,
                  'NumberOfPanelsX': 1,
                  'NumberOfPanelsY': 1,
                  'RepetitionDistanceOfPVBlocksX': 1,
                  'RepetitionDistanceOfPVBlocksY': 1,
                  'NumberOfPVBlocksX': 1,
                  'NumberOfPVBlocksY': 1,
                  'Height': 1,
                  'CentralAzimut': 0,
                  'TiltY': 0,
                  'TwoFacetsRelativePosition': 0,
                  'RotationAxisNumber': 0,
                  'Hinge': 'center'}

# Configure the scene
PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict,
                                    None,
                                    visualization=False)

# Initiation of the mesh object containing points of interest to compute light
M = Mesh()

# Add sensors to the scene
step = 0.5
start = -0.5
stop = 0.5

x_sensors = np.arange(start, stop+step, step=step)
y_sensors = np.arange(start, stop+step, step=step)

for y, x in product(y_sensors, x_sensors):
    M.add_triangular_probe(position=(x, y, 0), normal=(0, 0, 1), area=0.01)


MFs = [1, 2, 4, 8]
results_indices = ['point ID', 0, 1, 2, 3, 4, 5, 6, 7, 8, 'COV corners', 'COV midpoints', 'Test result']
results = []
results_cols = ['point ID']

for MF in MFs:
    results_cols.append(f'MF: {MF}')

    discrete_sky = ReinhartSky(MF=MF).reinhart_patches

    # Iniation and run of light ray casting model (direct and diffuse) with points of interest and scene
    L = Ray_casting_scene(mesh=M, geometry=PV_1_3Dconfig.PV_central_PD, discrete_sky=discrete_sky)

    L.diffuse_mask = L.get_diffuse_mask(L.geometry)

    L.get_diffuse_weights_map()

    L.get_diffuse_shaded_weights_map()

    if PLOT:
        L.visualize_diffuse_light_map(0)

    L.diffuse_shaded_weights_map = L.diffuse_shaded_weights_map.sum(axis=1)

    print(f'{MF=}')
    print(L.diffuse_shaded_weights_map[0:3])
    print(L.diffuse_shaded_weights_map[3:6])
    print(L.diffuse_shaded_weights_map[6:9])

    # Analyze corners

    corners_ids = [0, 2, 6, 8]
    print(10 * '-')
    print("Corners' values:")
    print(L.diffuse_shaded_weights_map[corners_ids])
    print('coef of var =', L.diffuse_shaded_weights_map[corners_ids].std() / L.diffuse_shaded_weights_map[corners_ids].mean())
    cov_corners = L.diffuse_shaded_weights_map[corners_ids].std() / L.diffuse_shaded_weights_map[corners_ids].mean()

    # Analyze midpoints
    midpoints_ids = [1, 3, 5, 7]
    print(10 * '-')
    print("Midpoints' values:")
    print(L.diffuse_shaded_weights_map[midpoints_ids])
    print('coef of var =', L.diffuse_shaded_weights_map[midpoints_ids].std() / L.diffuse_shaded_weights_map[midpoints_ids].mean())
    cov_midpoints = L.diffuse_shaded_weights_map[midpoints_ids].std() / L.diffuse_shaded_weights_map[midpoints_ids].mean()


    TOL_STRICT = 0.01
    TOL_LOOSE  = 0.05

    corners_ok_strict  = math.isclose(cov_corners,   0, abs_tol=TOL_STRICT)
    corners_ok_loose   = math.isclose(cov_corners,   0, abs_tol=TOL_LOOSE)
    midpoints_ok_strict = math.isclose(cov_midpoints, 0, abs_tol=TOL_STRICT)
    midpoints_ok_loose  = math.isclose(cov_midpoints, 0, abs_tol=TOL_LOOSE)

    print(20*'=')
    if corners_ok_strict and midpoints_ok_strict:
        result = 'passed'
        print('Test passed !')
    elif corners_ok_loose and midpoints_ok_loose:
        result = 'borderline'
        failed_criteria = []
        if not corners_ok_strict:
            failed_criteria.append(f'COV corners ({cov_corners:.3g}) > {TOL_STRICT}')
        if not midpoints_ok_strict:
            failed_criteria.append(f'COV midpoints ({cov_midpoints:.3g}) > {TOL_STRICT}')
        print('Test borderline. Criteria outside strict tolerance: ' + '; '.join(failed_criteria))
    else:
        result = 'FAILED'
        failed_criteria = []
        if not corners_ok_loose:
            failed_criteria.append(f'COV corners ({cov_corners:.3g}) > {TOL_LOOSE}')
        if not midpoints_ok_loose:
            failed_criteria.append(f'COV midpoints ({cov_midpoints:.3g}) > {TOL_LOOSE}')
        print('Test FAILED. Failed criteria: ' + '; '.join(failed_criteria))
    results.append([L.diffuse_shaded_weights_map[0], L.diffuse_shaded_weights_map[1], L.diffuse_shaded_weights_map[2],
                    L.diffuse_shaded_weights_map[3], L.diffuse_shaded_weights_map[4], L.diffuse_shaded_weights_map[5],
                    L.diffuse_shaded_weights_map[6], L.diffuse_shaded_weights_map[7], L.diffuse_shaded_weights_map[8],
                    cov_corners, cov_midpoints, result])
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

    ground = np.array([[-200, 200, 0],
                       [200, 200, 0],
                       [-200, -200, 0],
                       [200, -200, 0]])

    ground_m = np.hstack([[3, 0, 1, 2],
                          [3, 1, 2, 3], ])

    grnd = pyV.PolyData(ground, ground_m)

    plotter.add_mesh(grnd, color='green', opacity=0.5)

    plotter.add_axes(**labels)

    spatialized_variable = np.array(L.diffuse_mask, dtype=np.float32)
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
                             fname_prefix='diffuse_benchmark_square_',
                             mode='x')

    # Sign with commit metadata
    sign_commit_hash(fpath)
