#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import pytest
import pyvista as pyV
from scipy.interpolate import interp1d

from pase.ENVIRONMENT.shading import Horizon
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_horizon(flat_elevation=5.0):
    """Return a Horizon with a flat synthetic profile (no PVGIS call)."""
    h = Horizon(lat=50.0, lon=4.0)
    azimuths = np.array([0.0, 360.0])
    elevations = np.array([flat_elevation, flat_elevation])
    h.interp_func = interp1d(azimuths, elevations,
                             kind='linear', fill_value="extrapolate")
    return h


def _create_simple_scene():
    """Return a minimal (cfg, mesh, sky) tuple for integration tests."""
    params = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=2.1,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1, RotationAxisNumber=0,
        CentralAzimut=0.0, TiltY=10.0, Height=2.0,
        NumberOfPanelsX=2, NumberOfPanelsY=2, Hinge='Center'
    )
    cfg = PVConfiguration3D()
    cfg.create_regular_central(params)

    M = Mesh()
    loc = dict(InterestZoneOrientationMode='custom', InterestZoneCustomAngle=0)
    M.set_interest_zone_orientation(loc, params)
    M.add_rectangular_surface(
        width=2, height=2, density=0.1, name="crop",
        center=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0),
        reference_direction=(1.0, 0.0, 0.0), face_type="rectangle"
    )

    sky = ReinhartSky(MF=1).reinhart_patches
    return cfg, M, sky


# Sun vector with elevation ~26° (el = arcsin(0.5/norm))
_SUN = np.array([[0.0, 1.0, 0.5]])
_SUN = _SUN / np.linalg.norm(_SUN)


# ─────────────────────────────────────────────
# Unit tests — Horizon class
# ─────────────────────────────────────────────

def test_horizon_mask_sun_above():
    """Sun well above horizon → visible."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, 45) == True


def test_horizon_mask_sun_below():
    """Sun below horizon → not visible."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, -5) == False


def test_horizon_mask_at_exact_boundary():
    """Sun exactly at horizon elevation → NOT visible (strict >)."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, 5.0) == False


def test_horizon_mask_just_above_boundary():
    """Sun just above horizon elevation → visible."""
    h = _make_horizon(flat_elevation=5.0)
    assert h.is_sun_visible(180, 5.01) == True


def test_horizon_mask_azimuth_normalization():
    """Azimuths outside [0, 360] are normalized correctly."""
    h = _make_horizon(flat_elevation=5.0)
    # 370° ≡ 10° : sun at el=45 should be visible
    assert h.is_sun_visible(370, 45) == True
    # 370° ≡ 10° : sun at el=2 should be blocked
    assert h.is_sun_visible(370, 2) == False


def test_horizon_mask_no_profile():
    """If no profile is loaded, all positions are assumed visible."""
    h = Horizon(lat=50.0, lon=4.0)
    azimuths = np.array([0.0, 90.0, 180.0, 270.0])
    elevations = np.array([0.0, 0.0, 0.0, 0.0])
    result = h.get_horizon_mask(azimuths, elevations)
    assert np.all(result)


def test_horizon_mask_array_input():
    """Array inputs: mixed visible/blocked positions."""
    h = _make_horizon(flat_elevation=5.0)
    azimuths = np.array([0.0, 90.0, 180.0, 270.0])
    elevations = np.array([10.0, 3.0, 20.0, 1.0])  # above, below, above, below
    result = h.is_sun_visible(azimuths, elevations)
    expected = np.array([True, False, True, False])
    assert np.array_equal(result, expected)


# ─────────────────────────────────────────────
# Integration tests — Horizon + Ray_casting_scene
# ─────────────────────────────────────────────

def test_direct_mask_horizon_blocks_all():
    """Horizon at 89° blocks all sun positions with elevation < 89°."""
    cfg, M, sky = _create_simple_scene()
    h = _make_horizon(flat_elevation=89.0)
    L = Ray_casting_scene(M, cfg, sky, horizon=h)
    direct_mask = L.get_direct_mask(_SUN, cfg)
    assert np.all(direct_mask == 0)


def test_direct_mask_horizon_no_effect():
    """Horizon at -5° (below all sun positions) → same result as without horizon."""
    cfg, M, sky = _create_simple_scene()
    h = _make_horizon(flat_elevation=-5.0)
    L_with = Ray_casting_scene(M, cfg, sky, horizon=h)
    L_without = Ray_casting_scene(M, cfg, sky)
    mask_with = L_with.get_direct_mask(_SUN, cfg)
    mask_without = L_without.get_direct_mask(_SUN, cfg)
    assert np.array_equal(mask_with, mask_without)


# ─────────────────────────────────────────────
# Diffuse irradiance — analytical horizon tests
# ─────────────────────────────────────────────
#
# For a uniform-radiance sky, diffuse irradiance on a horizontal surface is:
#
#   E = ∫ L·cos(θ)·dΩ  over the visible sky
#     = πL · cos²(el₀)
#
# where el₀ is the flat horizon elevation threshold (el > el₀ → visible).
# The fraction of irradiance remaining is therefore cos²(el₀).
#
# The discrete Reinhart sky weight w_j = cos(z_j) × A_normalized_j
# approximates this: Σ_{j: el_j > el₀} w_j / Σ_all w_j ≈ cos²(el₀).


def _sky_horizon_fraction(patches, horizon):
    """Fraction of normalized diffuse weight visible through horizon."""
    visible = horizon.get_horizon_mask(patches['az'].values, patches['el'].values)
    w = patches['cos(z)'].values * patches['Normalized surf area'].values
    return float(w[visible].sum() / w.sum())


def test_horizon_diffuse_fraction_lower_half_sky_area():
    """Horizon at 30° blocks the lower half of sky by surface area → fraction ≈ cos²(30°) = 0.75.

    The sky hemisphere surface area up to elevation el₀ is 2π·sin(el₀).
    For el₀ = 30°, sin(30°) = 0.5, so exactly half the surface is hidden.
    """
    sky = ReinhartSky(MF=4)
    h = _make_horizon(flat_elevation=30.0)
    fraction = _sky_horizon_fraction(sky.reinhart_patches, h)
    assert abs(fraction - 0.75) < 0.03


@pytest.mark.parametrize('el_threshold', [30.0, 45.0, 60.0])
def test_horizon_diffuse_fraction_matches_cos2_analytical(el_threshold):
    """Fraction of diffuse weight visible through flat horizon at el° ≈ cos²(el°).

    Analytical derivation:
        E_visible / E_full
          = ∫_{el>el₀} sin(el)·cos(el) dΩ / ∫_hemisphere sin(el)·cos(el) dΩ
          = cos²(el₀)

    Tolerance of 0.03 accounts for Reinhart MF=4 discretization error
    (~alpha × cos(el)·sin(el) × π/180 ≈ 0.028 at worst).
    """
    sky = ReinhartSky(MF=4)
    h = _make_horizon(flat_elevation=el_threshold)
    fraction = _sky_horizon_fraction(sky.reinhart_patches, h)
    expected = np.cos(np.radians(el_threshold)) ** 2
    assert abs(fraction - expected) < 0.03, (
        f"el={el_threshold}°: got {fraction:.4f}, expected {expected:.4f}"
    )


def test_horizon_below_all_patches_full_sky():
    """Horizon below all patches (-1°) → all patches visible → fraction = 1.0."""
    sky = ReinhartSky(MF=4)
    h = _make_horizon(flat_elevation=-1.0)
    fraction = _sky_horizon_fraction(sky.reinhart_patches, h)
    assert abs(fraction - 1.0) < 1e-10


def test_horizon_89deg_nearly_all_blocked():
    """Horizon at 89° blocks almost all sky → fraction ≈ cos²(89°) ≈ 0.0003."""
    sky = ReinhartSky(MF=4)
    h = _make_horizon(flat_elevation=89.0)
    fraction = _sky_horizon_fraction(sky.reinhart_patches, h)
    assert fraction < 0.005


def test_horizon_diffuse_irradiance_cos2_fraction_via_scene():
    """Horizon at 45° reduces DHI to cos²(45°) = 50% through the full pipeline.

    Uses an empty PolyData geometry so only the horizon blocks sky patches
    (no panel geometry → 2D mask path via the AttributeError branch in
    get_diffuse_mask). Sky type 5 (uniform) ensures sky_integral = 1.0 so
    the get_shaded_radiance_contrib normalization is transparent.
    """
    pyV.global_theme.allow_empty_mesh = True
    el_threshold = 45.0
    h = _make_horizon(flat_elevation=el_threshold)

    M = Mesh()
    M.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=0.01)
    discrete_sky = ReinhartSky(MF=4).reinhart_patches

    DHI = 1.0  # W/m²
    df = pd.DataFrame({
        'DHI': [DHI], 'azimuth': [180.0], 'elevation': [45.0],
        'CIE Sky Type': [5],  # uniform sky → sky_integral = 1.0
    })

    L = Ray_casting_scene(mesh=M, geometry=pyV.PolyData(),
                          discrete_sky=discrete_sky, horizon=h)
    L.diffuse_mask = L.get_diffuse_mask(L.geometry)
    L.get_diffuse_weights_map()
    L.get_diffuse_shaded_weights_map()
    result = L.compute_daily_diff_irradiation(df, n_freq=1, indices=pd.Index([0]))

    result_Wh = float(result[0] / 3600 * 1e6)   # MJ/m² → W·h/m²
    expected = DHI * np.cos(np.radians(el_threshold)) ** 2   # = 0.5
    assert abs(result_Wh - expected) < 0.03, (
        f"expected {expected:.3f} W·h/m², got {result_Wh:.4f}. "
        f"Horizon mask may not propagate correctly through diffuse irradiance computation."
    )