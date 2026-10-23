#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
Author : Bouvry Arnaud (abouvry@uliege.be)
This file is part of the PASE software, and is distributed under the MIT license.

Sky subdivision after:
Bourgeois, Denis & Reinhart, C. & Ward, G. (2008). Standard daylight coefficient model for dynamic daylighting simulations. Building Research and Information - BUILDING RES INFORM. 36. 10.1080/09613210701446325.
Paper openly available on Researchgate: https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.researchgate.net/publication/228683789_Standard_daylight_coefficient_model_for_dynamic_daylighting_simulations&ved=2ahUKEwjp96OWi_iLAxWj8LsIHea6LUMQFnoECAoQAQ&usg=AOvVaw060IkWjmPP1qEXHvIA08C6
"""

import cProfile
import logging
import math
import numpy as np
import os
import pandas as pd
from pathlib import Path
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon

from pase.conversion_functions import sph_to_cart
from pase.paths import static_data_path

logger = logging.getLogger(__name__)
_CIE_STANDARD_SKIES = None


def subpatch_polygon(az_start_deg, az_stop_deg, el_start, el_end,
                     nsteps=10):
    """
    Create a polygon that represents a sky patch.
    Inputs:
    - az_start_deg: lower azimuth angle in degrees --> float
    - az_stop_deg: upper azimuth angle in degrees --> float
    - el_start: lower elevation angle in degrees --> float
    - el_end: upper elevation angle in degrees --> float
    - nsteps: number of point for the discretization in azimuth (default: 10) --> int
    """
    th1 = np.deg2rad(np.linspace(az_start_deg, az_stop_deg, nsteps))
    th2 = np.deg2rad(np.linspace(az_stop_deg, az_start_deg, nsteps))
    rho_inner = (90 - el_start) / 90
    rho_outer = (90 - el_end) / 90
    rho1 = np.ones_like(th1) * rho_inner
    rho2 = np.ones_like(th2) * rho_outer
    th = np.concatenate([th1, th2])
    rho = np.concatenate([rho1, rho2])
    x = rho * np.cos(th)
    y = rho * np.sin(th)
    coords = np.column_stack([x, y])
    return coords

def _load_standard_skies() -> pd.DataFrame:
    """
    Load the CIE standard skies parameter file and store the content in a
    global variable upon module import (saves time on pd.read_csv()).
    :return:
        _CIE_STANDARD_SKIES: dataframe
    """
    global _CIE_STANDARD_SKIES
    if _CIE_STANDARD_SKIES is None:
        _CIE_STANDARD_SKIES = pd.read_csv(
            static_data_path('CIE_standard_skies.csv'))
    return _CIE_STANDARD_SKIES

def fibonacci_half_sphere(samples=18):
    """
    Function computing a number of direction sampling a virtual upper half sphere with a center at 0,0,0

    Parameters:
        samples (int): Number of directions

    Returns:
       Directions (np.array): Matrix (samples x 3) providing the direction
    """
    phi = np.pi * (3. - np.sqrt(5.))
    i = np.linspace(0, samples - 1, num=samples)
    yp = (1 - i / float(samples - 1))
    radius = np.sqrt(1 - yp ** 2)
    theta = phi * i
    xp = np.cos(theta) * radius
    zp = np.sin(theta) * radius
    return np.column_stack([xp, zp, yp])


class ReinhartSky:
    """
    Reinhart discretization scheme used in diffuse irradiance computations.
    """
    def __init__(self, MF=1):
        # Validate MF and compute F
        self.MF, self.F = self.validate_MF_F(MF)

        # Compute alpha
        self.alpha = self.compute_alpha()

        # Build the base dataframe
        self.reinhart_sky, self.reinhart_num_total = self.get_reinhart()

        # Build the discrete sky patches
        self.reinhart_patches, self.patch_id = self.build_patches()

        # Add the top patch
        self.add_top_patch()

        # Compute surface areas of all patches
        self.compute_surface_areas()

        # Compute x, y, z coordinates of unit vectors pointing towards the sky patches
        self.get_patches_xyz()

        # Compute cos(zenith angle), used later in irradiance computations
        self.compute_cos_zenith()

    def validate_MF_F(self, mf) -> tuple[int, float]:
        """
        Validate Multiplying Factor (MF)
        and compute F: 2**F == MF <=> F = log2(MF)

          - MF must be a number (int or float equiv. to an int)
          - MF >= 1

        :param mf: Multiplying Factor
        :return:
            - int(mf_float) : the validated multiplying factor
            - f : F factor
        """
        try:
            mf_float = float(mf)
        except Exception as e:
            raise TypeError(f"MF must be a number. Received {mf!r}") from e

        if mf_float <= 0:
            raise ValueError("MF must be strictly positive.")

        if mf_float.is_integer() is False:
            raise ValueError("MF must be integer or integer-like")

        try:
            f = float(np.log2(mf_float))
        except (ValueError, OverflowError) as e:
            raise ValueError(f"MF invalid for log2: {mf!r}") from e

        return int(mf_float), f

    def compute_alpha(self) -> float:
        """
        Compute alpha, the differential altitude between sky patches.

        :return: alpha [°] (type: float)
        """
        return 90 / ((2 ** self.F * 7) + 1/2)  # [deg] Differential altitude

    def compute_num_rows(self) -> int:
        """
        Compute the total number of discretization rows of the sky hemisphere.
        It is computed as 7 * 2**F, 7 being the base number of rows in the
        Tregenza discretization scheme (which is the scientific basis of
        Reinhart).

        :return: num_rows (type: int)
        """

        return round(2**self.F * 7)

    def get_original_tregenza(self) -> pd.DataFrame:
        """
        Build a dataframe of the original Tregenza discretization scheme, for
        reference. Used to compare Reinhart sky against the reference from
        which it "inherits".
        :return:
            original_tregenza_segments: dataframe
        """
        original_tregenza_segments = pd.DataFrame()

        original_tregenza_segments['tregenza_row'] = np.arange(7)
        original_tregenza_segments['num_segments'] = np.array(
            [30, 30, 24, 24, 18, 12, 6])

        differential_altitude = 12  # [deg]
        original_tregenza_segments['altitude_deg'] = (np.arange(
            7) + 0.5) * differential_altitude

        original_tregenza_segments['diff_azimuth'] = np.array(
            [12, 12, 15, 15, 20, 30, 60])

        return original_tregenza_segments

    def get_corresp_tregenza145_row(self) -> np.ndarray | np.ndarray:
        """
        Get the correspondance between rows in:
         - the original Tregenza discretization scheme with 145 sky patches
         - the current Reinhart discretization scheme
         depending on the self.MF value (attribute of the class).

        :return:
            - reinhart_rows: row numbers in the Reinhart discretization scheme
            - tregenza_rows: row numbers in the base Tregenza discretization scheme
        """
        num_rows = self.compute_num_rows()
        reinhart_rows = np.arange(num_rows, dtype=int)
        tregenza_rows = np.floor(reinhart_rows/self.MF)

        return reinhart_rows, tregenza_rows

    def get_reinhart(self, _verbose=False):
        """
        Build a reinhart_sky dataframe that holds the discretization blueprint.

        :param _verbose: Print debug messages to console OUTPUT.
        :type _verbose: bool
        :return:
            - reinhart_sky: dataframe (cols: 'row', 'altitude_deg',
                'tregenza_row', 'num_tregenza_segments', 'num_segments')
            -  reinhart_num_total: total number of sky patches (int)
        """
        original_tregenza_segments = self.get_original_tregenza()

        reinhart_sky = pd.DataFrame()
        reinhart_rows, tregenza_rows = self.get_corresp_tregenza145_row()
        reinhart_sky['row'] = reinhart_rows
        reinhart_sky['altitude_deg'] = (reinhart_rows + 0.5) * self.alpha
        reinhart_sky['tregenza_row'] = tregenza_rows.astype(int)
        reinhart_sky = pd.merge(reinhart_sky, original_tregenza_segments[
            ['tregenza_row', 'num_segments']], on='tregenza_row', how='left')
        reinhart_sky = reinhart_sky.rename(
            columns={'num_segments': 'num_tregenza_segments'})

        reinhart_sky['num_segments'] = (reinhart_sky['num_tregenza_segments']
                                        * round(2 ** self.F))

        reinhart_num_total = round(4 ** self.F * 144) + 1

        return reinhart_sky, reinhart_num_total

    def build_patches(self) -> pd.DataFrame | int:
        """
        Build the reinhart_patches dataframe that contains all coordinates of the discretized sky patches.
        Columns are :
        - row : the row in the sky discretization scheme (row 0 is near the
                horizon, next rows go towards zenith)
        - patch_id : the ID of each patch (global id)
        - patch_id_in_row : the ID of each patch in that patch's row
                            (i.e. for each new row, patch_id_in_row resets to 0)
        - d_el : differential elevation of the patch [°]
        - d_az : differential azimuth of the patch [°]
        - el : elevation of the patch [°]
        - az : azimuth of the patch [°]
        - solid_angle_sr : solid angle of the patch in steradian [sr]

        :return:
            - reinhart_patches : dataframe with all patches except the top one
            - patch_id : patch ID of the last inserted patch of the dataframe
        """
        self.cols = ['row', 'patch_id', 'patch_id_in_row', 'd_el', 'd_az', 'el',
                     'az', 'solid_angle_sr']

        sky = (self.reinhart_sky[['row', 'num_segments']]
               .sort_values('row')
               .reset_index(drop=True))

        sky['d_az'] = 360.0 / sky['num_segments']
        sky['el'] = self.alpha * (sky['row'] + 0.5)

        patches = sky.loc[sky.index.repeat(sky['num_segments'])].copy()
        patches['patch_id_in_row'] = patches.groupby('row').cumcount()
        patches['patch_id'] = np.arange(len(patches), dtype=int)
        patches['d_el'] = self.alpha
        patches['az'] = patches['d_az'] * (patches['patch_id_in_row'] + 0.5)

        patches['solid_angle_sr'] = self.compute_solid_angle_from_elev_azim(
            patches['el'].to_numpy(),
            patches['d_az'].to_numpy()
        )

        reinhart_patches = patches[self.cols].reset_index(drop=True)
        patch_id = int(
            reinhart_patches['patch_id'].iloc[-1]) + 1 if len(
            reinhart_patches) else 0

        return reinhart_patches, patch_id

    def add_top_patch(self):
        """
        Dynamically adds the top patch to the self.reinhart_patches attribute
        dataframe.
        """
        top_row = max(self.reinhart_sky['row']) + 1
        top_patch_solid_angle = self.compute_solid_angle_cone(self.alpha / 2)
        top_patch = pd.DataFrame(
            [[top_row, self.patch_id, 0, self.alpha / 2, 360, 90, 0, top_patch_solid_angle]],
            columns=self.cols)
        self.reinhart_patches = pd.concat([self.reinhart_patches, top_patch],
                                     ignore_index=True)


    def compute_solid_angle_from_elev_azim(self, el, d_az):
        """
        Compute the solid angle (in steradians) based on elevation of the patch,
        the differential azimuth and differential elevation values.

        :param el:  elevation at the center of the patch [deg]
        :param d_az: differential azimuth of the patch [deg]
        :return:
            - solid_angle: solid angle of the patch [sr]
        """
        # convert to rad
        el = np.deg2rad(el)
        d_el = np.deg2rad(self.alpha)
        d_az = np.deg2rad(d_az)

        # compute the solid angle [sr]
        solid_angle = np.cos(el) * d_el * d_az

        return solid_angle

    def compute_solid_angle_cone(self, half_apex_angle) -> float:
        """
        Compute the solid angle at the top of the dome where it is a cone ;
        there is an exact analytical expression for this value.

        :param half_apex_angle: half apex angle of a cone [°]
        :return:
            - solid_angle: solid angle of a cone in steradian [sr]
        """

        half_apex_angle = np.deg2rad(half_apex_angle)
        solid_angle = 2 * np.pi * (1 - np.cos(half_apex_angle))

        return solid_angle

    def compute_surface_areas(self):
        """
        Add a new column 'Normalized surf area' to self.reinhart_patches
        dataframe, containing the normalized surface area of each patch.
        """

        self.reinhart_patches['Normalized surf area'] = self.reinhart_patches['solid_angle_sr'] / (
                2 * np.pi)

    def get_patches_xyz(self):
        """
        Compute xyz coords of the sky patches on the sky dome (i.e. upper
        half-sphere)
        """

        (self.reinhart_patches['x'],
         self.reinhart_patches['y'],
         self.reinhart_patches['z']) = sph_to_cart(units='deg',
                                                   azimut=self.reinhart_patches['az'],
                                                   elev=self.reinhart_patches['el'])

    def compute_cos_zenith(self):
        """
        Add a 'cos(z)' column to the instances' reinhart_patches dataframe,
        containing the cosine of zenith angle.
        """
        self.reinhart_patches['cos(z)'] = np.cos(np.deg2rad(90-self.reinhart_patches['el']))


    def scatter_3D(self, text_id=False):
        """
        Display a 3D scatter plot of the discretized sky. It is advised to only
        call this method for reasonable MF values (e.g. MF <= 8), lest it would
        take large amount of times.
        For larger MF values, also consider passing text_id as False or the
        display will be cluttered and unreadable.

        :param text_id: display the patch's ID in the 3D scatter plot.
        :type text_id: bool
        """
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        ax.scatter(self.reinhart_patches['x'],
                   self.reinhart_patches['y'],
                   self.reinhart_patches['z'], marker='.', c='k')

        if text_id:
            for idx in range(len(self.reinhart_patches)):
                patch = self.reinhart_patches.iloc[idx]
                ax.text(patch['x'], patch['y'], patch['z'],
                        s=f"{patch['patch_id']:.0f}")

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')

        title = f'{self.reinhart_num_total} patches (MF:{self.MF})'
        ax.set_title(title)
        ax.set_box_aspect([1.0, 1.0, 1/2])
        plt.show()

    def scatter_2D(self, text_id=False):
        """
        Display a 2D scatter plot of the discretized sky. It is advised to only
        call this method for reasonable MF values (e.g. MF <= 8), lest it would
        take large amount of times.
        For larger MF values, also consider passing text_id as False or the
        display will be cluttered and unreadable.

        :param text_id: display the patch's ID in the 2D scatter plot.
        :type text_id: bool
        """
        fig = plt.figure()
        ax = fig.add_subplot()

        ax.scatter(self.reinhart_patches['x'], self.reinhart_patches['y'],
                   c=self.reinhart_patches['patch_id'])

        if text_id:
            for idx in range(len(self.reinhart_patches)):
                patch = self.reinhart_patches.iloc[idx]
                ax.text(patch['x'], patch['y'], f"{patch['patch_id']:.0f}")

        ax.set_xlabel('X')
        ax.set_ylabel('Y')

        ax.set_aspect('equal', adjustable='box')

        plt.show()

    def patch_plot_value(self, values, cmap='viridis', clabel='', direction=True, show_colorbar=True):
        """
        Display a 2D colored plot off the values on the discretized sky. It is advised to only
        call this method for reasonable MF values
        Inputs:
        - values: flattened array of values to plot. The size should be equal to the number of sky patches --> np.array of size N
        - cmap: Colormap (default: viridis) --> str
        - clabel: Label of the colorbar (default: '') --> str
        - direction: Add the direction labels  (default: True) --> Boolean
        - show_colorbar: Show colorbar (default: True) --> Boolean
        """
        #value should be a flattened array of size N, N = number of patches
        az = np.asarray(-self.reinhart_patches['az']) +270
        el = np.asarray(self.reinhart_patches['el'])
        daz = np.asarray(self.reinhart_patches['d_az'])
        del_ = np.asarray(self.reinhart_patches['d_el'])
        values = np.asarray(values)

        N = len(values)

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_aspect("equal")
        ax.axis("off")

        cmap_obj = plt.get_cmap(cmap)
        vmin, vmax = np.nanmin(values), np.nanmax(values)
        norm = plt.Normalize(vmin, vmax)

        for k in range(N):

            azc = az[k]
            elc = el[k]

            AZ = np.array([azc - daz[k] / 2,
                           azc + daz[k] / 2])

            EL = np.array([elc - del_[k] / 2,
                           elc + del_[k] / 2])

            if el[k] !=90:
                coords = subpatch_polygon(AZ[0], AZ[1], EL[0], EL[1])
            else:
                print(el[k])
                theta = np.deg2rad(np.linspace(0, 360, 100))
                x = del_[k] * np.cos(theta)/90
                y = del_[k] * np.sin(theta)/90
                coords = np.column_stack([x, y])

            poly = Polygon(
                coords,
                closed=True,
                facecolor=cmap_obj(norm(values[k])),
                edgecolor="white",
                linewidth=0.2
            )
            ax.add_patch(poly)

        if direction:
            ax.text(0, 1.05, '0°', ha='center', fontsize=12)
            ax.text(0, -1.05, '180°', ha='center', fontsize=12)
            ax.text(1.05, 0, '90°', ha='center', fontsize=12)
            ax.text(-1.05, 0, '270°', ha='center', fontsize=12)

        if show_colorbar:
            m = plt.cm.ScalarMappable(norm=norm, cmap=cmap_obj)
            m.set_array(values)
            cb = fig.colorbar(m, ax=ax, shrink=0.8)
            cb.set_label(clabel)

        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)

        plt.tight_layout()
        return fig, ax

class CIEStandardSky:
    """
    Generate a standard radiance distribution among the 15 CIE General Skies.
    """

    def __init__(self, discrete_sky,
                 sun_az, sun_el,
                 sky_type=5):

        self.sky = discrete_sky

        self.az = discrete_sky['az'].values
        self.el = discrete_sky['el'].values

        self.az_s = sun_az  # [°] Sun azimuth (145° is south-east)
        self.el_s = sun_el  # [°]  Sun elevation

        self.sky_type = int(sky_type)

        # Load the cached table (see top of this module)
        self.standard_skies = _load_standard_skies()

        # cache sky params dict (all types) to avoid repeated DataFrame lookups
        # do this once per instance (cheap)
        types = self.standard_skies['Type'].values
        self._sky_params_by_type = {
            int(row['Type']): (row['a'], row['b'], row['c'], row['d'], row['e'])
            for _, row in self.standard_skies.iterrows()
        }
        # store current params for quick use later
        self._current_sky_params = self._sky_params_by_type[self.sky_type]

        # compute and cache phi_zenith and indicatrix_zenith per sky_type
        # (they're scalars and reused)
        a, b, c, d, e = self._current_sky_params
        self._phi_zenith = self.compute_gradation(a, b, 0.0)
        self._indicatrix_zenith = self.scattering_indicatrix_fun(c, d, e,
                                                                 np.deg2rad(
                                                                     90.0 - self.el_s))

        self.rel_radiance_distribution = self.compute_rel_radiance()

    def compute_sph_angular_dist(self, Z, Z_s, az, az_s):
        """

        :param Z: Sky patch zenith angle [deg]
        :param Z: float
        :param Z_s: Solar zenith angle [deg]
        :param Z_s: float
        :param az: Sky patch azimuth angle from north [deg]
        :param az: float
        :param az_s: Solar azimuth angle from north [deg]
        :param az_s: float
        :return: chi = Spherical angular distance [rad]
        """

        # Convert all angles from degrees to radians
        Z = np.deg2rad(Z)
        Z_s = np.deg2rad(Z_s)
        az = np.deg2rad(az)
        az_s = np.deg2rad(az_s)

        # Absolute difference in azimuth angles
        Az = np.abs(az - az_s)

        # Angular distance chi
        chi = np.arccos(
            np.cos(Z_s) * np.cos(Z) + np.sin(Z_s) * np.sin(Z) * np.cos(Az))

        return chi

    def compute_gradation(self, a, b, Z):
        """
        Vectorizes and computes the gradation function

        :param a: Horizon-zenith gradient (gradation parameter) [-]
        :type a: float
        :param b: Gradient intensity (gradation parameter) [-]
        :type b: float
        :param Z: Zenith angle [deg]
        :type Z: Nx1 array of float
        :return: gradation function [-], same shape as Z
        """

        Z_rad = np.deg2rad(Z)
        # mask for Z == pi/2 (90 deg), use np.isclose for numerical safety
        mask = np.isclose(Z_rad, np.pi / 2)
        # compute 1 + a * exp(b / cos(Z)) safely (cos may be zero but masked)
        cosZ = np.cos(Z_rad)
        # avoid division by zero by using where; for masked entries result will be set to 1 afterwards
        with np.errstate(divide='ignore', invalid='ignore'):
            grad = 1.0 + a * np.exp(b / cosZ)
        # set masked entries to 1
        if np.any(mask):
            grad = np.where(mask, 1.0, grad)
        return grad

    def scattering_indicatrix_fun(self, c, d, e, x):
        """
        Compute the scattering indicatrix value.

        :param c: Circumsolar intensity (scattering parameter) [-]
        :type c: float
        :param d: Circumsolar radius (scattering parameter) [-]
        :type d: float
        :param e: Backscattering effect (scattering parameter) [-]
        :type e: float
        :param x: angle (spherical angular distance or zenith, i.e. 0) [rad]
        :type x: array of float or float
        :return: Scattering indicatrix value [-], same shape as x
        """
        return 1 + c * (np.exp(d * x) - np.exp(d * np.pi / 2)) + e * (
            np.cos(x)) ** 2

    def get_sky_params(self, standard_sky=None, sky_type=None):
        """

        :param standard_sky: Dataframe of length 1 with standard sky information
        :return a: Horizon-zenith gradient (gradation parameter) [-]
        :return b: Gradient intensity (gradation parameter) [-]
        :return c: Circumsolar intensity (scattering parameter) [-]
        :return d: Circumsolar radius (scattering parameter) [-]
        :return e: Backscattering effect (scattering parameter) [-]
        """

        # prefer sky_type (int) if provided
        if sky_type is not None:
            return self._sky_params_by_type[int(sky_type)]

        if standard_sky is not None:
            # keep for backward compatibility but avoid DataFrame ops if possible
            t = int(standard_sky['Type'].values[0])
            return self._sky_params_by_type[t]

        # if sky_type is None and standard_sky is None:
        return self._current_sky_params

    def relative_radiance_fun(self, az=None, el=None):
        """

        :return: relative quantity (radiance or luminance) with respect to
                 value at the zenith
        """

        # Sky model parameters
        a, b, c, d, e = self._current_sky_params

        # Elevation to zenith (Sun)
        Z_s = 90.0 - float(self.el_s)  # scalar [deg]

        # determine Z (zenith angle) and az arrays, allow scalar or array input
        if el is None:
            Z = 90.0 - np.asarray(self.el)
        else:
            Z = 90.0 - np.asarray(el)

        if az is None:
            az_arr = np.asarray(self.az)
        else:
            az_arr = np.asarray(az)

        # broadcast Z and az to common shape
        Z, az_arr = np.broadcast_arrays(Z, az_arr)

        # spherical angular distance (returns array)
        chi = self.compute_sph_angular_dist(Z, Z_s, az_arr, self.az_s)

        # gradation: phi and phi_zenith (phi_zenith is scalar)
        phi = self.compute_gradation(a, b, Z)

        # scattering indicatrix: array and scalar
        indicatrix = self.scattering_indicatrix_fun(c, d, e, chi)

        rel_quantity = (phi * indicatrix) / (self._phi_zenith * self._indicatrix_zenith)
        return rel_quantity

    def compute_rel_radiance(self, az=None, el=None):
        if self.sky_type == 5:
            return np.ones_like(self.az)
        rel = self.relative_radiance_fun(az=az, el=el)
        return rel


if __name__ == '__main__':

    profile_flag = False

    if profile_flag:
        MFs = [1, 2]
        for MF in MFs:
            profile_output = os.path.join('..', '..', 'OUTPUTS', 'profiling', f'cprofile_output_sky_model_MF{MF}.prof')
            cProfile.run(f"ReinhartSky(MF={MF})", profile_output, sort='tottime')
    else:
        MF = 1

        sky = ReinhartSky(MF=MF)
        if MF == 1:
            text_id = True
        else:
            text_id = False

        if MF < 8:
            sky.scatter_2D(text_id=text_id)
            sky.scatter_3D(text_id=text_id)

    sky.reinhart_patches['Relative radiance distribution'] = CIEStandardSky(sky.reinhart_patches,
                               sun_az=147.67, sun_el=38.02, sky_type=15).rel_radiance_distribution

    DHI = 100  # [W/m²] arbitrary value for example's sake
    integral_rel_sky_radiance = (sky.reinhart_patches['Relative radiance distribution']
                                 * sky.reinhart_patches['solid_angle_sr']).sum()
    zenith_radiance = DHI/integral_rel_sky_radiance
    sky.reinhart_patches['Absolute radiance distribution'] = (sky.reinhart_patches['Relative radiance distribution']
                                                              * zenith_radiance)

