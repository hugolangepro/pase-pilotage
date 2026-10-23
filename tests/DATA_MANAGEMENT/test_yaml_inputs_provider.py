import pytest

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator

PASE_Logger()


def _bare_provider():
    """Build a YAML_Inputs_provider instance without going through __init__/file loading."""
    provider = YAML_Inputs_provider.__new__(YAML_Inputs_provider)
    provider.inputs = {}
    return provider


# -----------------------
# check_possibilities
# -----------------------

def test_check_possibilities_numeric_value_passes():
    provider = _bare_provider()
    data = {"Value": 2, "Possibilities": [1, 2, 3]}

    provider.check_possibilities("MF", data)

    assert provider.inputs["MF"] == 2


def test_check_possibilities_string_is_normalized():
    provider = _bare_provider()
    data = {"Value": " StIcS ", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    provider.check_possibilities("CropModel", data)

    assert provider.inputs["CropModel"] == "stics"


def test_check_possibilities_invalid_value_raises():
    provider = _bare_provider()
    data = {"Value": "unknown_model", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    with pytest.raises(ValueError) as excinfo:
        provider.check_possibilities("CropModel", data)

    assert "CropModel" in str(excinfo.value)
    assert "stics" in str(excinfo.value)
    assert "unknown_model" in str(excinfo.value)


def test_check_possibilities_rejects_non_list_possibilities():
    provider = _bare_provider()
    data = {"Value": "stics", "Possibilities": "stics, grassim, simple, pystics"}

    with pytest.raises(TypeError, match="square brackets"):
        provider.check_possibilities("CropModel", data)


def test_check_possibilities_mixed_type_list():
    provider = _bare_provider()
    data = {"Value": "a", "Possibilities": ["A", 1]}

    provider.check_possibilities("Key", data)

    assert provider.inputs["Key"] == "a"


def test_check_possibilities_boolean_value_not_normalized():
    provider = _bare_provider()
    data = {"Value": True, "Possibilities": [True, False]}

    provider.check_possibilities("Flag", data)

    assert provider.inputs["Flag"] is True


# -----------------------
# check_value_str
# -----------------------

def test_check_value_str_with_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": " StIcS ", "Type": "string", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    provider.check_value_str("CropModel", data, {})

    assert provider.inputs["CropModel"] == "stics"


def test_check_value_str_with_possibilities_invalid_raises():
    provider = _bare_provider()
    data = {"Value": "unknown_model", "Type": "string", "Possibilities": ["stics", "grassim", "simple", "pystics"]}

    with pytest.raises(ValueError):
        provider.check_value_str("CropModel", data, {})


def test_check_value_str_without_possibilities_is_not_normalized():
    # Documents current behavior: stripping/lowering only happens inside
    # check_possibilities, so a string without a Possibilities list is stored verbatim.
    provider = _bare_provider()
    data = {"Value": " Chanco_Chile_WD ", "Type": "string"}

    provider.check_value_str("WeatherFileName", data, {})

    assert provider.inputs["WeatherFileName"] == " Chanco_Chile_WD "


# -----------------------
# check_value_bool
# -----------------------

def test_check_value_bool_with_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": True, "Type": "boolean", "Possibilities": [True, False]}

    provider.check_value_bool("Flag", data, {})

    assert provider.inputs["Flag"] is True


def test_check_value_bool_with_possibilities_invalid_raises():
    provider = _bare_provider()
    data = {"Value": True, "Type": "boolean", "Possibilities": [False]}

    with pytest.raises(ValueError):
        provider.check_value_bool("Flag", data, {})


# -----------------------
# check_value_list
# -----------------------

def test_check_value_list_with_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": [1, 2], "Type": "list", "Possibilities": [[1, 2], [3, 4]]}

    provider.check_value_list("Coords", data, {})

    assert provider.inputs["Coords"] == [1, 2]


def test_check_value_list_with_possibilities_invalid_raises():
    provider = _bare_provider()
    data = {"Value": [9, 9], "Type": "list", "Possibilities": [[1, 2], [3, 4]]}

    with pytest.raises(ValueError):
        provider.check_value_list("Coords", data, {})


# -----------------------
# check_value_float (Limit is checked before Possibilities)
# -----------------------

def test_check_value_float_with_limits_and_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": 15.0, "Type": "float", "Limit": [0, 100], "Possibilities": [15.0, 30.0]}

    provider.check_value_float("Tilt", data, {})

    assert provider.inputs["Tilt"] == 15.0


def test_check_value_float_limits_pass_possibilities_fail_raises():
    provider = _bare_provider()
    data = {"Value": 20.0, "Type": "float", "Limit": [0, 100], "Possibilities": [15.0, 30.0]}

    with pytest.raises(ValueError):
        provider.check_value_float("Tilt", data, {})


# -----------------------
# check_value_int (Limit is checked before Possibilities)
# -----------------------

def test_check_value_int_with_limits_and_possibilities_valid():
    provider = _bare_provider()
    data = {"Value": 2, "Type": "integer", "Limit": [1, 5], "Possibilities": [1, 2, 3]}

    provider.check_value_int("Option", data, {})

    assert provider.inputs["Option"] == 2


def test_check_value_int_limits_pass_possibilities_fail_raises():
    provider = _bare_provider()
    data = {"Value": 4, "Type": "integer", "Limit": [1, 5], "Possibilities": [1, 2, 3]}

    with pytest.raises(ValueError):
        provider.check_value_int("Option", data, {})


# -----------------------
# check_limits: conditional skip for superfluous repetition distances
# -----------------------

def _pv_blocks_inputs(n_blocks_x=4, n_blocks_y=4, n_panels_x=1, n_panels_y=16):
    """Minimal `inputs` dict holding the params referenced by the repetition-distance limits."""
    return {
        "NumberOfPanelsX": {"Value": n_panels_x},
        "RepetitionDistanceOfPanelsX": {"Value": 2.45},
        "NumberOfPanelsY": {"Value": n_panels_y},
        "RepetitionDistanceOfPanelsY": {"Value": 1.31},
        "NumberOfPVBlocksX": {"Value": n_blocks_x},
        "NumberOfPVBlocksY": {"Value": n_blocks_y},
    }


def test_check_limits_skipped_with_single_block_x():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_blocks_x=1)
    # 0.5 < NumberOfPanelsX*RepetitionDistanceOfPanelsX (= 2.45): would fail if checked.
    data = {"Value": 0.5, "Type": "float",
            "Limit": ["NumberOfPanelsX*RepetitionDistanceOfPanelsX", 1000]}

    provider.check_limits("RepetitionDistanceOfPVBlocksX", data, inputs)

    assert provider.inputs["RepetitionDistanceOfPVBlocksX"] == 0.5


def test_check_limits_skipped_with_zero_blocks_x():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_blocks_x=0)
    data = {"Value": 0.5, "Type": "float",
            "Limit": ["NumberOfPanelsX*RepetitionDistanceOfPanelsX", 1000]}

    provider.check_limits("RepetitionDistanceOfPVBlocksX", data, inputs)

    assert provider.inputs["RepetitionDistanceOfPVBlocksX"] == 0.5


def test_check_limits_still_enforced_with_multiple_blocks_x():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_blocks_x=4)
    data = {"Value": 0.5, "Type": "float",
            "Limit": ["NumberOfPanelsX*RepetitionDistanceOfPanelsX", 1000]}

    with pytest.raises(ValueError):
        provider.check_limits("RepetitionDistanceOfPVBlocksX", data, inputs)


def test_check_limits_valid_value_with_multiple_blocks_x():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_blocks_x=4)
    # 4.5 >= 2.45 and <= 1000: passes normally.
    data = {"Value": 4.5, "Type": "float",
            "Limit": ["NumberOfPanelsX*RepetitionDistanceOfPanelsX", 1000]}

    provider.check_limits("RepetitionDistanceOfPVBlocksX", data, inputs)

    assert provider.inputs["RepetitionDistanceOfPVBlocksX"] == 4.5


def test_check_limits_skipped_with_single_block_y():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_blocks_y=1)
    # 0.5 < NumberOfPanelsY*RepetitionDistanceOfPanelsY (= 16*1.31): would fail if checked.
    data = {"Value": 0.5, "Type": "float",
            "Limit": ["NumberOfPanelsY*RepetitionDistanceOfPanelsY", 1000]}

    provider.check_limits("RepetitionDistanceOfPVBlocksY", data, inputs)

    assert provider.inputs["RepetitionDistanceOfPVBlocksY"] == 0.5


def test_check_limits_non_conditional_param_still_enforced():
    # A param not in CONDITIONAL_LIMIT_GOVERNORS must still be validated, even if a block
    # count of 1 is present in inputs (guards against the early-out over-matching).
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_blocks_x=1)
    data = {"Value": 250.0, "Type": "float", "Limit": [-90, 90]}

    with pytest.raises(ValueError):
        provider.check_limits("TiltY", data, inputs)


def test_check_limits_skipped_with_single_panel_x():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_panels_x=1)
    # 150 > 100 (upper limit): would fail if checked, but a lone panel makes it superfluous.
    data = {"Value": 150.0, "Type": "float", "Limit": [0, 100]}

    provider.check_limits("RepetitionDistanceOfPanelsX", data, inputs)

    assert provider.inputs["RepetitionDistanceOfPanelsX"] == 150.0


def test_check_limits_still_enforced_with_multiple_panels_x():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_panels_x=16)
    data = {"Value": 150.0, "Type": "float", "Limit": [0, 100]}

    with pytest.raises(ValueError):
        provider.check_limits("RepetitionDistanceOfPanelsX", data, inputs)


def test_check_limits_skipped_with_single_panel_y():
    provider = _bare_provider()
    inputs = _pv_blocks_inputs(n_panels_y=1)
    data = {"Value": 150.0, "Type": "float", "Limit": [0, 100]}

    provider.check_limits("RepetitionDistanceOfPanelsY", data, inputs)

    assert provider.inputs["RepetitionDistanceOfPanelsY"] == 150.0


# -----------------------
# Inputs_aggregator._check_panel_spacing: skip clipping check for a single panel
# -----------------------

def _bare_aggregator(aggregated_inputs):
    """Build an Inputs_aggregator instance without running __init__/sanity checks."""
    aggregator = Inputs_aggregator.__new__(Inputs_aggregator)
    aggregator.aggregated_inputs = aggregated_inputs
    return aggregator


def _panel_spacing_inputs(n_panels_x=1, n_panels_y=1, rep_x=0.5, rep_y=0.5):
    """Aggregated inputs for _check_panel_spacing. Default rep distances clip the 1x1 m panels."""
    return {
        "NumberOfPanelsX": n_panels_x,
        "NumberOfPanelsY": n_panels_y,
        "RepetitionDistanceOfPanelsX": rep_x,
        "RepetitionDistanceOfPanelsY": rep_y,
        "PanelDimensionX": 1.0,
        "PanelDimensionY": 1.0,
    }


def test_check_panel_spacing_skipped_with_single_panel_x():
    # rep_x (0.5) < PanelDimensionX (1.0) would clip, but a single panel in X cannot clip.
    aggregator = _bare_aggregator(_panel_spacing_inputs(n_panels_x=1, n_panels_y=1))

    aggregator._check_panel_spacing()  # must not raise


def test_check_panel_spacing_enforced_with_multiple_panels_x():
    aggregator = _bare_aggregator(_panel_spacing_inputs(n_panels_x=16, n_panels_y=1))

    with pytest.raises(ValueError, match="axis X"):
        aggregator._check_panel_spacing()


def test_check_panel_spacing_enforced_with_multiple_panels_y():
    aggregator = _bare_aggregator(_panel_spacing_inputs(n_panels_x=1, n_panels_y=16))

    with pytest.raises(ValueError, match="axis Y"):
        aggregator._check_panel_spacing()


def test_check_panel_spacing_ok_with_non_clipping_distances():
    aggregator = _bare_aggregator(
        _panel_spacing_inputs(n_panels_x=16, n_panels_y=16, rep_x=1.5, rep_y=1.5))

    aggregator._check_panel_spacing()  # must not raise


# -----------------------
# End-to-end through __init__ / real YAML file
# -----------------------

def test_end_to_end_yaml_with_valid_possibilities_list(tmp_path):
    # Mirrors the real CropModel field in INPUTS/CROPS/config/simple_example.yml
    yaml_content = (
        "CropModel:\n"
        "  Value: Stics\n"
        "  Type: string\n"
        "  Possibilities: [stics, grassim, simple, pystics]\n"
    )
    (tmp_path / "test_inputs.yaml").write_text(yaml_content)

    provider = YAML_Inputs_provider(file="test_inputs.yaml", path=str(tmp_path))

    assert provider.inputs["CropModel"] == "stics"


def test_end_to_end_yaml_possibilities_missing_brackets_raises(tmp_path):
    yaml_content = (
        "CropModel:\n"
        "  Value: stics\n"
        "  Type: string\n"
        "  Possibilities: stics, grassim, simple, pystics\n"
    )
    (tmp_path / "test_inputs.yaml").write_text(yaml_content)

    with pytest.raises(TypeError, match="square brackets"):
        YAML_Inputs_provider(file="test_inputs.yaml", path=str(tmp_path))
