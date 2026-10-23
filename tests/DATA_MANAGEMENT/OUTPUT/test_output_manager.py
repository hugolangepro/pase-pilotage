import json
import pytest
from pathlib import Path

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager

PASE_Logger()

# Constants
LOC = {'Name': 'Gembloux'}
LOC2 = {'Name': 'Denver'}
LOC3 = {'Name': 'Freiburg'}
AV = {'NumberPanelsX': 1}
PV_MODULE = {'PanelsSizeX': 1.5}
STRUCTURE = {'StructureType': 'Agrivoltaic fence'}
CROP_CONFIG = {'CropModel': 'Grassim'}

def test_set_pase_root_and_project(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    om = OutputsManager("Loc", 2020, 2021)
    assert om.root == tmp_path
    assert om.project == "Loc_2020-2021"


def test_setup_variant_creates_structure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    om = OutputsManager("SiteA", 2019, 2020)

    vroot = om.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                             structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    # expected subdirectories from SUBDIRS constant:
    assert (vroot / "1-inputs").is_dir()
    assert (vroot / "2-data").is_dir()
    assert (vroot / "3-interm_results").is_dir() or (vroot / "3-interm_results").exists()
    assert (vroot / "4-results").is_dir()

    # input hash and inputs.json should exist
    assert (vroot / "1-inputs" / "input_hash.txt").exists()
    assert (vroot / "1-inputs" / "simulation_metadata.yaml").exists()


def test_variant_auto_increment_and_names(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    om = OutputsManager("ProjInc", 2000, 2001)

    v1 = om.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                          structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    assert v1.name.startswith("variant_")
    assert v1.name.endswith(v1.name.split("_")[-1])  # sanity

    v2 = om.setup_variant(loc=LOC2, av=AV, pv_module=PV_MODULE,
                          structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    # ensure different name from v1
    assert v2.name != v1.name

    v3 = om.setup_variant(loc=LOC3, av=AV, pv_module=PV_MODULE,
                          structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    assert v3.name != v2.name and v3.name != v1.name


def test_hash_based_reuse(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    om1 = OutputsManager("ReuseProj", 2010, 2012)
    v1 = om1.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                           structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    # Recreate manager to simulate clean run, same inputs
    om2 = OutputsManager("ReuseProj", 2010, 2012)
    v2 = om2.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                           structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)

    # should reuse same variant folder
    assert v1.resolve() == v2.resolve()
    assert v1.resolve().name == v2.resolve().name


def test_custom_variant_override(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    om = OutputsManager("CustomProj", 2005, 2006)

    v_custom = om.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                                structure=STRUCTURE, crop_config=CROP_CONFIG,
                                variant="my_run",
                                source=__file__)
    assert v_custom.name == "my_run"

    # subsequent different inputs without override should create an auto variant
    v_auto = om.setup_variant(loc=LOC2, av=AV, pv_module=PV_MODULE,
                              structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    assert v_auto.name != "my_run"
    assert v_auto.exists()


def test_registry_updates_and_contents(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    om = OutputsManager("RegProj", 2015, 2016)

    v1 = om.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                          structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)
    v2 = om.setup_variant(loc=LOC2, av=AV, pv_module=PV_MODULE,
                          structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)

    registry_path = om.project_root / "variants.json"
    assert registry_path.exists()

    registry = json.loads(registry_path.read_text())
    assert v1.name in registry
    assert v2.name in registry

    e1 = registry[v1.name]
    assert "hash" in e1 and "timestamp" in e1

def test_save_load_helpers_and_cache_weather(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    om = OutputsManager("IOProj", 2017, 2018)

    # prepare variant
    variant_dir = om.setup_variant(loc=LOC, av=AV, pv_module=PV_MODULE,
                                   structure=STRUCTURE, crop_config=CROP_CONFIG,
                             source=__file__)

    # JSON save/load
    om.save_json_to_cache("r1.json", {"val": 123})
    assert om.load_json_from_cache("r1.json") == {"val": 123}

    # bytes save/load
    om.save_bytes("data", "bin.dat", b"spam")
    assert om.load_bytes("data", "bin.dat") == b"spam"

    # test weather caching via load_or_fetch_weather (fetch function called once)
    calls = {"n": 0}

    def fake_fetch():
        calls["n"] += 1
        return {"weather": "clear"}

    d1 = om.load_or_fetch_weather("loc_1_2020", fake_fetch)
    d2 = om.load_or_fetch_weather("loc_1_2020", fake_fetch)
    assert d1 == d2
    assert calls["n"] == 1

    # cached file exists on disk under variant's 2-data
    assert (om.CACHE_DIR/"wd_loc_1_2020.json").exists()

    # Cleanup under CACHE_DIR
    Path.unlink(om.CACHE_DIR/"wd_loc_1_2020.json")
    Path.unlink(om.CACHE_DIR/"r1.json")
