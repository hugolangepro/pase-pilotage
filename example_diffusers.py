from datetime import datetime
import numpy as np
import os

from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization
from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from pase.DATA_MANAGEMENT.input_checker import InputsEvaluator
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        get_cache_key,
                                                        Weather_data)
from pase.PHOTOVOLTAICS.configuration import PVConfiguration3D
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.PHOTOVOLTAICS.diffuser import LenticularDiffuser
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager


PASE_Logger()

Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml', subpath='SCENARIOS').inputs
AV_1 = YAML_Inputs_provider(file='Example_diffuser_AV.yaml', subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='PV_module_SigueSOL.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).inputs
crop_config = YAML_Inputs_provider(file='grassim_example.yml', subpath=os.path.join('CROPS', 'config')).inputs
diffuser_config = YAML_Inputs_provider(file='dplenticular_3D 20 LPI UV-LF.yaml', subpath=os.path.join('HARDWARE', 'DIFFUSERS')).inputs
input_checker = InputsEvaluator(Loc_1, AV_1)

PV_params_dict = Inputs_aggregator([AV_1, PV_module_1,diffuser_config]).aggregated_inputs

om = OutputsManager(Loc_1['LocationName'],
                    Loc_1['SimulationStartingYear'],
                    Loc_1['SimulationEndingYear'])

variant_dir = om.setup_variant(loc=Loc_1,
                               av=AV_1,
                               pv_module=PV_module_1,
                               structure=dict(),
                               crop_config=crop_config,
                               source=__file__)

cache_key = get_cache_key(Loc_1['Latitude'],
                          Loc_1['Longitude'],
                          Loc_1['SimulationStartingYear'],
                          Loc_1['SimulationEndingYear'])

##################
# Pre-processing #
##################
# Import weather data and compute daily weather data
lat = Loc_1['Latitude']
lon = Loc_1['Longitude']
start_year = Loc_1['SimulationStartingYear']
end_year = Loc_1['SimulationEndingYear']

if Loc_1['WeatherDataOption'] == 1:
    raw_weather = om.load_or_fetch_weather(
        key=cache_key,
        fetch_fn=lambda: fetch_weather_from_pvgis(lat, lon, start_year, end_year)
    )
else:  # Weather data from csv file
    raw_weather=None

WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  raw_weather,
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName']
                  )

# Import sun positions, complete for the HDKR model and sampled for the direct light model
Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])
Sun_positions_complete = Sun_positions(Loc_1['Latitude'],
                                       Loc_1['Longitude'],
                                       len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                       Loc_1['TimeZone'])
# Creation of the 3D PV central
PV_1_3Dconfig = PVConfiguration3D()
PV_1_3Dconfig.create_regular_central(PV_params_dict)
PV_1_3Dconfig.visualize_simple()

M = Mesh()
M.set_interest_zone_orientation(Loc_1, AV_1)
M.add_oriented_plane_ground_mesh(Loc_1['Xmin_InterestZone'],
                                  Loc_1['Xmax_InterestZone'],
                                  Loc_1['Ymin_InterestZone'],
                                  Loc_1['Ymax_InterestZone'],
                                  Loc_1['dX_InterestZone'],
                                  Loc_1['dY_InterestZone'],
                                  flag="crop")

discrete_sky = ReinhartSky(MF=Loc_1['MF']).reinhart_patches

# Computation of sun and light data
Light_instance = Light(WD.nyears_data, Sun_positions_complete, Loc_1['DiffuseSkyType'])
Diffuser = LenticularDiffuser(AV_1['CentralAzimut'], PV_params_dict['TiltY'],
                              omega=PV_params_dict['half_aperture_angle'],
                              res=PV_params_dict['Resolution'])

L = Ray_casting_scene(mesh=M,
                      geometry=PV_1_3Dconfig,
                      discrete_sky=discrete_sky,
                      diffusers=Diffuser)

L.get_light_maps(Sun_positions_samp.solar_vector,
                 visualization=False,
                 Sun_P_map_to_visualize=3)

L.get_daily_irradiation_map(Sun_positions_samp.SP,
                            Light_instance.data,
                            visualization=True,
                            year=2005, julian_day=5)


L.visualize_daily_irrad_map(2015, 48)
L.visualize_diffuser_light_map(50, Sun_positions_samp.solar_vector)

