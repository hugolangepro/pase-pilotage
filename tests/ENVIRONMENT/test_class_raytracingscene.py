import math
import numpy as np
import pandas as pd
import pytest
import pyvista as pyV

from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.diffuser import LenticularDiffuser


def _diffuser_trace(x, x0, a, l, theta_max):
    """
    Trace of a diffuser parallel to the "ground", with an incoming light of unit
    energy, normal to the plane of the diffuser.

     Input:
        x (1d vector of size len(x)): coordinates to which a value of the function will be computed
        x0 (scalar): center of the diffuser
        a (scalar): height of the diffuser
        l (scalar): length of the diffuser
        theta_max (scalar): half of the aperture angle of the diffuser lens in radians
    x, x0, a, and l are length and should have the same units.
    Output:
        I (1d vector of size len(x)): Intensity repartition of the energy on the "ground" in m-1 m_{perp}-1
        tan(DB*I) = a*(beta-alpha)/(a^2 + x^2 - x*(beta+alpha)+alpha*beta)
    Variables:
        alpha (1d vector of size len(x)): maximum between x0-l/2 and x-a*tan(DB/2), same length units
        beta (1d vector of size len(x)): minimum between x0+l/2 and x+a*tan(DB/2), same length units
    """
    alpha = np.maximum(x0 - l * np.ones(len(x)) / 2, x - a * np.tan(theta_max))
    beta = np.minimum(x0 + l * np.ones(len(x)) / 2, x + a * np.tan(theta_max))
    I = np.arctan(a*(beta-alpha)/(a**2+x**2-x*(beta+alpha)+alpha*beta))/(2 * theta_max)
    ind = np.where(I < 0)
    I[ind] = 0
    return I


def _create_example_central():  # creation of example centrals
    cfg = [PVConfiguration3D(), PVConfiguration3D(), PVConfiguration3D()]

    base_dict = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=2.1,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,RotationAxisNumber=0,
        CentralAzimut=0.0, TiltY=10.0, Height=2.0,NumberOfPanelsX=2, NumberOfPanelsY=2, Hinge='Center'
    )
    variants ={"PV_A":dict(),
               "PV_B":dict(DiffuserDimensionZ=0.003,DiffuserDimensionX=1,
                           DiffuserDimensionY=1.6, DiffusersBetweenPanels=True,
                           DiffusersAtRowEnds=False,DiffusersFillXAxis=True),
               "PV_C":dict(DiffuserDimensionZ=0.003,DiffuserDimensionX=1,
                           DiffuserDimensionY=1.6, DiffusersBetweenPanels=True,
                           DiffusersAtRowEnds=False,DiffusersFillXAxis=True, TiltY=0.0)}
    M = Mesh()
    loc = dict(InterestZoneOrientationMode='custom', InterestZoneCustomAngle=0)

    M.set_interest_zone_orientation(loc, base_dict|variants["PV_C"])
    M.add_rectangular_surface(
        width=2,
        height=2,
        density=0.1,
        name="crop",
        center=(0.0, 0.0, 0.0),
        normal=(0.0, 0.0, 1.0),
        reference_direction=(1.0, 0.0, 0.0),
        face_type="rectangle",
    )

    cfg[0].create_regular_central(base_dict|variants["PV_A"])
    cfg[1].create_regular_central(base_dict|variants["PV_B"])
    cfg[2].create_regular_central(base_dict|variants["PV_C"])
    return cfg, M


sky = ReinhartSky(MF=1).reinhart_patches
suns = np.array([np.array([i, j, 1]).reshape((1,3))/np.sqrt(i**2+j**2+1)
                 for i in range(-1, 2, 1)
                 for j in range(-1, 2, 1)]).reshape((9, 3))
Diffusers = LenticularDiffuser(0, 10, omega = 30)
Diffusers2 = LenticularDiffuser(0, 0, omega = 30)


def test_check_mask_Ray_casting_scene():
    """Test the shape of the different masks"""
    geometry,M = _create_example_central()
    L = Ray_casting_scene(M, geometry[0], sky) # test with example 1
    L.get_light_maps(suns,visualization=False,Sun_P_map_to_visualize=3)
    assert list(L.masks.keys()) == ['Diffuse', 'PV'] # check the keys of the visualisation matrices
    L = Ray_casting_scene(M, geometry[1], sky, diffusers=Diffusers)
    L.get_light_maps(suns, visualization=False, Sun_P_map_to_visualize=3)
    assert list(L.masks.keys()) == ['Diffuse', 'Diffuser', 'PV']
    assert L.masks['Diffuser'].shape == (M.sourcepoints.shape[0], len(sky)) # check the shape of the visualisation
    assert L.masks['PV'].shape == (M.sourcepoints.shape[0], len(sky))       # matrices
    assert L.masks['Diffuse'].shape == (M.sourcepoints.shape[0], len(sky))


def test_self_intercept():
    """Test the self-intercept function. Add a small delta to the rays and check the filtering based on this delta"""
    geometry, M = _create_example_central()
    L = Ray_casting_scene(M, geometry[0], sky)
    sourcepoints = M.sourcepoints[:, :3]
    Delta = np.zeros(sourcepoints.shape)
    Delta[5:, 0] = 0.005
    Delta[10:20, 1] = 0.01
    Delta[20:, 2] = 0.005
    Rays = np.arange(0, sourcepoints.shape[0], 1)
    Cells = np.zeros_like(Rays)
    R_filt, C_filt = L.self_intercept(sourcepoints, sourcepoints+Delta, Rays, Cells)
    ind = np.where(np.linalg.norm(Delta, axis=1)>0.01)
    assert (R_filt == Rays[ind]).all() # test if the 'delta' filtering is working


def test_compute_diffuser_map():
    """
    1) Calculate the diffuser map in the standard way and compare it with another similar calculation.
    2) Test energy conservation. The integral of the diffuser map shouldn't be
    higher than the area of the diffuser times 1 (the value of the unit radiation). In this case the diffuser area
    is 1.6 m² ==> The integral shouldn't be higher than 1.6 m²"""
    geometry, M = _create_example_central()
    mesh_data = M.get_mesh_data("crop")
    cell_area = mesh_data["areas"][0]

    L = Ray_casting_scene(M, geometry[2], sky, diffusers=Diffusers2)
    L.get_light_maps(suns,visualization=False)
    maps = L.diffuser_map
    pTarget = np.column_stack([sky.x, sky.y, sky.z])
    weight = Diffusers2.get_light_direction(suns, pTarget, sky['Normalized surf area'], np.sqrt(np.min(sky['solid_angle_sr'])))
    _cos_elev_patch = sky['cos(z)']
    diffuser_map = np.zeros((weight.shape[0], L.masks['Diffuser'].shape[0]))
    for i in range(weight.shape[0]):
        for k in range(L.masks['Diffuser'].shape[0]):
            for j in range(weight.shape[1]):
                diffuser_map[i, k]+=weight[i, j]*_cos_elev_patch[j]*L.masks['Diffuser'][k, j]
    assert np.allclose(maps, diffuser_map, rtol=1e-05)

    # in the following assertion, 1.6 comes from the fact that the diffuser is a
    # rectangle of 1mx1.6 m  (i.e. 1.6 m² area) and the light rays are unit rays ; thus
    # by conservation of energy no value should be greater than 1.6 units of energy
    assert (np.sum(diffuser_map, axis=1)*cell_area <= 1.6).all()


def test_diffuser_map_theory():
    """
    Compare the transfer function implementation against the discretized analytical
    solution.
    """
    sky = ReinhartSky(MF=8).reinhart_patches
    geometry, M = _create_example_central()
    L = Ray_casting_scene(M, geometry[2], sky, diffusers=Diffusers2)  # example 3
    L.get_light_maps(np.array([0,0,1]).reshape((1,3)), visualization=False)
    maps = L.diffuser_map

    # take the indices of the cells on the sixth line
    ind = np.where(np.isclose(M.sourcepoints[:, 0], np.unique(M.sourcepoints[:, 0])[5]))
    maps = maps[0, ind]

    x = np.linspace(min(M.sourcepoints[:, 0]), max(M.sourcepoints[:, 0]), maps.size)
    F = _diffuser_trace(x, 0, 2, 1, np.radians(30))  # build the ground truth

    assert np.allclose(maps, F, atol=1e-1)


def test_compute_daily_diffuser_irradiation():
    """
    Test the time integration of the irradiation on a day for the diffuser
    Compare the standard method with an alternative one.
    """

    geometry, M = _create_example_central()
    L = Ray_casting_scene(M, geometry[2], sky, diffusers=Diffusers2)
    L.get_light_maps(suns,visualization=False)
    ghi = np.arange(1, 25, 1)
    sunIndex = np.random.randint(0, 9, 24)
    df = pd.DataFrame({'GHI': ghi, 'SolPosInd': sunIndex})
    Irr = L.compute_daily_diffuser_irradiation(df, 1)
    Irr2 = np.sum(L.diffuser_map[sunIndex, :]*ghi[:, np.newaxis], axis=0) * 3600.0 * 1e-6

    assert np.allclose(Irr, Irr2)


# ---------------------------------------------------------------------------
# compute_daily_diff_irradiation must recover DHI for all CIE sky types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('sky_type', [1, 4, 5, 7, 11, 13])
def test_diffuse_irr_unity_all_sky_types(sky_type):
    """
    For any CIE sky type, an unobstructed sensor with non-empty geometry
    (2D mask path) must recover DHI within 1 %.
    The geometry is a tiny disc placed far away so it blocks a negligible
    fraction of the sky (~1e-12), forcing the 2D mask path without introducing
    meaningful shading.
    """
    pyV.global_theme.allow_empty_mesh = True
    geometry = pyV.Cylinder(center=(100, 0, 1000), radius=0.001,
                            height=0.0001, direction=(0, 0, 1)).triangulate()
    M = Mesh()
    M.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=0.01)
    discrete_sky = ReinhartSky(MF=1).reinhart_patches
    DHI = 1.0  # W/m²
    df = pd.DataFrame({'DHI': [DHI], 'azimuth': [180.0],
                       'elevation': [45.0], 'CIE Sky Type': [sky_type]})
    L = Ray_casting_scene(mesh=M, geometry=geometry, discrete_sky=discrete_sky)
    L.diffuse_mask = L.get_diffuse_mask(L.geometry)
    L.get_diffuse_weights_map()
    L.get_diffuse_shaded_weights_map()
    result = L.compute_daily_diff_irradiation(df, n_freq=1, indices=pd.Index([0]))
    result_Wh = float(result[0] / 3600 * 1e6)  # MJ/m² → W·h/m²
    assert math.isclose(result_Wh, DHI, rel_tol=0.01), (
        f"sky_type={sky_type}: expected {DHI} W·h/m², got {result_Wh:.6f}. "
        f"Possible sky_integral normalization bug."
    )


# ---------------------------------------------------------------------------
# get_diffuse_shaded_weights_map must produce 2D output for empty geometry
# ---------------------------------------------------------------------------

def test_diffuse_shaded_weights_map_2d_for_empty_geometry():
    """
    get_diffuse_shaded_weights_map() must return a 2D
    array of shape (n_sources, N_patches) even when the scene is empty.
    For an unshaded sensor the row sum must equal 1 (energy conservation).
    """
    pyV.global_theme.allow_empty_mesh = True
    M = Mesh()
    M.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=0.01)
    discrete_sky = ReinhartSky(MF=1).reinhart_patches
    N = len(discrete_sky)
    L = Ray_casting_scene(mesh=M, geometry=pyV.PolyData(), discrete_sky=discrete_sky)
    L.diffuse_mask = L.get_diffuse_mask(L.geometry)
    L.get_diffuse_weights_map()
    L.get_diffuse_shaded_weights_map()
    assert L.diffuse_shaded_weights_map.ndim == 2, (
        f"Expected 2D weights map for empty geometry, "
        f"got ndim={L.diffuse_shaded_weights_map.ndim}"
    )
    assert L.diffuse_shaded_weights_map.shape == (1, N)
    row_sum = float(L.diffuse_shaded_weights_map.sum(axis=1)[0])
    assert math.isclose(row_sum, 1.0, rel_tol=1e-3), (
        f"Row sum should be 1.0 for unshaded sensor, got {row_sum:.6f}"
    )
