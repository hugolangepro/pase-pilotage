import pyvista as pv
import numpy as np
import os

length_m     = 1.0
side_m       = 0.05
n_bars       = 3
group_height = 1.0
clearance    = 0.5
rotation_x   = -45
support_y    = +side_m
n_groups     = 3
group_offset = 1.0
ground_z     = 0.0

spacing = group_height / (n_bars - 1) if n_bars > 1 else 0.0
theta = np.radians(rotation_x)

def make_group(x_offset=0.0, end=False):
    z_positions = [clearance + i * spacing for i in range(n_bars)]
    bars = [pv.Cube(center=(x_offset + length_m/2, 0, z),
                    x_length=length_m, y_length=side_m, z_length=side_m)
            for z in z_positions]
    assembly = bars[0]
    for b in bars[1:]:
        assembly = assembly.merge(b)

    z_min = min(z_positions) - side_m
    z_max = max(z_positions) + side_m
    support_height = z_max - z_min
    support_center_z = (z_max + z_min) / 2.0

    support_x_a = x_offset + side_m/2
    support_a = pv.Cube(center=(support_x_a, support_y, support_center_z),
                        x_length=side_m, y_length=side_m, z_length=support_height)
    assembly = assembly.merge(support_a)

    supports = [(support_x_a, support_y, support_center_z)]
    if end:
        support_x_b = x_offset + length_m - side_m/2
        support_b = pv.Cube(center=(support_x_b, support_y, support_center_z),
                            x_length=side_m, y_length=side_m, z_length=support_height)
        assembly = assembly.merge(support_b)
        supports.append((support_x_b, support_y, support_center_z))

    return assembly, supports

def rot_x_about(pivot, angle_rad, p):
    x0,y0,z0 = pivot
    x,y,z = p
    cy, sy = np.cos(angle_rad), np.sin(angle_rad)
    dy, dz = y - y0, z - z0
    y2 = y0 + dy*cy - dz*sy
    z2 = z0 + dy*sy + dz*cy
    return (x, y2, z2)

groups = [make_group(i * group_offset, end=(i == n_groups - 1)) for i in range(n_groups)]

upper_all = groups[0][0]
for g in groups[1:]:
    upper_all = upper_all.merge(g[0])

center_x = ((n_groups - 1) * group_offset + length_m) / 2.0
pivot = (center_x, 0.0, clearance + group_height/2.0)
upper_rot = upper_all.rotate_x(rotation_x, point=pivot, inplace=False)

feet = None
for _, supports in groups:
    for (sx, sy, sz) in supports:
        top = rot_x_about(pivot, theta, (sx, sy, sz))
        _, ty, tz = top
        fh = max(tz - ground_z, side_m)
        fc = pv.Cube(center=(sx, ty, ground_z + fh/2.0),
                     x_length=side_m, y_length=side_m, z_length=fh)
        feet = fc if feet is None else feet.merge(fc)

ground = pv.Plane(center=(0,0,ground_z), direction=(0,0,1), i_size=10.0, j_size=10.0)

if os.environ.get("CI")!="true":
    pl = pv.Plotter()
    pl.add_mesh(ground, color="#d0d0d0", lighting=True)
    pl.add_mesh(upper_rot, color="lightgrey", lighting=True)
    pl.add_mesh(feet, color="lightgrey", lighting=True)
    pl.add_axes()
    pl.camera_position = "xz"
    pl.show()
