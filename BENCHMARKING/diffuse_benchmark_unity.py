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

pyV.global_theme.allow_empty_mesh = True

# Configure the scene
geometry = pyV.PolyData()
expected_value = 1

# Initiation of the mesh object containing points of interest to compute light
M = Mesh()

# Add a sensor to the scene
M.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=0.01)

# Build dummy DataFrame for irradiance data
DHI = 1  # W/m²
df = pd.DataFrame.from_dict({'DHI': [DHI],
                             'azimuth': [180],
                             'elevation': [45],
                             'CIE Sky Type': [5]})
print(f'{DHI=} W/m²')

# Initialize and run light ray casting model (direct and diffuse) with points of interest and scene
MFs = [1, 2, 4, 6, 8]
some_test_failed = False
result_dict = {}
indices = pd.Index([0])
for MF in MFs:

    discrete_sky = ReinhartSky(MF=MF).reinhart_patches

    L = Ray_casting_scene(mesh=M, geometry=geometry, discrete_sky=discrete_sky)

    L.diffuse_mask = L.get_diffuse_mask(L.geometry)

    L.get_diffuse_weights_map()

    L.get_diffuse_shaded_weights_map()

    if PLOT:
        L.visualize_diffuse_light_map()

    # L.diffuse_shaded_weights_map = L.diffuse_shaded_weights_map.sum(axis=0)
    daily_diffuse_irradiance = L.compute_daily_diff_irradiation(df, 1, indices=indices)

    print(f'{MF=}')
    print(f'Daily diffuse irradiance = {daily_diffuse_irradiance} MJ/m²')
    print(f'Daily diffuse irradiance = {daily_diffuse_irradiance/(60**2)*1e6} W·h/m²')

    if math.isclose(daily_diffuse_irradiance/(60**2)*1e6, DHI, rel_tol=1e-3):
        print('Test passed')
        result = 'passed'
    else:
        print('Test FAILED !')
        result = 'failed'
        some_test_failed = True
        print(f"Expected 3600 J/m² ; got {daily_diffuse_irradiance*1e6}")

    result_dict.update({f'MF{MF}': result})


print('Computation is over')

if some_test_failed:
    print('Some test failed !!!')
else:
    print('All tests successful')
