import logging
import math
import numpy as np
import os
import pandas as pd
import pyvista as pv
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import pyplot as plt

from MODULES.conversion_functions import sph_to_cart
from MODULES.ENVIRONMENT.sky_model import ReinhartSky

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

def compute_sph_angular_dist(Z, Z_s, az, az_s):
    """

    Args:
        Z: Sky patch zenith angle [deg]
        Z_s: Solar zenith angle [deg]
        az: Sky patch azimuth angle from north [deg]
        az_s: Solar azimuth angle from north [deg]

    Returns:
        chi: Spherical angular distance [rad]
    """

    # Convert all angles from degrees to radians
    Z = np.deg2rad(Z)
    Z_s = np.deg2rad(Z_s)
    az = np.deg2rad(az)
    az_s = np.deg2rad(az_s)

    # Absolute difference in azimuth angles
    Az = np.abs(az-az_s)

    # Angular distance chi
    chi = np.arccos(np.cos(Z_s) * np.cos(Z) + np.sin(Z_s)*np.sin(Z)*np.cos(Az))

    return chi

def gradation_fun(a, b, Z):
    """
    Gradation function defined to be vectorized in compute_gradation().
    Args:
        a: Horizon-zenith gradient (gradation parameter) [-]
        b: Gradient intensity (gradation parameter) [-]
        Z: zenith angle [rad]

    Returns:
        Gradation value.
    """
    if math.isclose(Z, np.pi/2):
        return 1
    else:
        return 1 + a*np.exp(b/np.cos(Z))

def compute_gradation(a, b, Z):
    """
    Computes the gradation function based on vectorized gradation_fun function.
    Args:
        a: Horizon-zenith gradient (gradation parameter) [-]
        b: Gradient intensity (gradation parameter) [-]
        Z: Zenith angle [deg]. Type : Nx1 array

    Returns:
        gradation function result
    """
    v_gradation = np.vectorize(gradation_fun)

    Z = np.deg2rad(Z)

    return v_gradation(a, b, Z)

def scattering_indicatrix_fun(c, d, e, x):
    """

    Args:
        c: Circumsolar intensity (scattering parameter) [-]
        d: Circumsolar radius (scattering parameter) [-]
        e: Backscattering effect (scattering parameter) [-]
        x: angle (sphericla angular distance or zenith, i.e. 0) [rad]
    Returns:
        Scattering indicatrix value
    """
    return 1 + c * (np.exp(d*x) - np.exp(d*np.pi/2)) + e * (np.cos(x))**2

def get_sky_params(standard_sky):
    """

    Args:
        standard_sky: Dataframe of length 1 with standard sky information

    Returns:
        a: Horizon-zenith gradient (gradation parameter) [-]
        b: Gradient intensity (gradation parameter) [-]
        c: Circumsolar intensity (scattering parameter) [-]
        d: Circumsolar radius (scattering parameter) [-]
        e: Backscattering effect (scattering parameter) [-]
    """

    a = standard_sky['a'].values[0]
    b = standard_sky['b'].values[0]
    c = standard_sky['c'].values[0]
    d = standard_sky['d'].values[0]
    e = standard_sky['e'].values[0]

    return a, b, c, d, e

def luminance_fun(sky_type, patch_az, patch_el, sun_az, sun_el):
    # Standard sky parameters and description
    standard_sky = standard_skies.loc[standard_skies['Type'] == sky_type]

    # Sky model parameters
    a, b, c, d, e = get_sky_params(standard_sky)

    # Elevation to zenith (sky patch)
    Z = 90 - patch_el  # [deg]

    # Elevation to zenith (Sun)
    Z_s = 90 - sun_el  # [deg]

    # Spherical angular dist
    chi = compute_sph_angular_dist(Z, Z_s, patch_az, sun_az)

    # Gradation
    phi = compute_gradation(a, b, Z)
    phi_zenith = compute_gradation(a, b, Z=0)

    # Indicatrix
    indicatrix = scattering_indicatrix_fun(c, d, e, chi)
    indicatrix_zenith = scattering_indicatrix_fun(c, d, e, np.deg2rad(Z_s))

    # Relative luminance
    rel_lum = phi * indicatrix / (phi_zenith * indicatrix_zenith)

    return rel_lum

def compute_luminance(sky_type, patch_az, patch_el, sun_az, sun_el):
    v_luminance_fun = np.vectorize(luminance_fun)
    return v_luminance_fun(sky_type, patch_az, patch_el, sun_az, sun_el)

def print_n_max_values(vect, n):
    a = vect.copy()
    b = np.unique(a)
    c = np.sort(b)
    c = c[::-1]
    print(c[:n])

def plot_luminance_map(az, el, lum, az_s=None, el_s=None, luminance_or_radiance='radiance', polar=True, colormap=None):
    lum_min = np.min(lum)
    lum_max = np.max(lum)

    fig = plt.figure()
    if polar:
        ax = fig.add_subplot(111, polar=True)
        c = ax.pcolormesh(np.deg2rad(az), 90-el, lum, vmin=lum_min, vmax=lum_max, cmap=colormap)
    else:
        ax = fig.gca()

        c = ax.pcolormesh(az, el, lum, vmin=lum_min, vmax=lum_max, cmap=colormap)

        ax.set_xlabel('Azimuth [deg]')
        ax.set_ylabel('Zenith angle [deg]')

    cbar = fig.colorbar(c, ax=ax)
    if luminance_or_radiance == 'luminance':
        cbar_label = 'Luminance [cd/m²]'
    elif luminance_or_radiance == 'radiance':
        cbar_label = 'Radiance [W/(m²⋅sr)]'
    cbar.set_label(cbar_label)

    if (az_s is not None) and (el_s is not None):
        if polar:
            ax.plot(np.deg2rad(az_s), 90-el_s, 'ro', label='Sun position')
        else:
            ax.plot(az_s, el_s, 'ro', label='Sun position')
        ax.legend()

    if polar:
        # Set N at the top, E to the right
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)

    plt.show()

def plot_all_skies(polar=True, luminance_or_radiance='luminance', colormap='jet'):
    # sky = ReinhartSky().reinhart_patches
    # az = sky['az']
    # el = sky['el']
    az = np.arange(0, 360, step=5)  # [°]
    el = np.arange(0, 90, step=5)  # [°]

    az_meshgrid, el_meshgrid = np.meshgrid(az, el)

    el_s = 38.02  # [°]
    az_s = 147.67  # [°] 145° is south-east
    zenith_luminance = 4404  # cd/m²

    fig, axs = plt.subplots(3, 5,
                            figsize=(14, 8),
                            subplot_kw=dict(polar=polar))

    sky_types = np.arange(1, 16)
    for sky_type in sky_types:
        lum = compute_luminance(sky_type, az_meshgrid.flatten(), el_meshgrid.flatten(), az_s, el_s)

        lum_min = np.min(lum)
        lum_max = np.max(lum)

        ax_row = int(np.floor((sky_type-1)/5))
        ax_col = (sky_type-1) % 5
        print(f'{sky_type=}', f'{ax_row=}', f'{ax_col=}')

        ax = axs[ax_row, ax_col]
        if polar:
            c = ax.pcolormesh(np.deg2rad(az), 90-el, lum.reshape(az_meshgrid.shape), vmin=lum_min, vmax=lum_max, cmap=colormap)
        else:
            c = ax.pcolormesh(az, el, lum.reshape(az_meshgrid.shape), vmin=lum_min, vmax=lum_max, cmap=colormap)

            ax.set_xlabel('Azimuth [deg]')
            ax.set_ylabel('Zenith [deg]')

        ax.title.set_text(f'Sky type {sky_type}')

        # Set N at the top, E to the right
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)

        fig.colorbar(c, ax=ax)

        if (az_s is not None) and (el_s is not None):
            if polar:
                ax.plot(np.deg2rad(az_s), 90-el_s, 'ro', markeredgecolor='yellow', label='Sun position')
            else:
                ax.plot(az_s, 90-el_s, 'ro', markeredgecolor='yellow', label='Sun position')

    if luminance_or_radiance == 'luminance':
        fig_title = 'Luminance [cd/m²]'
    elif luminance_or_radiance == 'radiance':
        fig_title = 'Radiance [W/(m²⋅sr)]'
    fig.suptitle(fig_title + ' (azimuth-zenith)')

    plt.tight_layout()
    plt.show()

def plot_3D(sky, rel_lum):

    sky['patch_bound_el_low'] = sky['el'] - sky['d_el'] / 2
    sky['patch_bound_el_up'] = sky['el'] + sky['d_el'] / 2
    sky['patch_bound_az_low'] = sky['az'] - sky['d_az'] / 2
    sky['patch_bound_az_up'] = sky['az'] + sky['d_az'] / 2
    print(sky['patch_bound_el_up'].iloc[-1])
    # Fix elevation for top patch
    sky['patch_bound_el_up'].iloc[-1] = 90
    print(sky['patch_bound_el_up'].iloc[len(sky) - 1])

    # Vertical levels
    # in this case a single level slightly above the surface of a sphere
    RADIUS = 1
    levels = [RADIUS * 1.01]

    xx_bounds = np.concatenate([sky['patch_bound_az_low'].values,
                                [sky['patch_bound_az_up'].values[
                                     -1]]])  # az
    xx_bounds[-2:-1] += 180
    yy_bounds = np.concatenate([sky['patch_bound_el_low'].values,
                                [sky['patch_bound_el_up'].values[
                                     -1]]])  # el

    grid_scalar = pv.grid_from_sph_coords(xx_bounds, 90 - yy_bounds, levels)

    # And fill its cell arrays with the scalar data
    grid_scalar.cell_data["Luminance relative to zenith"] = np.array(
        rel_lum.reshape(az_meshgrid.shape)).swapaxes(-2, -1).ravel("C")

    # Prepare the Sun
    xyz_sun = sph_to_cart('deg', azimut=az_s, elev=el_s, zenith_angle=None,
                          dist=RADIUS)
    sun_mesh = pv.Sphere(radius=RADIUS / 20, center=xyz_sun)

    # Make a plot
    p = pv.Plotter()
    p.add_mesh(sun_mesh, color='yellow')
    p.add_mesh(grid_scalar, opacity=0.8, cmap="jet")
    p.show()

if __name__ == '__main__':

    standard_skies = pd.read_csv(os.path.join('..', 'INPUTS', 'CIE_standard_skies.csv'))

    # Example from the paper
    sky_type = 12

    sky_mesh = 'arange'  # {'arange', 'linspace', 'Reinhart'}

    if sky_mesh.lower() == 'reinhart':
        sky = ReinhartSky(MF=1).reinhart_patches
        az = sky['az'].values
        el = sky['el'].values
        # meshgrid_flag = False
        meshgrid_flag = True
        az_meshgrid, el_meshgrid = np.meshgrid(az, el)
    else:
        if sky_mesh.lower() == 'arange':
            step = 5
            az = np.arange(0, 360+step, step=step)  # [°]
            el = np.arange(0, 90+step, step=step)  # [°]
        elif sky_mesh.lower() == 'linspace':
            az = np.linspace(0, 360, num=145)  # [°]
            el = np.linspace(0, 90, num=145)  # [°]

        else:
            raise ValueError('Unrecognized sky discretization')

        meshgrid_flag = True
        az_meshgrid, el_meshgrid = np.meshgrid(az, el)

    el_s = 38.02  # [°]
    az_s = 147.67  # [°] 145° is south-east
    zenith_luminance = 4404  # cd/m²

    if meshgrid_flag:
        rel_lum = compute_luminance(sky_type, az_meshgrid.flatten(), el_meshgrid.flatten(), az_s, el_s).reshape(az_meshgrid.shape)
    else:
        # rel_lum = compute_luminance(sky_type, az, el, az_s, el_s)
        rel_lum = compute_luminance(sky_type, np.append(az, [360]), np.append(el, [90]), az_s, el_s)

    lum = rel_lum * zenith_luminance

    print_n_max_values(rel_lum, 3)

    # Plot with pcolormesh
    plot_luminance_map(az, el, rel_lum,
                       az_s, el_s,
                       luminance_or_radiance='radiance',
                       polar=True,
                       colormap='jet')

    # Plot all 15 standard skies in a (5, 3) subplots figure (takes a couple of minutes)
    # plot_all_skies()

if sky_mesh.lower() == 'reinhart':
    # Plot with PyVista (only for Reinhart scheme)
    plot_3D(sky, rel_lum)

