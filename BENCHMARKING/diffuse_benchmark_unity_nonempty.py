#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Bouvry Arnaud (abouvry@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.
""""
Benchmark the diffuse irradiance map — unity test with non-empty geometry.

Same as diffuse_benchmark_unity.py but inserts a tiny disc very high above
the sensor, forcing get_diffuse_mask() to return a 2D mask
(n_sources, N_patches) and exercising the ndim==2 path in
get_diffuse_shaded_weights_map().

The disc is sized so that it subtends a negligible solid angle
(blocked view factor < 1e-8), so the expected result remains DHI
within any reasonable tolerance.
"""
import math
import numpy as np
import pandas as pd
import pyvista as pyV

from pase.user_support_tools import PASE_Logger
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky

PASE_Logger()

VERBOSE = True
PLOT = False

pyV.global_theme.allow_empty_mesh = True

# ---------------------------------------------------------------------------
# Scene geometry: a tiny disc placed far above the sensor.
# Blocked view factor = sin²(arctan(R/H)) ≈ (R/H)² for small angles.
# With R=0.001 m and H=1000 m: blocked fraction ≈ 1e-12 → negligible.
# ---------------------------------------------------------------------------
disc_height = 1000.0        # [m] height above the sensor
disc_radius = 0.001         # [m] radius of the tiny disc
disc_thickness = 0.0001     # [m]
disc_offset_X = 100         # [m] offset the disc position relative to the sensor which will be in (0, 0, 0)

blocked_fraction = (disc_radius / disc_height) ** 2
print(f'Tiny disc: radius={disc_radius} m, height={disc_height} m')
print(f'Analytical blocked sky fraction ≈ {blocked_fraction:.2e}  (should be negligible)')

geometry = pyV.Cylinder(center=(disc_offset_X, 0, disc_height),
                        radius=disc_radius,
                        height=disc_thickness,
                        direction=(0, 0, 1)).triangulate()

# ---------------------------------------------------------------------------
# Sensor
# ---------------------------------------------------------------------------
M = Mesh()
M.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=0.01)

# ---------------------------------------------------------------------------
# Dummy irradiance data: 1 timestep, DHI = 1 W/m²
# ---------------------------------------------------------------------------
DHI = 1  # [W/m²]
df = pd.DataFrame({'DHI': [DHI],
                   'azimuth': [180],
                   'elevation': [45],
                   'CIE Sky Type': [5]})
print(f'{DHI=} W/m²')

# ---------------------------------------------------------------------------
# Run for several Multiplying Factors
# ---------------------------------------------------------------------------
MFs = [1, 2, 4, 6, 8]
some_test_failed = False
result_dict = {}
indices = pd.Index([0])

for MF in MFs:

    discrete_sky = ReinhartSky(MF=MF).reinhart_patches

    L = Ray_casting_scene(mesh=M, geometry=geometry, discrete_sky=discrete_sky)

    L.diffuse_mask = L.get_diffuse_mask(L.geometry)

    assert L.diffuse_mask.ndim == 2, (
        f"MF={MF}: expected a 2D diffuse mask (non-empty geometry path), "
        f"got ndim={L.diffuse_mask.ndim}"
    )

    L.get_diffuse_weights_map()
    L.get_diffuse_shaded_weights_map()

    daily_diffuse_irradiance = L.compute_daily_diff_irradiation(df, 1, indices=indices)

    result_W = float(daily_diffuse_irradiance / 3600 * 1e6)  # convert MJ/m² back to W·h/m²

    print(f'{MF=}')
    print(f'Daily diffuse irradiance = {daily_diffuse_irradiance} MJ/m²')
    print(f'Daily diffuse irradiance = {result_W} W·h/m²')

    # Tolerance: 1 % to catch any factor-of-N regression while allowing
    # minor discretization artefacts from the tiny blocking disc.
    if math.isclose(result_W, DHI, rel_tol=0.01):
        print('Test passed')
        result = 'passed'
    else:
        print('Test FAILED !')
        result = 'failed'
        some_test_failed = True
        print(f'Expected {DHI} W·h/m² ; got {result_W:.6f} W·h/m²')

    result_dict[f'MF{MF}'] = result

print()
print('Computation is over')
print(result_dict)

if some_test_failed:
    print('Some test failed !!!')
else:
    print('All tests successful')
