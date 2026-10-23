"""Working-directory independence of the light/PV chain.

Static data files (model lookup tables) must resolve relative to the
installed package, and outputs/cache must follow the caller's working
directory — never the package directory. User inputs keep the existing
contract: the user places their ``INPUTS/`` in the directory they launch
from (the tests below provision it into a temporary directory).

``test_light_chain_runs_from_any_cwd`` exercises the full chain and
needs network access to PVGIS; it is skipped unless
``RUN_PASE_INTEGRATION=1`` is set:

    RUN_PASE_INTEGRATION=1 pytest tests/test_path_resolution.py
"""

import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from pase.paths import static_data_path
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager

REPO_ROOT = Path(__file__).parents[1]


def _snapshot_outside_writes():
    """Files currently present where a path regression would write."""
    seen = {d: set(os.listdir(d)) for d in (REPO_ROOT, REPO_ROOT / "pase")}
    outputs = REPO_ROOT / "OUTPUTS"
    seen[outputs] = ({p for p in outputs.rglob('*')}
                     if outputs.exists() else set())
    return seen


def _assert_no_outside_writes(before):
    for d, entries in before.items():
        now = ({p for p in d.rglob('*')} if d.name == "OUTPUTS"
               else set(os.listdir(d))) if d.exists() else set()
        new = {str(p) for p in now - entries}
        assert all("__pycache__" in p for p in new), (
            f"unexpected writes outside tmp_path in {d}: {sorted(new)}")

PV_PARAMS = {
    "PanelDimensionX": 2.384,
    "PanelDimensionY": 1.303,
    "PanelThickness": True,
    "Panel_Peak_Power": 400,
    "Bifaciality": False,
    "Bifaciality_factor": 0.7,
    "NumberOfPanelsX": 1,
    "NumberOfPanelsY": 16,
    "RepetitionDistanceOfPanelsX": 2.450,
    "RepetitionDistanceOfPanelsY": 1.31,
    "NumberOfPVBlocksX": 4,
    "NumberOfPVBlocksY": 1,
    "RepetitionDistanceOfPVBlocksX": 4.5,
    "RepetitionDistanceOfPVBlocksY": 100.0,
    "Height": 1.22,
    "TiltY": 20,
    "CentralAzimut": 180,
    "Hinge": "center",
    "RotationAxisNumber": 0,
    "TwoFacetsRelativePosition": 0,
    "DiffusersBetweenPanels": False,
    "DiffusersAtRowEnds": False,
    "DiffusersFillXAxis": True,
}


def test_static_data_and_writes_are_cwd_independent(monkeypatch, tmp_path):
    """Fast, offline check: shipped data readable and writes under cwd."""
    monkeypatch.chdir(tmp_path)

    lut = pd.read_csv(static_data_path('Igawa-5_sky_types_lut.csv'), sep=';')
    assert {'Kc', 'Cle', 'CIE Sky Type'} <= set(lut.columns)
    cie = pd.read_csv(static_data_path('CIE_standard_skies.csv'))
    assert {'Type', 'Gradation'} <= set(cie.columns)

    om = OutputsManager("anywhere", 2020, 2020)
    assert om.root == tmp_path
    om.save_json_to_cache("probe.json", {"ok": True})
    assert (tmp_path / "OUTPUTS" / "_cache" / "probe.json").exists()


@pytest.mark.network
@pytest.mark.skipif(os.environ.get("RUN_PASE_INTEGRATION", "").lower()
                    not in ("1", "true", "yes"),
                    reason="integration test, needs network access to PVGIS "
                           "(set RUN_PASE_INTEGRATION=1 to run)")
def test_light_chain_runs_from_any_cwd(monkeypatch, tmp_path):
    """Full light/PV chain executed from a directory outside the repo."""
    from pase.DATA_MANAGEMENT.weather_data_provider import (
        Weather_data, fetch_weather_from_pvgis)
    from pase.ENVIRONMENT.light import (
        Sun_positions, Sun_positions_sampled, Light, Ray_casting_scene)
    from pase.ENVIRONMENT.mesh import Mesh
    from pase.ENVIRONMENT.sky_model import ReinhartSky
    from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D
    from pase.PHOTOVOLTAICS.production import PV_Production

    lat, lon, year = 50.6, 5.6, 2020

    # User-data contract: the user places their INPUTS/ in the launch
    # directory. Provision the daily weather file the chain needs.
    weather_dir = tmp_path / "INPUTS" / "WEATHER_FILES"
    weather_dir.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "INPUTS" / "WEATHER_FILES"
                / "minimal_PRECIP_VP.csv", weather_dir)
    monkeypatch.chdir(tmp_path)
    before = _snapshot_outside_writes()

    raw_weather = fetch_weather_from_pvgis(lat, lon, year, year)
    wd = Weather_data(lat, lon, year, year, WD_option=1,
                      raw_weather=raw_weather,
                      daily_file="minimal_PRECIP_VP")

    freq = len(wd.nyears_data[str(year)])
    tz = "Etc/GMT+0"
    sun_samp = Sun_positions_sampled(lat, lon, 1, "anywhere", freq, tz)
    sun = Sun_positions(lat, lon, freq, tz)

    pv_3d = PV_Configuration_3D(PV_PARAMS, sun_samp.solar_vector,
                                visualization=False)

    mesh = Mesh()
    mesh.set_interest_zone_orientation(
        {"InterestZoneOrientationMode": "default"},
        {"CentralAzimut": PV_PARAMS["CentralAzimut"]})
    mesh.add_oriented_plane_ground_mesh(-25, 25, -25, 25, 5, 5, flag="crop")

    light = Light(wd.nyears_data, sun, "From weather data")

    rc = Ray_casting_scene(mesh=mesh, geometry=pv_3d,
                           discrete_sky=ReinhartSky(MF=1).reinhart_patches)
    rc.get_light_maps(sun_samp.solar_vector, visualization=False)
    rc.get_daily_irradiation_map(sun_samp.SP, light.data)

    pv_prod = PV_Production(PV_PARAMS)
    pv_prod.get_several_years_of_electricity_production(sun, light.data,
                                                        wd.nyears_data)
    prod = pv_prod.production[str(year)]
    assert prod["P_central"].notna().all()
    assert prod["P_central"].sum() > 0

    # Writes follow the cwd, never the package directory.
    om = OutputsManager("anywhere", year, year)
    assert om.root == tmp_path
    _assert_no_outside_writes(before)
