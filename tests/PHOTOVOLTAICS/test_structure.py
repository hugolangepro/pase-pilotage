import pyvista as pyv
import pytest

from pase.PHOTOVOLTAICS.structure import AgrivoltaicFence, HSATS, PVTable


@pytest.fixture
def structure_inputs():
    """Provide a minimal yet coherent configuration for structure classes."""

    base = {
        "PanelsPerGroup": 2,
        "NumberOfStructureGroups": 2,
        "RepetitionDistanceGroupY": 2.0,
        "NumberOfPanelsX": 2,
        "NumberOfPanelsY": 2,
        "RepetitionDistanceOfPanelsX": 2.0,
        "RepetitionDistanceOfPanelsY": 2.0,
        "StructureHeight": 3.0,
        "PoleShape": "circle",
        "PoleWidth": 0.2,
        "PoleHeight": 0.2,
        "PoleSide": 0.2,
        "PoleRadius": 0.1,
        "PoleLength": 3.0,
        "PoleGroundPositioning": 0.0,
        "PurlinShape": "rectangle",
        "PurlinWidth": 0.1,
        "PurlinHeight": 0.05,
        "PurlinSide": 0.1,
        "PurlinRadius": 0.05,
        "NumberOfPurlins": 2,
        "RafterShape": "rectangle",
        "RafterWidth": 0.1,
        "RafterHeight": 0.05,
        "RafterSide": 0.1,
        "RafterLength": 4.0,
        "RafterRadius": 0.05,
        "NumberOfRafters": 2,
        "DiagonalShape": "rectangle",
        "DiagonalWidth": 0.05,
        "DiagonalHeight": 1.0,
        "DiagonalSide": 0.05,
        "DiagonalRadius": 0.05,
        "DiagonalGroundGuard": 0.1,
        "Material": "steel",
        "PanelDimensionX": 1.6,
        "PanelDimensionY": 1.0,
        "RepetitionDistanceOfPVBlocksX": 4.0,
        "RepetitionDistanceOfPVBlocksY": 3.0,
        "NumberOfPVBlocksX": 1,
        "NumberOfPVBlocksY": 1,
        "Height": 2.0,
        "PoleSpacingX": 1.0,
        "TiltY": 15.0,
        "PanelOffset": 0.5,
        "DiagonalEpsilon": 0.000001,
        "RepetitionDistanceGroupYMode": "manual",
    }

    def _factory(**overrides):
        data = base.copy()
        data.update(overrides)
        return data

    return _factory


@pytest.mark.parametrize("structure_cls", [HSATS, PVTable])
@pytest.mark.parametrize(
    "config_overrides",
    [
        {},
        pytest.param(
            {
                "NumberOfPanelsX": 4,
                "NumberOfPanelsY": 2,
                "PanelsPerGroup": 4,
                "NumberOfStructureGroups": 2,
                "RepetitionDistanceGroupY": 2.4,
                "NumberOfPVBlocksX": 2,
                "NumberOfPVBlocksY": 1,
                "RepetitionDistanceOfPVBlocksX": 6.0,
                "RepetitionDistanceOfPanelsY": 2.4,
                "NumberOfPurlins": 3,
                "NumberOfRafters": 3,
                "PoleSpacingX": 1.5,
                "PoleLength": 3.5,
                "RafterLength": 8.0,
                "TiltY": 5.0,
            },
            id="wider-layout",
        ),
    ],
)
def test_structure_builds_without_errors(structure_cls, structure_inputs, config_overrides):
    cfg = structure_inputs(**config_overrides)
    structure = structure_cls(cfg)

    # Check DiagonalEpsilon
    assert structure.diagonal_epsilon == 0.000001

    built = structure.build_structure()

    assert isinstance(built, pyv.DataSet)
    assert built.n_cells > 0


@pytest.mark.parametrize(
    "config_overrides",
    [
        # Base: 1 panel per group, fits within RepetitionDistanceGroupY=2.0m
        # panel_span_x = (2-1)*2.0 = 2.0, top_bar = 2.0+1.0 = 3.0, bottom = 1.0 >= 0.0 ✓
        # panel_span_y = 0*2.0 + 1.0 = 1.0 <= 2.0 ✓
        {"NumberOfPanelsY": 1},
        pytest.param(
            {
                # wider-layout: 4 panels in X, Height raised so bottom bar stays above ground
                # panel_span_x = (4-1)*2.0 = 6.0, top_bar = 4.0+3.0 = 7.0, bottom = 1.0 >= 0.0 ✓
                # panel_span_y = 0*2.4 + 1.0 = 1.0 <= 3.0 ✓
                "NumberOfPanelsX": 4,
                "NumberOfPanelsY": 1,
                "Height": 4.0,
                "PanelsPerGroup": 4,
                "NumberOfStructureGroups": 2,
                "RepetitionDistanceGroupY": 3.0,
                "RepetitionDistanceGroupYMode": "auto",
                "NumberOfPVBlocksX": 2,
                "NumberOfPVBlocksY": 1,
                "RepetitionDistanceOfPVBlocksX": 6.0,
                "RepetitionDistanceOfPanelsY": 2.4,
                "NumberOfPurlins": 3,
                "NumberOfRafters": 3,
                "PoleSpacingX": 1.5,
                "PoleLength": 3.5,
                "RafterLength": 8.0,
                "TiltY": 5.0,
            },
            id="wider-layout",
        ),
    ],
)
def test_agrivoltaic_fence_builds_without_errors(structure_inputs, config_overrides):
    """AgrivoltaicFence requires panels to fit strictly within one group (between two poles)."""
    cfg = structure_inputs(**config_overrides)
    structure = AgrivoltaicFence(cfg)

    assert structure.diagonal_epsilon == 0.000001

    built = structure.build_structure()

    assert isinstance(built, pyv.DataSet)
    assert built.n_cells > 0

def test_agrivoltaic_fence_accepts_minimal_config(structure_inputs):
    """AgrivoltaicFence should build without rafter, diagonal, tilt, or span params."""
    keys_to_drop = [
        'NumberOfRafters', 'RafterShape', 'RafterWidth', 'RafterHeight',
        'RafterSide', 'RafterLength', 'RafterRadius',
        'DiagonalShape', 'DiagonalWidth', 'DiagonalHeight',
        'DiagonalSide', 'DiagonalRadius', 'DiagonalEpsilon',
        'TiltY', 'PoleSpacingX',
    ]
    cfg = structure_inputs(NumberOfPanelsY=1)
    for key in keys_to_drop:
        cfg.pop(key, None)

    built = AgrivoltaicFence(cfg).build_structure()
    assert isinstance(built, pyv.DataSet)
    assert built.n_cells > 0


