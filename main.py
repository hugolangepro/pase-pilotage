#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import os

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import (YAML_Inputs_provider,
                                                       Inputs_aggregator)
from pase.DATA_MANAGEMENT.input_checker import InputsEvaluator
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager
from pase.DATA_MANAGEMENT.OUTPUT.save_csv import save_mean_to_csv
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        get_cache_key,
                                                        Weather_data)
from pase.PHOTOVOLTAICS.configuration import (PV_Configuration_3D,
                                              PVConfiguration3D)
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.CROPS.run_crop_simulations import (run_crop_simu,
                                             visualize_map_of_a_variable)

PASE_Logger()
# Import of general parameters
Loc_1 = YAML_Inputs_provider(file='Siguesol_loc.yaml', subpath='SCENARIOS').inputs
# Import PV system and PV modules parameters
AV_1 = YAML_Inputs_provider(file='AV_siguesol.yaml', subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='PV_module_SigueSOL.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).inputs
Structure = dict()  # no structure here yet
crop_config = YAML_Inputs_provider(file='pystics_example.yml', subpath=os.path.join('CROPS', 'config')).inputs

# Using Sky Types characterization while simulating an AV central with solar
# tracking is very computer intensive ; InputChecker asks the user to reconsider
input_checker = InputsEvaluator(Loc_1, AV_1)

PV_params_dict = Inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs

om = OutputsManager(Loc_1['LocationName'],
                    Loc_1['SimulationStartingYear'],
                    Loc_1['SimulationEndingYear'])

variant_dir = om.setup_variant(loc=Loc_1,
                               av=AV_1,
                               pv_module=PV_module_1,
                               structure=Structure,
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
PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict,
                                    Sun_positions_samp.solar_vector,
                                    visualization=True)  # !!!! Problem with rotation angle that are negative
# #  Add custom polydata, for example a cube (not yet compatible with the tracking)
# cube = pyv.Cube(center=(0, 0, 1.0), x_length=1.0, y_length=1.0, z_length=1.0)
# info_cube = {
#     "Type": "Obstacle",         # <- required
#     "Central": 0
# }
#
# # Add the cube
# oid_cube = PV_1_3Dconfig.add_custom_polydata(cube, info_cube, name="Custom")
# PV_1_3Dconfig.polydata_all_centrals().plot()

# Initiation of the object containing points of interest to compute light
M = Mesh()

# Parts to integer in a function that aims to use ray casting light model for PV panels production
# Still have to integer this in a user friendly way and to couple with eletricity production part
"""
PV_params_dictBis = PV_params_dict.copy()
PV_params_dictBis['PanelThickness'] = False
PV_1_3DconfigMeshTop = PV_Configuration_3D(PV_params_dictBis, Sun_positions_samp.solar_vector,
                                    visualization=False)
PV_params_dictBis["PanelDimensionZ"] = -0.1
PV_1_3DconfigMeshBot = PV_Configuration_3D(PV_params_dictBis, Sun_positions_samp.solar_vector,
                                    visualization=False)
M.Add_PV_Mesh(PV_1_3DconfigMeshTop.PV_central,flag = "TopPV", radius = 0.5)
M.Add_PV_Mesh(PV_1_3DconfigMeshBot.PV_central, flag = "BotPV", radius = 0.5)
#TopPoints = M.Get_SourcePoints_ByFlag('TopPV')
#BotPoints = M.Get_SourcePoints_ByFlag('BotPV')
#TopPointsBis = M.Get_SourcePoints(FlagId=[0])
#BotPointsBis = M.Get_SourcePoints(FlagId=[1])
#FlagIdTop = M.Get_FlagId_ByFlag("BotPV")
#print("The Bottom of the PV have the FlagID = " + str(FlagIdTop))
"""

# Interest Zone Orientation Mode
M.set_interest_zone_orientation(Loc_1, AV_1)

# Add of the points of interests on the ground for crop models
M.add_oriented_plane_ground_mesh(
    Loc_1['Xmin_InterestZone'],
    Loc_1['Xmax_InterestZone'],
    Loc_1['Ymin_InterestZone'],
    Loc_1['Ymax_InterestZone'],
    Loc_1['dX_InterestZone'],
    Loc_1['dY_InterestZone'],
    flag="crop"
)

#Activation of the ray castinf from a PV module of the central (this functionnalities is under construction)
#M.add_PV_mesh(PV_1_3Dconfig.PV_central_MB[3]) #(This will not work if you are with a PV system with a rotation axis)

# Discrete sky model
discrete_sky = ReinhartSky(MF=Loc_1['MF']).reinhart_patches

# Computation of sun and light data
Light_instance = Light(WD.nyears_data, Sun_positions_complete, Loc_1['DiffuseSkyType'])

# Instantiation of light ray casting model (direct and diffuse) with points of interest and scene
L = Ray_casting_scene(mesh=M,
                      geometry=PV_1_3Dconfig.PV_central_PD,
                      discrete_sky=discrete_sky)

# Run light ray casting model (direct and diffuse) with points of interest and scene
L.get_light_maps(Sun_positions_samp.solar_vector,
                 visualization=False,
                 Sun_P_map_to_visualize=3)

# Integration of irradiation along days
L.get_daily_irradiation_map(Sun_positions_samp.SP,
                            Light_instance.data,
                            visualization=True,
                            year=Loc_1['SimulationStartingYear'], julian_day=5)

L.visualize_direct_light_map(1)
L.visualize_diffuse_light_map(10)
L.visualize_daily_irrad_map(2005, 150)

#DiffuseGround = L.Get_diffuse_map_byFlag(Flags=["wheat","corn"])
#DirectGround = L.Get_direct_map_byFlag(Flags=["crop"])
"""
# Examples of visualisation for the direct light map, diffuse light map (sky view factor)
# and daily irradiation map. Those lines are for PV system with no rotation axis. 
j = 5 #day definition

open_pyvista_3D_visualization(M.sourcepoints[:,:-1], 
                L.dir_map[:,3], 
                PV_1_3Dconfig.PV_central_PD,
                "Direct map [-]")

open_pyvista_3D_visualization(M.sourcepoints[:,:-1], 
                np.array(L.diff_map,dtype=np.float32), 
                PV_1_3Dconfig.PV_central_PD,
                "Sky visibility map [-]")

open_pyvista_3D_visualization(M.sourcepoints[:,:-1], 
                L.daily_irr_spat['2008'][:,j], 
                PV_1_3Dconfig.PV_central_PD,
                "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")
"""



"""
# Examples of visualisation for the direct light map, diffuse light map (sky view factor)
# and daily irradiation map. Those lines are for PV system with ONE rotation axis. 
j = 5 #Julian day definition
sun_p = 5 #Index of the sun positions as it is in the Sun_positions_samp.SP attribute
show_light_map2(L.sourcepoints[:,:-1], 
                L.dir_map[:,sun_p], 
                PV_1_3Dconfig.PV_central_PD[sun_p],
                "Direct map [-]")

show_light_map2(L.sourcepoints[:,:-1], 
                np.array(L.diff_map[:,sun_p],dtype=np.float32), 
                PV_1_3Dconfig.PV_central_PD[sun_p],
                "Sky visibility map [-]")

show_light_map2(L.sourcepoints[:,:-1], 
                L.daily_irr_spat['2021'][:,j], 
                PV_1_3Dconfig.PV_central_PD[sun_p],
                "Total irradiation reaching the ground on the julian day "+str(j)+" [MJ/m²]")"
"""


# Example of visualisation of the meshes generate on both sides of the PV panels to compute light
"""
import pyvista
P = pyvista.Plotter()
P.add_mesh(PV_1_3Dconfig.PV_central_PD)
P.add_mesh(pyvista.PolyData(TopPoints[:,:-1]),color="blue")
P.add_mesh(pyvista.PolyData(BotPoints[:,:-1]),color="red")
P.show()
"""

# Method to compute the computational time of different parts of the model
"""
import time
start = time.time()
L.diffuse_map(180)
time1 = time.time() - start
print(time1)
start = time.time()
L.direct_map(Sun_positions_samp.solar_vector)
time2 = time.time() - start
print(time2)
"""

"""
#Example of a way to combine multiple configurations of PV rows and integration of a barrier 
#(Nicolas started to integrate the combination of mutpliple PV_central files in functions in the MaiBis.py)
#### TEMPORARY: EXAMPLE OF a .OBJ importation and merging with the PV panels and merge of the 2 PV polydata
import pyvista
reader = pyvista.get_reader('INPUTS/HARDWARE/STRUCTURES/gen_siguesol.obj')
structure = reader.read()

xrng = np.arange(1.08, 2.08, 2, dtype=np.float32)
yrng = np.arange(-1.54, -0.54, 2, dtype=np.float32)
zrng = np.arange(-3.3, -2.3, 2, dtype=np.float32)

x, y, z = np.meshgrid(xrng, yrng, zrng)    
GlobalMesh = pyvista.StructuredGrid(x, y, z)
structures = GlobalMesh.glyph(geom=structure, factor=0.001)
structures = structures.rotate_z(-AV_1['CentralAzimut'])

merged = PV_1_3Dconfig.PV_central_PD.merge(structures)
PV_1_3Dconfig.PV_central_PD.plot()
structures.plot()
merged.plot()
"""

# PV production model based on a geometric approach
PV_central = PV_Production(PV_params_dict)
PV_central.get_several_years_of_electricity_production(Sun_positions_complete, Light_instance.data, WD.nyears_data)


### CROP MODEL
#Temporary line, this parameter (option_2D) should be in SCENARIOS input files (general parameters)
option_2D = 1 # 0 pour pas de spatialisation et 1 pour une spatialisation du modèle de culture
agro_results = run_crop_simu(crop_config, option_2D, WD.nyears_daily_data,
                                     L.daily_irr_spat,
                                     Loc_1)


if crop_config['CropModel'] == 'simple':
    visualize_map_of_a_variable(crop_config, agro_results, 'Fresh_yield',
                                PV_1_3Dconfig.PV_central_PD, M, Loc_1['SimulationStartingYear'],
                                MM_DD='10-10', unit='g/m²')
    save_mean_to_csv('mean_data.csv', agro_results, ['Dry_yield', 'Biomass'])
elif crop_config['CropModel'] == 'grassim':
    visualize_map_of_a_variable(crop_config, agro_results,'BM',
                                PV_1_3Dconfig.PV_central_PD, M, Loc_1['SimulationStartingYear'],
                                MM_DD='10-10', unit='t/ha')
    save_mean_to_csv('mean_data.csv', agro_results, ['BM'])

else:
    visualize_map_of_a_variable(crop_config, agro_results,'Dry_yield',
                                PV_1_3Dconfig.PV_central_PD, M, 2006,
                                MM_DD='Harvest_day', unit='t/ha')
