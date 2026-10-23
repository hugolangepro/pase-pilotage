import math
import numpy as np
import pytest
import pyvista as pv

from pase.ENVIRONMENT.mesh import Mesh


def create_panel_box(width=2.0, height=1.0, thickness=0.1):
    half_w = width / 2
    half_h = height / 2
    half_t = thickness / 2
    return pv.Box(bounds=(-half_w, half_w, -half_h, half_h, -half_t, half_t))


def test_import_from_pvconfiguration_top_and_bottom():
    """Mesh a box-like PV panel requesting both top and bottom faces."""
    panel = create_panel_box()
    mesh = Mesh()

    mesh_ids = mesh.import_from_pvconfiguration([panel], include_top=True, include_bottom=True, density=0)

    assert mesh_ids == [0]
    polydata = mesh.meshes[mesh_ids[0]]
    # Full mesh retained when both orientations are requested (six faces, two triangles each)
    assert polydata.n_cells == 12
    normals = polydata.cell_data["Normals"]
    assert np.any(normals[:, 2] > 0)
    assert np.any(normals[:, 2] < 0)


def test_import_from_pvconfiguration_only_top():
    """Mesh a PV-style box while keeping only the upward-facing surface."""
    panel = create_panel_box()
    mesh = Mesh()

    mesh_ids = mesh.import_from_pvconfiguration([panel], include_top=True, include_bottom=False, density=0)

    polydata = mesh.meshes[mesh_ids[0]]
    assert polydata.n_cells == 2
    normals = polydata.cell_data["Normals"]
    assert np.all(normals[:, 2] > 0)


def test_import_from_pvconfiguration_density_refines_mesh():
    """Ensure density subdivides PV faces and yields predictable triangle counts."""
    panel = create_panel_box()
    mesh = Mesh()

    coarse_mesh_id = mesh.import_from_pvconfiguration(
        [panel], include_top=True, include_bottom=False, density=0
    )[0]
    base_cell_count = mesh.meshes[coarse_mesh_id].n_cells

    assert base_cell_count == 2

    def expected_cells(density: float) -> int:
        if density <= 0:
            return base_cell_count

        width = 2.0
        height = 1.0
        average_dimension = (width + height) / 2.0
        target_divisions = math.ceil(average_dimension / max(density, 1e-6))
        subdivisions = max(0, target_divisions - 1)
        return int(base_cell_count * (4 ** subdivisions))

    for density in (0, 0.5, 0.25):
        mesh_id = mesh.import_from_pvconfiguration(
            [panel], include_top=True, include_bottom=False, density=density
        )[0]
        assert mesh.meshes[mesh_id].n_cells == expected_cells(density)


def test_add_rectangular_surface_and_get_mesh_data():
    """Generate a rectangular surface mesh and verify centers, normals, and areas."""
    mesh = Mesh()
    mesh_id = mesh.add_rectangular_surface(width=2.0, height=1.0, density=0.5, center=(0, 0, 0), normal=(0, 0, 1))

    data = mesh.get_mesh_data(mesh_id)
    # width divisions=4, height divisions=2 -> 8 quads -> 16 triangles
    assert data["centers"].shape == (16, 3)
    assert data["normals"].shape == (16, 3)
    assert np.allclose(data["normals"], np.array([0, 0, 1]))
    assert data["areas"].shape == (16,)


def test_add_rectangular_surface_with_rectangular_faces():
    """Build a grid using rectangle faces and ensure areas and counts match."""
    mesh = Mesh()
    mesh_id = mesh.add_rectangular_surface(
        width=2.0,
        height=1.0,
        density=0.5,
        center=(0, 0, 0),
        normal=(0, 0, 1),
        face_type="rectangle",
    )

    data = mesh.get_mesh_data(mesh_id)
    # width divisions=4, height divisions=2 -> 8 rectangles
    assert data["centers"].shape == (8, 3)
    assert data["areas"].shape == (8,)
    # Each rectangle covers 0.5 by 0.5 units
    assert np.allclose(data["areas"], 0.25)


def test_mesh_can_mix_triangular_and_rectangular_surfaces():
    """Ensure a single Mesh instance can hold both triangles and rectangles."""
    mesh = Mesh()
    triangle_id = mesh.add_rectangular_surface(width=1.0, height=1.0, density=0.5, face_type="triangle")
    rectangle_id = mesh.add_rectangular_surface(width=1.0, height=1.0, density=0.5, face_type="rectangle")

    triangle_mesh = mesh.meshes[triangle_id]
    rectangle_mesh = mesh.meshes[rectangle_id]

    assert triangle_mesh.n_cells == 8  # 4 quads -> 8 triangles
    assert rectangle_mesh.n_cells == 4  # 4 rectangles


def test_add_triangular_probe_area_matches():
    """Ensure triangular probe creation preserves the requested surface area."""
    mesh = Mesh()
    target_area = 2.0
    mesh_id = mesh.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=target_area)

    data = mesh.get_mesh_data(mesh_id)
    assert data["centers"].shape == (1, 3)
    assert math.isclose(float(data["areas"][0]), target_area, rel_tol=1e-6)


def test_add_polydata_and_resolve_by_name():
    """Register custom polydata and retrieve it via its assigned name."""
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    faces = np.hstack([[3, 0, 1, 2]])
    polydata = pv.PolyData(points, faces=faces)

    mesh = Mesh()
    mesh_id = mesh.add_polydata(polydata, name="custom_face")

    assert mesh_id == 0
    data = mesh.get_mesh_data("custom_face")
    assert data["centers"].shape == (1, 3)
    assert data["areas"].shape == (1,)


def test_compute_homogeneity_returns_zero_for_single_cell():
    """Confirm homogeneity metric returns zero when only one cell is present."""
    mesh = Mesh()
    mesh.add_triangular_probe(position=(0, 0, 0), normal=(0, 0, 1), area=1.0)

    assert mesh.compute_homogeneity(0) == 0.0


class TestSetInterestZoneOrientation:
    """Tests for Mesh.set_interest_zone_orientation()."""

    def test_default_mode_returns_zero(self):
        """'default' mode must yield azimut=0 regardless of AV config."""
        mesh = Mesh()
        result = mesh.set_interest_zone_orientation(
            {"InterestZoneOrientationMode": "default"},
            {"CentralAzimut": 45.0},
        )
        assert result == 0.0
        assert mesh.default_azimut == 0.0

    def test_auto_mode_negates_central_azimut(self):
        """'auto' mode must return the negation of AV_1['CentralAzimut']."""
        mesh = Mesh()
        result = mesh.set_interest_zone_orientation(
            {"InterestZoneOrientationMode": "auto"},
            {"CentralAzimut": 30.0},
        )
        assert result == -30.0
        assert mesh.default_azimut == -30.0

    def test_custom_mode_negates_custom_angle(self):
        """'custom' mode must return the negation of InterestZoneCustomAngle."""
        mesh = Mesh()
        result = mesh.set_interest_zone_orientation(
            {"InterestZoneOrientationMode": "custom", "InterestZoneCustomAngle": 120.0},
            {"CentralAzimut": 0.0},
        )
        assert result == -120.0
        assert mesh.default_azimut == -120.0

    def test_mode_is_case_insensitive(self):
        """Mode string comparison must be case-insensitive."""
        mesh = Mesh()
        result = mesh.set_interest_zone_orientation(
            {"InterestZoneOrientationMode": "AUTO"},
            {"CentralAzimut": 15.0},
        )
        assert result == -15.0

    def test_unknown_mode_raises_value_error(self):
        """An unrecognised mode must raise ValueError."""
        mesh = Mesh()
        with pytest.raises(ValueError, match="Unknown InterestZoneOrientationMode"):
            mesh.set_interest_zone_orientation(
                {"InterestZoneOrientationMode": "diagonal"},
                {"CentralAzimut": 0.0},
            )
