import pytest
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.ENVIRONMENT.light import Sun_positions, Light
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        Weather_data)
import yaml
from pathlib import Path
import pandas as pd

@pytest.fixture
def default_PV_Central():
    default_param_dict = {
        "Bifaciality": False,
        "Bifaciality_factor": 1,
        "CentralAzimut": 90,
        "Panel_Peak_Power": 400,
        "PanelDimensionX": 2.384,
        "PanelDimensionY": 1.303,
        "NumberOfPanelsX": 1,
        "NumberOfPanelsY": 16,
        "NumberOfPVBlocksX": 14,
        "NumberOfPVBlocksY": 1,
        "RotationAxisNumber": 0,
        "TiltY": 180,
        "RepetitionDistanceOfPanelsX": 2.45,
        "RepetitionDistanceOfPVBlocksX": 1.31,
    }
    default_PV_Central = PV_Production(default_param_dict)
    return default_PV_Central
@pytest.fixture
def default_series_input():
    default_parameters={
        'Latitude': 50.565114,
        'Longitude': 4.702089,
        'SimulationStartingYear': 2020,
        'SimulationEndingYear': 2020,
        'WeatherDataOption': 1,
        'WeatherFileName': 'Chanco_Chile_WD',
        'DailyWeatherFileName': 'minimal_PRECIP_VP',
        'DiffuseSkyType': 'From weather data',
        'TimeZone': 'Etc/GMT+0',
    }

    lat = default_parameters['Latitude']
    lon = default_parameters['Longitude']
    start_year = default_parameters['SimulationStartingYear']
    end_year = default_parameters['SimulationEndingYear']
    raw_weather = fetch_weather_from_pvgis(lat, lon, start_year, end_year)
    default_WD = Weather_data(
        lat,
        lon,
        start_year,
        end_year,
        default_parameters['WeatherDataOption'],
        raw_weather,
        default_parameters['WeatherFileName'],
        default_parameters['DailyWeatherFileName']
        )
    default_Sun_positions = Sun_positions(
        lat,
        lon,
        len(default_WD.nyears_data[str(start_year)]),
        default_parameters['TimeZone'])
    default_Light = Light(default_WD.nyears_data, default_Sun_positions,
                      default_parameters['DiffuseSkyType'])
    return default_Sun_positions,default_Light,default_WD

@pytest.mark.network
@pytest.mark.parametrize("AlbedoOptionAndName",
                         [(1,"Non_existant_file_to_test_function_call"),
                          (2,"albedo_colza")]
                         )
def test_get_several_years_of_electricity_production(default_PV_Central,
                                                AlbedoOptionAndName,
                                                default_series_input):
    default_Sun_positions,default_Light,default_WD=default_series_input
    # Using a PV central facing down (tilt=180) so direct component is null
    # Using no diffuse component in light data so diffuse component is null
    default_WD.nyears_data['2020']['G(h)']=100
    default_WD.nyears_data['2020']['Gb(n)'] = 100
    default_WD.nyears_data['2020']['Gd(h)'] = 0
    # Using Ai=1 so diffuse component is null
    default_Light.data['2020'].Ai=1
    # Using constant GHI, which means constant GHI reaching ground
    default_Light.data['2020'].GHI=100
    # front panel GTI is constant except for albedo
    default_PV_Central.get_several_years_of_electricity_production(
        default_Sun_positions,
        default_Light.data,
        default_WD.nyears_data,
        AlbedoOptionAndName[1],
        AlbedoOptionAndName[0])
    assert min(default_Light.data.keys())=='2020'
    assert max(default_Light.data.keys()) == '2020'
    if AlbedoOptionAndName[0]==1:
        assert default_PV_Central.production['2020'].GTI_f.nunique() == 1, \
            "front GTI is not constant for constant GHI and only reflected " \
            "component for GTI. Albedo might be variable when " \
            "AlbedoDataOption is 1"
    if AlbedoOptionAndName[0]==2:
        assert default_PV_Central.production['2020'].GTI_f.nunique() >1,             \
            "GTI front is constant, Albedo is likely constant and " \
            "AlbedoDataOption is 2"

@pytest.mark.network
@pytest.mark.parametrize("freq", ["h", "15min"])
def test_get_several_years_of_electricity_production_nominal(default_PV_Central,freq):
    albedo=default_PV_Central.get_n_years_albedo_from_csvfile(
        "albedo_colza",
        '2020',
        '2020',
        freq,
        0.25)

    assert isinstance(albedo, dict)
    assert "2020" in albedo
    assert isinstance(albedo["2020"], pd.DataFrame)
    assert "Albedo" in albedo["2020"].columns

    albedo2020 = albedo["2020"]["Albedo"]
    assert "2020-01-01 00:00" in albedo2020.index,\
        "Starting date '2020-01-01 00:00' not in albedo_colza series."
    assert albedo2020["2020-01-01 00:00"]==0.18,\
        (f"Incorrect value for '2020-01-01 00:00' : got "
         f"={albedo2020['2020-01-01 00:00']}, expected=0.26535534")
    assert albedo2020["2020-03-28 16:00"]==0.26535534,\
        (f"Incorrect value for '2020-03-28 16:00' : got={albedo2020['2020-03-28 16:00']},"
         f" expected=0.26535534")
    assert albedo2020.notna().all(), (f"The series contains NaN values: NaN "
                                      f"{albedo2020[albedo2020.isna()].index.tolist()}")

    if freq=="15min":
        assert "2020-12-31 23:45" in albedo2020.index, \
            "End timestamp '2020-12-31 23:45' not in " \
            "albedo_colza series."
    elif freq=="h":
        assert "2020-12-31 23:00" in albedo2020.index, \
            "End timestamp '2020-12-31 23:00' not in albedo_colza series."

@pytest.mark.network
def test_get_several_years_of_electricity_production_hors_periode(default_PV_Central):
    albedo=default_PV_Central.get_n_years_albedo_from_csvfile(
        "albedo_colza",
        '2021',
        '2021',
        'h',
        0.25)

    assert isinstance(albedo, dict)
    assert "2021" in albedo
    assert isinstance(albedo["2021"], pd.DataFrame)
    assert "Albedo" in albedo["2021"].columns

    albedo2021 = albedo["2021"]["Albedo"]
    assert albedo2021.nunique() == 1, \
        f"Series is not constant: {albedo2021.unique()}"
    assert "2021-01-01 00:00" in albedo2021.index,\
        "Start timestamp '2021-01-01 00:00' not in albedo_colza series."
    assert "2021-12-31 23:00" in albedo2021.index, \
        "End timestamp '2021-12-31 23:00' not in albedo_colza series."
    assert albedo2021.notna().all(),\
        (f"The series contains NaN values: NaN :"
         f"{albedo2021[albedo2021.isna()].index.tolist()}")

def test_csv_file_matches_format():
    yaml_path = (
        Path(__file__).resolve()
        .parents[2]
        / "INPUTS"
        / "SCENARIOS"
        / "Example_albedo.yaml"
    )
    assert yaml_path.exists(), f"YAML file not found at {yaml_path}"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert ('AlbedoDataOption' in data.keys()), f"AlbedoDataOption not " \
                                                f"in {yaml_path}"
    if data['AlbedoDataOption']['Value']==2:
        name_csv_file=data['AlbedoFileName']['Value']

        csv_path = (
                Path(__file__).resolve()
                .parents[2]
                / "INPUTS"
                / "CROPS"
                / str(name_csv_file + ".csv")
        )
        csv_data = pd.read_csv(csv_path, delimiter=',|;', engine='python')
        expected_columns = {
            "date",
            "Albedo"
        }
        csv_columns = csv_data.columns
        missing = expected_columns - set(csv_columns)
        extra = set(csv_columns) - expected_columns
        assert not missing, f"Missing keys in YAML: {missing}"
        assert not extra, f"Unexpected keys in YAML: {extra}"
