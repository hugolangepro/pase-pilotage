import pytest

from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.DATA_MANAGEMENT.weather_data_provider import (
    Weather_data,
    get_cache_key,
    fetch_weather_from_pvgis,
)
from pase.ENVIRONMENT.light import Sun_positions, Light


@pytest.fixture(scope="session")
def light_fixture():
    loc = YAML_Inputs_provider(file="Siguesol_loc.yaml", subpath="SCENARIOS").inputs

    om = OutputsManager(
        loc["LocationName"],
        loc["SimulationStartingYear"],
        loc["SimulationEndingYear"],
    )
    om.setup_variant(
        loc,
        av={},
        pv_module={},
        structure={},
        crop_config={"CropModel": ""},
        source=__file__,
    )

    lat = loc["Latitude"]
    lon = loc["Longitude"]
    start_year = loc["SimulationStartingYear"]
    end_year = loc["SimulationEndingYear"]

    cache_key = get_cache_key(lat, lon, start_year, end_year)
    raw_weather = om.load_or_fetch_weather(
        key=cache_key,
        fetch_fn=lambda: fetch_weather_from_pvgis(lat, lon, start_year, end_year),
    )

    wd = Weather_data(
        lat,
        lon,
        start_year,
        end_year,
        loc["WeatherDataOption"],
        raw_weather,
        loc["WeatherFileName"],
        loc["DailyWeatherFileName"],
    )

    sun = Sun_positions(
        lat,
        lon,
        len(wd.nyears_data[str(start_year)]),
        loc["TimeZone"],
    )

    return Light(wd.nyears_data, sun)
