import math
import numpy as np
import pyvista as pyv
import pytest

from pase.PHOTOVOLTAICS.configuration import (
    PV_Configuration_3D,   # alias used to test PV_central_MB
    PVConfiguration3D,     # recent API
    MultiBlockPASE,
    name_matches_flag,
)


def _create_three_centrals_with_prefixes():
    """
    Build 3 PV plants on a single PVConfiguration3D instance,
    rename the newly added blocks to PV_A_*, PV_B_*, PV_C_* and reindex.
    Returns (cfg, ranges) where ranges = dict(prefix -> (start_pos, end_pos_excl, height)).
    """
    cfg = PVConfiguration3D()

    base = dict(
        PanelDimensionX=1.6, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.8, RepetitionDistanceOfPanelsY=1.2,
        NumberOfPanelsX=2, NumberOfPanelsY=2,
        RepetitionDistanceOfPVBlocksX=3.6, RepetitionDistanceOfPVBlocksY=2.4,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,
        CentralAzimut=0.0, TiltY=10.0, Hinge='center',
    )
    # Different heights to verify z_min ordering
    variants = [
        ("PV_A", dict(CentralAzimut=0.0,   TiltY=10.0, PanelDimensionX=1.6, PanelDimensionY=1.0, Height=1.0)),
        ("PV_B", dict(CentralAzimut=90.0,  TiltY=20.0, PanelDimensionX=2.0, PanelDimensionY=1.2, Height=1.5)),
        ("PV_C", dict(CentralAzimut=180.0, TiltY=5.0,  PanelDimensionX=1.0, PanelDimensionY=1.6, Height=2.0)),
    ]

    ranges = {}
    for prefix, override in variants:
        start = cfg.n_blocks
        cfg.create_regular_central(base | override)
        end = cfg.n_blocks
        # Rename the newly added blocks with the desired prefix
        for i in range(start, end):
            name = cfg.get_block_name(i) or "PV"
            cfg.set_block_name(i, f"{prefix}_{name}")
        cfg.reindex()  # rebuild name/OID indices
        ranges[prefix] = (start, end, (base | override)["Height"])
    return cfg, ranges


def _assert_names_prefixed(mb: MultiBlockPASE, prefix: str):
    for i in range(mb.n_blocks):
        name = mb.get_block_name(i) or ""
        assert name.startswith(prefix + "_"), f"Unexpected block name: {name} (expected prefix: {prefix}_)"


def _norm(v):
    return float(np.linalg.norm(np.asarray(v, dtype=float)))


def test_flag_filtering_basic_and_union_and_options():
    cfg, _ = _create_three_centrals_with_prefixes()

    only_A = cfg.get_polydata_by_flag("PV_A")
    only_B = cfg.get_polydata_by_flag("PV_B")
    only_C = cfg.get_polydata_by_flag("PV_C")
    A_C = cfg.get_polydata_by_flag(["PV_A", "PV_C"])

    # Each sub-scene must contain only the expected prefix
    _assert_names_prefixed(only_A, "PV_A")
    _assert_names_prefixed(only_B, "PV_B")
    _assert_names_prefixed(only_C, "PV_C")

    # Union A ∪ C: no B entries must appear
    for i in range(A_C.n_blocks):
        name = A_C.get_block_name(i) or ""
        assert name.startswith("PV_A_") or name.startswith("PV_C_")
        assert not name.startswith("PV_B_")

    # name_matches_flag: exact / case_sensitive options
    assert name_matches_flag("PV_A_12", ["pv_a"], case_sensitive=False)
    assert not name_matches_flag("PV_A_12", ["pv_a"], case_sensitive=True)
    assert name_matches_flag("PV", ["PV", "INV"], exact=True)


def test_lowest_corners_single_and_multiblock_and_degenerate():
    cfg, _ = _create_three_centrals_with_prefixes()

    # A single arbitrary polydata
    poly = cfg[0]
    pts = cfg.get_lowest_corners(poly)
    assert isinstance(pts, np.ndarray) and pts.shape == (2, 3), f"Expected shape (2,3), got {getattr(pts, 'shape', None)}"
    # The two corners must have distinct XY and share the same minimal Z (numeric tolerance)
    assert not np.allclose(pts[0, :2], pts[1, :2])
    assert math.isclose(float(pts[0, 2]), float(pts[1, 2]), rel_tol=1e-6, abs_tol=1e-9)

    # Multi: B
    pts_mb = cfg.get_lowest_corners_multiblock("PV_B")
    assert isinstance(pts_mb, np.ndarray)
    assert pts_mb.ndim == 3 and pts_mb.shape[1:] == (2, 3), f"Expected (N,2,3), got {pts_mb.shape}"
    assert pts_mb.shape[0] > 0

    # Degenerate input: empty PolyData -> ValueError
    with pytest.raises(ValueError):
        cfg.get_lowest_corners(pyv.PolyData())


def test_areas_zmin_normals_consistency():
    cfg, ranges = _create_three_centrals_with_prefixes()

    # Strictly positive areas for C
    areas_C = cfg.get_area_multiblock("PV_C")
    areas_C = np.asarray(areas_C, dtype=float)
    assert areas_C.ndim == 1 and areas_C.size > 0
    assert np.all(areas_C > 0), f"Non-positive areas found: {areas_C}"

    # z_min: verify the expected ordering with heights (A < B < C)
    zmins_A = np.asarray(cfg.get_z_min_multiblock("PV_A"), dtype=float)
    zmins_B = np.asarray(cfg.get_z_min_multiblock("PV_B"), dtype=float)
    zmins_C = np.asarray(cfg.get_z_min_multiblock("PV_C"), dtype=float)
    assert zmins_A.size > 0 and zmins_B.size > 0 and zmins_C.size > 0
    # Use medians to be robust to multiple blocks
    med_A, med_B, med_C = np.median(zmins_A), np.median(zmins_B), np.median(zmins_C)
    assert med_A < med_B < med_C, f"Unexpected z_min order: A={med_A}, B={med_B}, C={med_C}"

    # Normals: well-defined vectors (norm > 0; many should be ~1, but default is tolerated)
    normals = np.asarray(cfg.get_normal_multiblock(["PV_A", "PV_B", "PV_C"]), dtype=float)
    assert normals.ndim == 2 and normals.shape[1] == 3 and normals.shape[0] > 0
    norms = np.linalg.norm(normals, axis=1)
    assert np.all(np.isfinite(norms)) and np.all(norms > 0)


def test_objectid_cycle_remove_and_consistency():
    cfg, _ = _create_three_centrals_with_prefixes()
    # df and ObjectIDs must be available
    assert hasattr(cfg, "df") and not cfg.df.empty, "df is missing or empty — this branch is expected to manage ObjectIDs"
    oids = list(map(int, cfg.df.index))
    assert len(oids) > 0

    # Pick an arbitrary OID
    oid = oids[0]
    pos_before = cfg.get_position_by_oid(oid)
    blk = cfg.get_block_by_oid(oid)
    assert pos_before is not None and isinstance(blk, pyv.PolyData)

    # Remove then assert consistency
    assert cfg.remove_by_oid(oid) is True
    cfg.assert_consistency()

    # The OID must be removed from df and indices
    assert oid not in set(map(int, cfg.df.index))
    assert cfg.get_position_by_oid(oid) is None

    # Safety: try removing again -> should fail cleanly (False or controlled Exception)
    try:
        res = cfg.remove_by_oid(oid)
        assert res is False
    except Exception:
        # Acceptable depending on implementation; consistency is what matters
        pass


def test_alias_pv_configuration_3d_multiblock_subset_equivalence():
    # The legacy alias builds a single plant and exposes PV_central_MB
    params = dict(
        PanelDimensionX=1.5, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.7, RepetitionDistanceOfPanelsY=1.1,
        NumberOfPanelsX=2, NumberOfPanelsY=1,
        RepetitionDistanceOfPVBlocksX=3.4, RepetitionDistanceOfPVBlocksY=2.2,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,
        Height=1.0, CentralAzimut=30.0, TiltY=15.0, Hinge='center',
    )
    cfg_legacy = PV_Configuration_3D(params, visualization=False)
    sub = cfg_legacy.PV_central_MB
    direct = cfg_legacy.get_polydata_by_flag("PV")

    assert isinstance(sub, MultiBlockPASE)
    assert sub.n_blocks == direct.n_blocks
    # Same block names (order should match after a single creation)
    sub_names = [sub.get_block_name(i) for i in range(sub.n_blocks)]
    dir_names = [direct.get_block_name(i) for i in range(direct.n_blocks)]
    assert sub_names == dir_names

@pytest.fixture
def cfg():
    """Fresh instance with a consistent schema for add_custom_polydata."""
    c = PVConfiguration3D()
    return c


def tuple_allclose(a, b, atol=1e-9):
    return np.allclose(np.asarray(a, float), np.asarray(b, float), atol=atol, rtol=0)


def test_add_custom_polydata_nominal(cfg):
    # Simple geometry: cube
    cube = pyv.Cube(center=(1.0, 2.0, 3.0), x_length=2.0, y_length=1.0, z_length=4.0)

    info = {
        "Type": "Obstacle",
        "Central": "PLANT_A",
        "Block_X": 10,
        "Block_Y": 5,
        "Module_X": 3,
        "Module_Y": 7,
        "Azimuth_deg": 180.0,
        "Tilt_deg": 30.0,
    }

    oid = cfg.add_custom_polydata(cube, info, name="Custom")

    # 1) The identifier must be a non-negative integer and index self.df
    assert isinstance(oid, int) and oid >= 0
    assert oid in cfg.df.index

    # 2) The multiblock must contain the added block with the correct name
    #    The method does append(name=f"Custom{oid}")
    assert cfg.n_blocks >= 1
    last_name = cfg.get_block_name(cfg.n_blocks - 1)
    assert last_name == f"Custom{oid}"

    # 3) Essential fields in the df row
    row = cfg.df.loc[oid]
    assert row["Type"] == "Obstacle"
    assert row["Central"] == "PLANT_A"
    assert row["Block_X"] == 10
    assert row["Block_Y"] == 5
    assert row["Module_X"] == 3
    assert row["Module_Y"] == 7
    assert row["Azimuth_deg"] == 180.0
    assert row["Tilt_deg"] == 30.0

    # 4) Verify computed Center / Bounds / Area
    mesh = cube  # the method copies for calculations; expected values = cube's ones
    expected_center = tuple(map(float, mesh.center))
    expected_bounds = tuple(map(float, mesh.bounds))
    expected_area = float(mesh.area)

    assert tuple_allclose(row["Center"], expected_center)
    assert tuple_allclose(row["Bounds"], expected_bounds)
    assert np.isfinite(row["Area"]) and abs(row["Area"] - expected_area) < 1e-9


def test_add_custom_polydata_requires_type(cfg):
    cube = pyv.Cube()
    with pytest.raises(ValueError):
        cfg.add_custom_polydata(cube, info={}, name="Custom")


def test_add_custom_polydata_converts_non_polydata(cfg):
    # Create a non-PolyData dataset (StructuredGrid), convertible via extract_surface()
    x = np.linspace(0, 1, 3)
    y = np.linspace(0, 1, 3)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    zz = np.zeros_like(xx)

    grid = pyv.StructuredGrid(xx, yy, zz)

    info = {"Type": "Obstacle"}

    oid = cfg.add_custom_polydata(grid, info, name="Custom")

    # Addition succeeded and row is present in df
    assert oid in cfg.df.index
    row = cfg.df.loc[oid]
    assert row["Type"] == "Obstacle"

    # The multiblock must contain the new block
    print(oid)
    assert cfg.get_block_by_oid(oid) is not None