#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Bouvry Arnaud (abouvry@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.
""""
Benchmark the diffuse irradiance map
"""
import os.path
from datetime import datetime
from itertools import product
import logging
import math
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
import pandas as pd
import pyvista as pyV

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.benchmarking import (export_benchmark,
                                               sign_commit_hash,
                                               get_git_revision_short_hash)
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky

DEBUG = False  # Fewer heights for faster debug diagnosis
PLOT = True
PLOT_3D = False
SAVE = False

if SAVE:
    GIT_REV = get_git_revision_short_hash()

if DEBUG:
    logger_lvl = logging.DEBUG
else:
    logger_lvl = logging.INFO
logging.basicConfig(level=logger_lvl)

FNAME_PREFIX = 'diffuse_benchmark_disc_height_'
date_str = datetime.today().strftime('%Y-%m-%d')

def compute_analytical_f(disc_radius, heights):
    theta_0 = np.arctan(disc_radius / heights)
    analytical_f = 1 - (np.sin(theta_0)) ** 2

    return analytical_f

def compute_RMSE(actual, predicted):
    diff = np.subtract(actual, predicted)
    square = np.square(diff)
    mse = square.mean()
    rmse = np.sqrt(mse)

    return rmse

# Various heights
if DEBUG:
    # shorter heights vector for faster debug
    heights = np.linspace(0.1, 1, 4)
else:
    step1 = 0.1
    heights = np.arange(0.1, 1, step=step1)

    step2 = 0.25
    heights = np.concatenate([heights, np.arange(1, 2, step=step2)])

    step3 = 1
    heights = np.concatenate([heights, np.arange(2, 6, step=step3)])

    heights = np.concatenate([heights, [10]])

# Disc constants
disc_direction = (0, 0, 1)
disc_thickness = 0.001
disc_radius = np.sqrt(1/np.pi)

# Analytical view factors
theta_0 = np.arctan(disc_radius/heights)
analytical_f_vec = 1 - (np.sin(theta_0))**2

# Build results DataFrame
df = pd.DataFrame([heights, analytical_f_vec]).T
df.columns = ['Height [m]', 'Analytical view factor']

# Configure sensors' positions in the scene
step = disc_radius
start = -disc_radius
stop = disc_radius

x_sensors = np.arange(start, stop+step, step=step)
y_sensors = np.arange(start, stop+step, step=step)

# Various MF values
if DEBUG:
    # fewer MF values for faster debug
    MFs = [1, 2]
else:
    MFs = [1, 2, 6, 8]

rmse_list = []
for MF in MFs:
    computed_view_factor = []
    rel_error_center_value_list = []

    for disc_height in heights:
        # Configure the scene
        disc_center = (0, 0, disc_height)

        # Compute analytical view factor
        theta_0 = np.arctan(disc_radius / disc_height)
        analytical_f = 1 - (np.sin(theta_0)) ** 2

        disc = pyV.Cylinder(center=disc_center, radius=disc_radius,
                            height=disc_thickness,
                            direction=disc_direction).triangulate()

        # Initiation of the mesh object containing points of interest to compute light
        M = Mesh()

        for y, x in product(y_sensors, x_sensors):
            M.add_triangular_probe(position=(x, y, 0), normal=(0, 0, 1), area=0.01)

        discrete_sky = ReinhartSky(MF=MF).reinhart_patches

        # Iniation and run of light ray casting model (direct and diffuse) with points of interest and scene
        L = Ray_casting_scene(mesh=M, geometry=disc, discrete_sky=discrete_sky)

        L.diffuse_mask = L.get_diffuse_mask(L.geometry)

        L.get_diffuse_weights_map()

        L.get_diffuse_shaded_weights_map()

        if PLOT_3D:
            L.visualize_diffuse_light_map(0)

        L.diffuse_shaded_weights_map = L.diffuse_shaded_weights_map.sum(axis=1)

        logging.info(f'{MF=}, height = {disc_height} m')
        logging.debug(L.diffuse_shaded_weights_map[0:3])
        logging.debug(L.diffuse_shaded_weights_map[3:6])
        logging.debug(L.diffuse_shaded_weights_map[6:9])

        # Check value at center
        center_id = 4
        center_computed_value = L.diffuse_shaded_weights_map[center_id]
        logging.debug(f'Center point computed value = {center_computed_value}')
        logging.debug(f'Center point expected value = {analytical_f}')
        rel_error_center_value = (1 - center_computed_value/analytical_f)  # [-]
        logging.debug(f'Relative error on center value = {rel_error_center_value:.3g}')
        # results.append([center_computed_value, rel_error_center_value])
        computed_view_factor.append(center_computed_value)
        rel_error_center_value_list.append(rel_error_center_value)

        # Analyze corners
        corners_ids = [0, 2, 6, 8]
        logging.debug(10 * '-')
        logging.debug("Corners' values:")
        logging.debug(L.diffuse_shaded_weights_map[corners_ids])
        cov_corners = L.diffuse_shaded_weights_map[corners_ids].std() / L.diffuse_shaded_weights_map[corners_ids].mean()
        logging.debug(f'coef of var = {cov_corners}')

        # Analyze midpoints
        midpoints_ids = [1, 3, 5, 7]
        logging.debug(10 * '-')
        logging.debug("Midpoints' values:")
        logging.debug(L.diffuse_shaded_weights_map[midpoints_ids])
        cov_midpoints = L.diffuse_shaded_weights_map[midpoints_ids].std() / L.diffuse_shaded_weights_map[midpoints_ids].mean()
        logging.debug(f'coef of var = {cov_midpoints}')

        TOL_STRICT = 0.01
        TOL_LOOSE  = 0.05

        center_ok_strict   = np.isclose(rel_error_center_value, 0, atol=TOL_STRICT)
        center_ok_loose    = np.isclose(rel_error_center_value, 0, atol=TOL_LOOSE)
        corners_ok_strict  = math.isclose(cov_corners,   0, abs_tol=TOL_STRICT)
        corners_ok_loose   = math.isclose(cov_corners,   0, abs_tol=TOL_LOOSE)
        midpoints_ok_strict = math.isclose(cov_midpoints, 0, abs_tol=TOL_STRICT)
        midpoints_ok_loose  = math.isclose(cov_midpoints, 0, abs_tol=TOL_LOOSE)

        logging.debug(20*'=')
        if center_ok_strict and corners_ok_strict and midpoints_ok_strict:
            result = 'passed'
            logging.info('Test passed !')
        elif center_ok_loose and corners_ok_loose and midpoints_ok_loose:
            result = 'borderline'
            failed_criteria = []
            if not center_ok_strict:
                failed_criteria.append(f'center rel. error ({rel_error_center_value:.3g}) > {TOL_STRICT}')
            if not corners_ok_strict:
                failed_criteria.append(f'COV corners ({cov_corners:.3g}) > {TOL_STRICT}')
            if not midpoints_ok_strict:
                failed_criteria.append(f'COV midpoints ({cov_midpoints:.3g}) > {TOL_STRICT}')
            logging.info('Test borderline. Criteria outside strict tolerance: ' + '; '.join(failed_criteria))
        else:
            result = 'FAILED'
            failed_criteria = []
            if not center_ok_loose:
                failed_criteria.append(f'center rel. error ({rel_error_center_value:.3g}) > {TOL_LOOSE}')
            if not corners_ok_loose:
                failed_criteria.append(f'COV corners ({cov_corners:.3g}) > {TOL_LOOSE}')
            if not midpoints_ok_loose:
                failed_criteria.append(f'COV midpoints ({cov_midpoints:.3g}) > {TOL_LOOSE}')
            logging.info('Test FAILED. Failed criteria: ' + '; '.join(failed_criteria))

        logging.debug('')

        logging.debug('Loop end')

    df[f'MF:{MF} computed value'] = computed_view_factor
    df[f'MF:{MF} rel error'] = rel_error_center_value_list

    rmse_list.append(compute_RMSE(computed_view_factor, analytical_f_vec))

logging.debug('Computations over')

df_rmse = pd.DataFrame([MFs, rmse_list]).T
df_rmse.columns = ['MF', 'RMSE']
df_rmse.set_index('MF', inplace=True)

logging.info(df_rmse)

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

# Save results
if SAVE:
    # Save to disk and return file name
    fpath = export_benchmark(df,
                             fname_prefix=FNAME_PREFIX,
                             mode='x')
    # Append RMSE dataframe to the same file
    export_benchmark(df_rmse, fpath=fpath, mode='a')

    # Sign with commit metadata
    sign_commit_hash(fpath)

# Plot results graph

colors = plt.cm.rainbow(np.linspace(0, 1, len(MFs)))

fig = plt.figure()
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))
ax.plot(heights, analytical_f_vec, 'k-', label='analytical value')
for i, MF in enumerate(MFs):
    ax.plot(heights, df[f'MF:{MF} computed value'], 'x-', label=f'MF:{MF}', color=colors[i])

ax.set_xlabel('Height [m]')
ax.set_ylabel('View factor [-]')

ax.legend()

if SAVE:
    # Annotate with GIT_REV
    fig_annotation = f'generated with git rev {GIT_REV}'
    fig.text(1, 0.05, fig_annotation, ha='right')

    # Save figure to disk
    fig_format = 'svg'
    figname = FNAME_PREFIX + date_str + '.' + fig_format
    figpath = os.path.join('OUTPUTS', figname)
    plt.savefig(figpath, transparent=False, format='svg')

if PLOT:
    plt.show()

# Plot error graph
fig = plt.figure()
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))

for i, MF in enumerate(MFs):
    markerline, stemlines, baseline = ax.stem(heights,
                                               df[f'MF:{MF} rel error'],
                                               label=f'MF:{MF}',
                                               basefmt='k-')

    stemlines.set_edgecolor(colors[i])
    markerline.set_markerfacecolor('none')
    markerline.set_markeredgecolor(colors[i])

ax.set_xlabel('Height [m]')
ax.set_ylabel('View factor rel error [%]')

ax.legend()

if SAVE:
    # Annotate with GIT_REV
    fig_annotation = f'generated with git rev {GIT_REV}'
    fig.text(1, 0.05, fig_annotation, ha='right')

    # Save figure to disk
    fig_format = 'svg'
    figname = FNAME_PREFIX + 'rel_err_' + date_str + '.' + fig_format
    figpath = os.path.join('OUTPUTS', figname)
    plt.savefig(figpath, transparent=False, format='svg')

if PLOT:
    plt.show()

