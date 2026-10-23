import numpy as np
from typing import Tuple


# ---- Grid maths ----
def compute_panel_grid_positions(num_blocks_x: int, num_blocks_y: int,
                                  panels_per_block_x: int, panels_per_block_y: int,
                                  block_spacing_x: float, block_spacing_y: float,
                                  panel_spacing_x: float, panel_spacing_y: float,
                                  base_height: float) -> (
        Tuple)[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute panel positions and their parent block centers.

    Parameters
    ----------
    num_blocks_x, num_blocks_y : int
        Number of blocks along X/Y.
    panels_per_block_x, panels_per_block_y : int
        Number of panels per block along X/Y.
    block_spacing_x, block_spacing_y : float
        Center-to-center spacing between blocks along X/Y.
    panel_spacing_x, panel_spacing_y : float
        Center-to-center spacing between panels within a block along X/Y.
    base_height : float
        Base Z elevation for all panels.

    Returns
    -------
    positions : numpy.ndarray, shape (N, 3)
        World coordinates (x, y, z) for each panel instance.
    block_centers : numpy.ndarray, shape (N, 3)
        The corresponding block center (x, y, z) per panel.
    grid_indices : numpy.ndarray, shape (N, 4)
        Integer indices ``[BX, BY, MX, MY]`` for block and module coordinates.

    Notes
    -----
    ``N = num_blocks_x * num_blocks_y * panels_per_block_x * panels_per_block_y``.
    """
    """Compute positions and block centers vectorially."""
    total_span_x = (num_blocks_x - 1) * block_spacing_x + (panels_per_block_x - 1) * panel_spacing_x
    total_span_y = (num_blocks_y - 1) * block_spacing_y + (panels_per_block_y - 1) * panel_spacing_y

    bx = np.arange(num_blocks_x)
    by = np.arange(num_blocks_y)
    mx = np.arange(panels_per_block_x)
    my = np.arange(panels_per_block_y)

    BX, BY, MX, MY = np.meshgrid(bx, by, mx, my, indexing='ij')
    grid_indices = np.column_stack([BX.ravel(), BY.ravel(), MX.ravel(), MY.ravel()])

    offset_x = (
        grid_indices[:, 0] * block_spacing_x + grid_indices[:, 2] * panel_spacing_x - total_span_x / 2.0
    )
    offset_y = (
        grid_indices[:, 1] * block_spacing_y + grid_indices[:, 3] * panel_spacing_y - total_span_y / 2.0
    )
    offset_z = np.full_like(offset_x, base_height, dtype=float)
    positions = np.column_stack([offset_x, offset_y, offset_z])

    block_center_x = (
        grid_indices[:, 0] * block_spacing_x + (
            panels_per_block_x - 1) * panel_spacing_x / 2.0 - total_span_x / 2.0
    )
    block_center_y = (
        grid_indices[:, 1] * block_spacing_y + (
            panels_per_block_y - 1) * panel_spacing_y / 2.0 - total_span_y / 2.0
    )
    block_center_z = np.full_like(block_center_x, base_height, dtype=float)
    block_centers = np.column_stack([block_center_x, block_center_y, block_center_z])

    return positions, block_centers, grid_indices

def compute_block_centers(num_blocks_x: int, num_blocks_y: int,
                          panels_per_block_x: int, panels_per_block_y: int,
                          block_spacing_x: float, block_spacing_y: float,
                          panel_spacing_x: float, panel_spacing_y: float,
                          base_height: float):
    total_span_x = (num_blocks_x - 1) * block_spacing_x + (
                panels_per_block_x - 1) * panel_spacing_x
    total_span_y = (num_blocks_y - 1) * block_spacing_y + (
                panels_per_block_y - 1) * panel_spacing_y
    bx = np.arange(num_blocks_x)
    by = np.arange(num_blocks_y)

    BX, BY = np.meshgrid(bx, by, indexing='ij')
    grid_indices = np.column_stack(
        [BX.ravel(), BY.ravel()])

    block_center_x = (
            grid_indices[:, 0] * block_spacing_x + (
            panels_per_block_x - 1) * panel_spacing_x / 2.0 - total_span_x / 2.0
    )
    block_center_y = (
            grid_indices[:, 1] * block_spacing_y + (
            panels_per_block_y - 1) * panel_spacing_y / 2.0 - total_span_y / 2.0
    )
    block_center_z = np.full_like(block_center_x, base_height, dtype=float)
    block_centers = np.column_stack(
        [block_center_x, block_center_y, block_center_z])

    return block_centers

def rotate_about_z(vec, angle):
    """
        Rotate a 3D vector or array of vectors about the Z axis by `azimuth` radians.
        vec: shape (3,) or (N,3)
        angle: scalar (degrees)

        Example usage:
        v = np.array([1.0, 0.0, 0.0])
        theta = 45  # degrees
        rotated_v = rotate_about_z(v, theta)
        print(rotated_v)  # [cos45, sin45, 0]
    """
    angle = np.deg2rad(angle)

    c = np.cos(angle)
    s = np.sin(angle)

    Rz = np.array([
        [c, -s, 0.0],
        [s, c, 0.0],
        [0.0, 0.0, 1.0]
    ])
    vec = np.asarray(vec)
    if vec.ndim == 1:
        return Rz @ vec
    else:
        # vec is (N,3): apply matrix to each row
        return (Rz @ vec.T).T


