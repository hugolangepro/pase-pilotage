#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 16:06:55 2023

@author: Roxane Bruhwyler
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
# from windrose import WindroseAxes 
from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.DATA_MANAGEMENT.weather_data_provider import Weather_data
from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.mesh import Plane_Ground_regular_meshes
from pase.ENVIRONMENT.light import show_light_map, Light_shade_scene
from pase.PHOTOVOLTAICS.photovoltaic_systems import PV_system
from pase.CROP.evapotranspiration import ET0_FAO56_PM, get_ETo_0D
from pase.ENVIRONMENT import Windbreak2D
from pase.DATA_MANAGEMENT import graphs


PASE_Logger()



Loc_1 = YAML_Inputs_provider(file='Chanco.yaml').i


WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName'])

Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])

#########################
# DEBUT DU NOUVEAU CODE #
#########################

#Modules necessaires pour la detection de fichier
import glob
import os

#Retourne une liste comprenant les fichiers repondant au masque "mask" situe dans le dossier "folder
def Get_Files(mask,folder = "INPUTS"):
    return glob.glob(folder + "/" + mask )


PV_List = Get_Files("PV_central*")

#Creation d'une liste comprenant les objets PV_Config
GeometryList = []
for PV in PV_List:
    GeometryList.append(PV_Configuration_3D(YAML_Inputs_provider(file=os.path.basename(PV)).i, Sun_positions_samp.solar_vector,
                                        visualization=False))
                        # !!!! Problem with rotation angle that are negative

#Creation d'une geometrie fusionnee avec les N geometries si N == 1 pas de boucle
Geometry = GeometryList[0].PV_central
if len(GeometryList)>1:
    for Geo in GeometryList[1:]:
        Geometry = Geometry + Geo.PV_central
        
Geometry.plot()



