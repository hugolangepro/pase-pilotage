from pase.DATA_MANAGEMENT.input_checker import InputsEvaluator, EvalResult

import builtins
import pytest
import time

# -----------------------
# helpers
# -----------------------

class DummyInput:
    """Simulate user inputs for input()."""
    def __init__(self, responses):
        self._responses = responses
        self._index = 0

    def __call__(self, prompt=""):
        if self._index < len(self._responses):
            val = self._responses[self._index]
            self._index += 1
            return val
        return ""


# -----------------------
# basic behavior
# -----------------------

def test_tracking_true_rotation_axis():
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1,
         "MF": 1}
    e = InputsEvaluator(d)
    assert e.tracking_active is True
    assert e.n_source_points == 4
    assert isinstance(e.mf, int)


def test_tracking_false_boolean_key():
    d = {"Tracking": False,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 2, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 2, "dY_InterestZone": 1,
         "MF": 2}
    e = InputsEvaluator(d)
    assert e.tracking_active is False
    assert e.n_source_points == 9
    assert isinstance(e.mf, int)


def test_invalid_tracking_value():
    d = {"Tracking": "bad"}
    with pytest.raises(ValueError):
        InputsEvaluator(d)


def test_invalid_rotation_axis_number():
    d = {"RotationAxisNumber": 5}
    with pytest.raises(ValueError):
        InputsEvaluator(d)


def test_missing_interest_zone_keys():
    d = {"RotationAxisNumber": 1}
    with pytest.raises(KeyError):
        InputsEvaluator(d)


def test_invalid_mf_type():
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1,
         "MF": "bad"}
    with pytest.raises(ValueError):
        InputsEvaluator(d)


# -----------------------
# thresholds and warnings
# -----------------------

def test_thresholds_trigger_and_continue(monkeypatch, capsys):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 40, "dX_InterestZone": 0.5,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 40, "dY_InterestZone": 0.5,
         "MF": 5}
    monkeypatch.setattr(builtins, "input", DummyInput(["y"]))
    e = InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1)
    out = capsys.readouterr().out
    assert "[WARNING]" in out
    assert e.tracking_active is True


def test_thresholds_trigger_and_exit(monkeypatch):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 10, "dX_InterestZone": 0.5,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 10, "dY_InterestZone": 0.5,
         "MF": 5}
    monkeypatch.setattr(builtins, "input", DummyInput(["n"]))
    with pytest.raises(SystemExit):
        InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1)


def test_thresholds_trigger_and_edit_reduce_mf(monkeypatch):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 10, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 10, "dY_InterestZone": 1,
         "MF": 5}
    monkeypatch.setattr(builtins, "input", DummyInput(["e", "1", "2"]))
    e = InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1)
    assert d["MF"] == 2
    assert e.mf == 2


def test_edit_coarsen_grid(monkeypatch):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 20, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 20, "dY_InterestZone": 1,
         "MF": 5}
    monkeypatch.setattr(builtins, "input", DummyInput(["e", "2"]))
    e = InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1)
    # grid should be coarsened
    assert d["dX_InterestZone"] > 1
    assert d["dY_InterestZone"] > 1
    assert e.n_source_points < 441  # original 21*21=441


def test_edit_disable_tracking(monkeypatch):
    d = {"Tracking": True,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 5, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 5, "dY_InterestZone": 1,
         "MF": 2}
    monkeypatch.setattr(builtins, "input", DummyInput(["e", "3"]))
    e = InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1)
    assert d["Tracking"] is False
    assert e.tracking_active is False


# -----------------------
# timeout fallback
# -----------------------

def test_prompt_timeout(monkeypatch, capsys):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 10, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 10, "dY_InterestZone": 1,
         "MF": 5}
    def slow_input(prompt=""):
        time.sleep(1)

    monkeypatch.setattr(builtins, "input", slow_input)
    e = InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1, input_timeout=0.1)
    out = capsys.readouterr().out
    assert "default 'y'" in out or "keeping current parameters" in out
    assert isinstance(e.tracking_active, bool)

def test_multiple_dicts_merging():
    d1 = {"RotationAxisNumber": 0, "MF": 1}
    d2 = {
        "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
        "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1,
    }
    e = InputsEvaluator(d1, d2)
    # Values from both dicts should be merged
    assert e.n_source_points == 4
    assert e.mf == 1
    assert e.tracking_active is False


def test_rotation_axis_zero_means_inactive():
    d = {"RotationAxisNumber": 0,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1,
         "MF": 1}
    e = InputsEvaluator(d)
    assert e.tracking_active is False


def test_tracking_true_boolean_key():
    d = {"Tracking": True,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1,
         "MF": 1}
    e = InputsEvaluator(d)
    assert e.tracking_active is True


def test_mf_absent_returns_none():
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1}
    e = InputsEvaluator(d)
    assert e.mf is None


def test_coarsen_grid_factor_clamped(monkeypatch):
    # Already ~100 points: factor < 1 → should clamp to 1 (no change)
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 9, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 9, "dY_InterestZone": 1,
         "MF": 2}
    monkeypatch.setattr(builtins, "input", DummyInput(["e", "2"]))
    e = InputsEvaluator(d, nSourcePoints_threshold=5, MF_threshold=1)
    # dX and dY unchanged (factor clamped to 1)
    assert d["dX_InterestZone"] == 1
    assert d["dY_InterestZone"] == 1


def test_timed_prompt_empty_input(monkeypatch, capsys):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 5, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 5, "dY_InterestZone": 1,
         "MF": 2}
    # Simulate user pressing Enter (empty input)
    monkeypatch.setattr(builtins, "input", DummyInput([""]))
    e = InputsEvaluator(d, nSourcePoints_threshold=5, MF_threshold=1)
    out = capsys.readouterr().out
    # Should proceed with default 'y'
    assert "default" not in out  # no timeout
    assert isinstance(e.tracking_active, bool)


def test_timed_prompt_invalid_input(monkeypatch, capsys):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 5, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 5, "dY_InterestZone": 1,
         "MF": 2}
    monkeypatch.setattr(builtins, "input", DummyInput(["foo"]))
    e = InputsEvaluator(d, nSourcePoints_threshold=5, MF_threshold=1)
    out = capsys.readouterr().out
    assert "[WARNING] Invalid input" in out


def test_no_thresholds_triggered(monkeypatch, capsys):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 1, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 1, "dY_InterestZone": 1,
         "MF": 1}
    # Should not trigger warnings → no input prompt needed
    monkeypatch.setattr(builtins, "input", DummyInput(["y"]))  # won't be used
    e = InputsEvaluator(d, nSourcePoints_threshold=500, MF_threshold=10)
    out = capsys.readouterr().out
    assert "[WARNING]" not in out


def test_edit_idle_keeps_parameters(monkeypatch, capsys):
    d = {"RotationAxisNumber": 1,
         "Xmin_InterestZone": 0, "Xmax_InterestZone": 10, "dX_InterestZone": 1,
         "Ymin_InterestZone": 0, "Ymax_InterestZone": 10, "dY_InterestZone": 1,
         "MF": 5}
    # First answer 'e' to enter edit, then idle → no change
    def slow_input(prompt=""):
        time.sleep(1)  # triggers timeout

    # First response "e" for policy prompt, then delegate to slow_input
    def combined_input(prompt=""):
        if not hasattr(combined_input, "called"):
            combined_input.called = True
            return "e"
        return slow_input(prompt)

    monkeypatch.setattr(builtins, "input", combined_input)
    e = InputsEvaluator(d, nSourcePoints_threshold=10, MF_threshold=1,
                        input_timeout=0.1)
    out = capsys.readouterr().out

    assert "keeping current parameters" in out
    assert d["MF"] == 5