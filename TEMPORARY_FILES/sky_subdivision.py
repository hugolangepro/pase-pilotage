"""
Sky subdivision after:
Bourgeois, Denis & Reinhart, C. & Ward, G. (2008). Standard daylight coefficient model for dynamic daylighting simulations. Building Research and Information - BUILDING RES INFORM. 36. 10.1080/09613210701446325.
Paper openly available on Researchgate: https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.researchgate.net/publication/228683789_Standard_daylight_coefficient_model_for_dynamic_daylighting_simulations&ved=2ahUKEwjp96OWi_iLAxWj8LsIHea6LUMQFnoECAoQAQ&usg=AOvVaw060IkWjmPP1qEXHvIA08C6

"""

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

from pase.conversion_functions import sph_to_cart

VERBOSE = False
compare_fhs = False

def get_original_tregenza():
    original_tregenza_segments = pd.DataFrame()

    original_tregenza_segments['tregenza_row'] = np.arange(7)
    original_tregenza_segments['num_segments'] = np.array([30, 30, 24, 24, 18, 12, 6])

    differential_altitude = 12  # [deg]
    original_tregenza_segments['altitude_deg'] = (np.arange(7) + 0.5) * differential_altitude

    original_tregenza_segments['diff_azimuth'] = np.array([12, 12, 15, 15, 20, 30, 60])

    return original_tregenza_segments

def get_corresp_tregenza145_row(F, MF):
    alpha = 90 / ((2 ** F * 7) + 1 / 2)  # [deg] Differential altitude

    num_rows = 2**F * 7

    reinhart_rows = np.arange(num_rows, dtype=int)
    tregenza_rows = np.floor(reinhart_rows/MF)

    return reinhart_rows, tregenza_rows, num_rows, alpha

def get_reinhart(MF, _verbose=False):
    F = np.log2(MF)

    original_tregenza_segments = get_original_tregenza()

    reinhart_sky = pd.DataFrame()
    reinhart_rows, tregenza_rows, num_rows, alpha = get_corresp_tregenza145_row(F, MF)
    reinhart_sky['row'] = reinhart_rows
    reinhart_sky['altitude_deg'] = (reinhart_rows + 0.5) * alpha
    reinhart_sky['tregenza_row'] = tregenza_rows.astype(int)
    reinhart_sky = pd.merge(reinhart_sky, original_tregenza_segments[['tregenza_row', 'num_segments']], on='tregenza_row', how='left')
    reinhart_sky = reinhart_sky.rename(columns={'num_segments': 'num_tregenza_segments'})

    reinhart_sky['num_segments'] = reinhart_sky['num_tregenza_segments'] * round(2**F)

    reinhart_num_total = round(4**F * 144) + 1
    Ivanova_num_total = 144 * MF**2 + 1
    num_segments_checksum = reinhart_sky['num_segments'].sum() + 1

    # assert reinhart_num_total == num_segments_checksum
    diff1 = reinhart_num_total - Ivanova_num_total
    diff = num_segments_checksum - reinhart_num_total

    if _verbose or VERBOSE or diff or diff1:
        print('\n', 5*'#', f'{MF=} ; {F=}', 5*'#')
        if not (diff) and not (diff1):
            print('Passed')

    if diff1:
        print('Mismatch in theoretical number of patches !!')
        print(f'Calc Reinhart = {reinhart_num_total}')
        print(f'Calc Ivanova et Gueymard = {Ivanova_num_total}')

    if diff != 0:
        print('Mismatch in implementation !!!')
    if diff > 0:
        print(f'{diff} extra patch(es)')
    elif diff < 0:
        print(f'{diff} missing patch(es)')

    return reinhart_sky, reinhart_num_total, num_rows, alpha

def compute_solid_angle_from_elev_azim(el, d_el, d_az):
    """

    Args:
        el: elevation at the center of the patch [deg]
        d_el: differential elevation of the patch [deg]
        d_az: differential azimuth of the patch [deg]

    Returns:
        solid_angle: solid angle of the patch [sr]
    """
    # inputs in deg, shape 2x1

    # convert to rad
    el = np.deg2rad(el)
    d_el = np.deg2rad(d_el)
    d_az = np.deg2rad(d_az)

    # compute the solid angle [sr]
    solid_angle = np.cos(el) * d_el * d_az

    # print(dw)

    return solid_angle

def compute_solid_angle_cone(half_apex_angle):
    """

    Args:
        half_apex_angle: in degrees

    Returns:
        solid angle of a cone
    """
    half_apex_angle = np.deg2rad(half_apex_angle)
    solid_angle = 2 * np.pi * (1 - np.cos(half_apex_angle))

    return solid_angle

def test_MFs():
    MFs = np.arange(1, 33)
    for MF in MFs:
        _, _, _, _ = get_reinhart(MF=MF, _verbose=False)
    return

test_MFs()

# F = 1  # F scale factor from Bourgeois et al.

# Multiplying Factor found everywhere else in the literature (most notably in Radiance)
MF = 1
reinhart_sky, reinhart_num_total, num_rows, alpha = get_reinhart(MF=MF)

# alpha = 11.25  # [deg] From CIE sky web app but I don't understand it

reinhart_patches = pd.DataFrame()
patch_id = 0
cols = ['row', 'patch_id', 'patch_id_in_row', 'd_el', 'd_az', 'el', 'az', 'solid_angle_sr']
for row in reinhart_sky['row']:
    # print(f'{row=}')
    d_az = 360/reinhart_sky[reinhart_sky['row']==row]['num_segments'].values[0]
    el = alpha * (row + 1/2)  # [deg]

    for segment in range(reinhart_sky['num_segments'].iloc[row]):
        # print(f'{segment=}')
        az = d_az * (segment + 1/2)  # [deg]
        solid_angle = compute_solid_angle_from_elev_azim(el, alpha, d_az)

        df = pd.DataFrame([[row, patch_id, segment, alpha, d_az, el, az, solid_angle]], columns=cols)

        reinhart_patches = pd.concat([reinhart_patches, df], ignore_index=True)

        patch_id += 1

# Add the top patch
top_row = max(reinhart_sky['row']) + 1
top_patch_solid_angle = compute_solid_angle_cone(alpha/2)
top_patch = pd.DataFrame([[top_row, patch_id, 0, alpha/2, 360, 90, 0, top_patch_solid_angle]], columns=cols)
reinhart_patches = pd.concat([reinhart_patches, top_patch], ignore_index=True)

# Compute surf area of each patch
reinhart_patches['surf area'] = reinhart_patches['solid_angle_sr']/(2*np.pi)
sum_surf_areas = reinhart_patches['surf area'].sum()
print(f'Sum of surface areas = {sum_surf_areas:.4g}')

# Check that the sum of solid angles is correct
sum_solid_angles = reinhart_patches['solid_angle_sr'].sum()
sum_solid_angles_div_pi = sum_solid_angles/np.pi
print(f'Sum of solid angles = {sum_solid_angles_div_pi:.4g} * pi')

# Compute xyz coords on a unit sphere (actually half sphere since it's the sky dome)
reinhart_patches['x'], reinhart_patches['y'], reinhart_patches['z'] = sph_to_cart(units='deg',
                                                                                  azimut=reinhart_patches['az'],
                                                                                  elev=reinhart_patches['el'])

if compare_fhs:
    # Compare with Fibonacci half sphere
    def fibonacci_half_sphere(samples=18):
        """
        Function computing a number of direction sampling a virtual upper half
        sphere with a center at 0,0,0

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


    def cart_to_sph(x, y, z):
        r = np.sqrt(x ** 2 + y ** 2 + z ** 2)

        if z > 0:
            elev = np.arctan((x ** 2 + y ** 2) / z)
        elif z < 0:
            raise NotImplementedError('Not done yet')
        elif (z == 0) and (np.sqrt(x ** 2 + y ** 2) != 0):
            elev = np.pi / 2

        elev = np.pi / 2 - elev

        if x > 0:
            az = np.arctan(y / x)
        elif (x < 0) and (y >= 0):
            az = np.arctan(y / x) + np.pi
        elif (x < 0) and (y < 0):
            az = np.arctan(y / x) - np.pi
        elif (x == 0) and (y > 0):
            az = np.pi / 2
        elif (x == 0) and (y < 0):
            az = -np.pi / 2
        elif (x == 0) and (y == 0):
            az = np.nan

        return az, elev


    N = reinhart_num_total
    fhs = fibonacci_half_sphere(N)

    azimuts = []
    elevations = []
    for xyz in fhs:
        x, y, z = xyz
        az, elev = cart_to_sph(x, y, z)
        azimuts.append(az)
        elevations.append(elev)

    azimuts[0] = 0

    #  Plot vs Fibonacci half sphere
    fig = plt.figure()

    plt.plot(reinhart_patches['az'], reinhart_patches['el'], 'x', label='Reinhart')
    plt.plot(np.degrees(azimuts)+180, np.degrees(elevations), '+', label='Fibonacci hs')

    plt.xlabel('Azimuth [°]')
    plt.ylabel('Elevation [°]')

    # loc supported values are 'best', 'upper right', 'upper left', 'lower left', 'lower right', 'right', 'center left', 'center right', 'lower center', 'upper center', 'center'
    fig.legend(loc='outside upper right')

    title = f'{reinhart_num_total} patches (MF:{MF})'
    plt.title(title)

    plt.show()

# 3D plot
fig = plt.figure()
ax = fig.add_subplot(projection='3d')

ax.scatter(reinhart_patches['x'],
           reinhart_patches['y'],
           reinhart_patches['z'], marker='.', c='k')

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

title = f'{reinhart_num_total} patches (MF:{MF})'
ax.set_title(title)
ax.set_box_aspect([1.0, 1.0, 1/2])
plt.show()

# 2D plot with ID
fig = plt.figure()
ax = fig.add_subplot()

ax.scatter(reinhart_patches['x'], reinhart_patches['y'], c=reinhart_patches['patch_id'])

for idx in range(len(reinhart_patches)):
    patch = reinhart_patches.iloc[idx]
    # ax.plot(patch['x'], patch['y'], '.')
    ax.text(patch['x'], patch['y'], f"{patch['patch_id']:.0f}")

ax.set_xlabel('X')
ax.set_ylabel('Y')

ax.set_aspect('equal', adjustable='box')

plt.show()

# 3D plot with ID
fig = plt.figure()
ax = fig.add_subplot(projection='3d')

ax.scatter(reinhart_patches['x'],
           reinhart_patches['y'],
           reinhart_patches['z'], marker='.', c=reinhart_patches['patch_id'])

for idx in range(len(reinhart_patches)):
    patch = reinhart_patches.iloc[idx]
    # ax.plot(patch['x'], patch['y'], '.')
    ax.text(patch['x'], patch['y'], patch['z'], s=f"{patch['patch_id']:.0f}")

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

title = f'{reinhart_num_total} patches (MF:{MF})'
ax.set_title(title)
ax.set_box_aspect([1.0, 1.0, 1/2])
plt.show()
