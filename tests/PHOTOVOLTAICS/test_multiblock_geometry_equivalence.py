import random
import numpy as np
import pyvista as pv
import pytest

from pase.PHOTOVOLTAICS.configuration import (
    PV_Configuration_3D,
    PVConfiguration3D,
    MultiBlockPASE,
)
from poly_compare import compare_polydata


def _merge_multiblock_to_poly(mb: MultiBlockPASE) -> pv.PolyData:
    """Merge all PolyData blocks of a MultiBlock into one PolyData (point-merging enabled)."""
    polys = [mb[i] for i in range(mb.n_blocks)]
    return pv.merge(polys, merge_points=True)


def _create_three_centrals_prefixed():
    """
    Create 3 PV plants on one PVConfiguration3D, rename new blocks to PV_A_*, PV_B_*, PV_C_*, reindex.
    Return (cfg, ranges) with block index ranges per prefix and the merged 'all PV' mesh.
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
        for i in range(start, end):
            name = cfg.get_block_name(i) or "PV"
            cfg.set_block_name(i, f"{prefix}_{name}")
        cfg.reindex()
        ranges[prefix] = (start, end)
    mb_all = cfg.get_polydata_by_flag(["PV_A","PV_B","PV_C"])
    return cfg, ranges, mb_all


def test_union_by_list_vs_manual_concat_equivalent_geometry():
    """
    Compare geometry produced by:
      (1) a single query with multiple flags, and
      (2) manually concatenating sub-queries in a different order.
    """
    cfg, _, _ = _create_three_centrals_prefixed()
    via_list = cfg.get_polydata_by_flag(["PV_A", "PV_B", "PV_C"])

    # manual concatenation, purposely shuffle order to ensure order-independence
    order = ["PV_C", "PV_A", "PV_B"]
    manual = MultiBlockPASE()
    for f in order:
        sub = cfg.get_polydata_by_flag(f)
        for i in range(sub.n_blocks):
            manual.append(sub[i], name=sub.get_block_name(i))
    cfg.reindex()  # (safe; not strictly needed for merging)

    poly_list = _merge_multiblock_to_poly(via_list)
    poly_manual = _merge_multiblock_to_poly(manual)

    assert compare_polydata(poly_list, poly_manual), "Merged geometry differs between list-query and manual concat"


def test_ac_union_equivalence_direct_vs_two_queries():
    """
    Compare geometry for A ∪ C built in two ways:
      (1) get_polydata_by_flag(['PV_A','PV_C'])
      (2) merge(get_polydata_by_flag('PV_A'), get_polydata_by_flag('PV_C'))
    """
    cfg, _, _ = _create_three_centrals_prefixed()
    direct = cfg.get_polydata_by_flag(["PV_A", "PV_C"])
    A = cfg.get_polydata_by_flag("PV_A")
    C = cfg.get_polydata_by_flag("PV_C")

    ac_manual = MultiBlockPASE()
    for mb in (A, C):
        for i in range(mb.n_blocks):
            ac_manual.append(mb[i], name=mb.get_block_name(i))

    poly_direct = _merge_multiblock_to_poly(direct)
    poly_manual = _merge_multiblock_to_poly(ac_manual)

    assert compare_polydata(poly_direct, poly_manual), "Direct A∪C and manual A + C geometries are not equivalent"


def test_flag_vs_oid_selection_same_geometry_for_A():
    """
    Compare geometry for PV_A obtained by:
      (1) flag selection, and
      (2) selecting blocks by OID set (shuffled), then merging.
    """
    cfg, _, _ = _create_three_centrals_prefixed()

    # baseline via flag
    A_flag = cfg.get_polydata_by_flag("PV_A")
    poly_flag = _merge_multiblock_to_poly(A_flag)

    # via ObjectIDs (shuffle to change order)
    oids = list(map(int, cfg.df.index))
    pos_by_oid = {
        oid: cfg.get_position_by_oid(oid)
        for oid in oids
    }
    names = {
        oid: cfg.get_block_name(pos) if pos is not None else None
        for oid, pos in pos_by_oid.items()
    }
    A_oids = [oid for oid, nm in names.items() if isinstance(nm, str) and nm.startswith("PV_A_")]
    assert A_oids, "No PV_A_* OIDs found; check setup"
    random.shuffle(A_oids)

    manual = MultiBlockPASE()
    for oid in A_oids:
        pos = cfg.get_position_by_oid(oid)
        assert pos is not None
        manual.append(cfg[pos], name=cfg.get_block_name(pos))
    poly_oid = _merge_multiblock_to_poly(manual)

    assert compare_polydata(poly_flag, poly_oid), "Flag-based and OID-based selections for PV_A are not geometrically equal"


def test_whole_scene_equivalence_various_paths():
    """
    Compare 'all PV' geometry from:
      (1) cfg.get_polydata_by_flag(['PV_A','PV_B','PV_C'])
      (2) merging each prefix one by one (C, A, B)
      (3) legacy alias PV_Configuration_3D single plant == flag 'PV' (sanity)
    """
    cfg, _, mb_all = _create_three_centrals_prefixed()

    # (1) baseline
    poly_1 = _merge_multiblock_to_poly(mb_all)

    # (2) manual build in different order
    manual = MultiBlockPASE()
    for flag in ("PV_C", "PV_A", "PV_B"):
        sub = cfg.get_polydata_by_flag(flag)
        for i in range(sub.n_blocks):
            manual.append(sub[i], name=sub.get_block_name(i))
    poly_2 = _merge_multiblock_to_poly(manual)

    assert compare_polydata(poly_1, poly_2), "Whole-scene geometry differs between list query and sequential build"

    # (3) alias sanity: single-plant configuration returns same as flag 'PV' for that instance
    params = dict(
        PanelDimensionX=1.5, PanelDimensionY=1.0, PanelThickness=False,
        RepetitionDistanceOfPanelsX=1.7, RepetitionDistanceOfPanelsY=1.1,
        NumberOfPanelsX=2, NumberOfPanelsY=1,
        RepetitionDistanceOfPVBlocksX=3.4, RepetitionDistanceOfPVBlocksY=2.2,
        NumberOfPVBlocksX=1, NumberOfPVBlocksY=1,
        Height=1.0, CentralAzimut=30.0, TiltY=15.0, Hinge='center',
    )
    cfg_legacy = PV_Configuration_3D(params, visualization=False)
    poly_alias = _merge_multiblock_to_poly(cfg_legacy.PV_central_MB)
    poly_flag = _merge_multiblock_to_poly(cfg_legacy.get_polydata_by_flag("PV"))
    assert compare_polydata(poly_alias, poly_flag), "Legacy alias PV_central_MB differs from flag 'PV' geometry"


@pytest.mark.parametrize("tol", [1e-6, 1e-9])
def test_compare_polydata_tolerance_and_order_insensitivity(tol):
    """
    Show that compare_polydata is robust to small numeric noise and ordering.
    We fabricate two identical squares with slightly jittered point order.
    """
    pts = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]], dtype=float)
    faces = np.hstack(([4], [0,1,2,3])).astype(np.int64)
    a = pv.PolyData(pts.copy(), faces.copy())

    # same geometry but permuted points and face order reversed
    perm = [2,1,0,3]
    pts2 = pts[perm] + np.random.default_rng(0).normal(scale=tol/10, size=pts.shape)
    faces2 = np.hstack(([4], [perm.index(i) for i in [0,3,2,1]])).astype(np.int64)  # reverse orientation
    b = pv.PolyData(pts2, faces2)

    assert compare_polydata(a, b, tol=tol), "Comparator should accept jittered coordinates and different order/orientation"
