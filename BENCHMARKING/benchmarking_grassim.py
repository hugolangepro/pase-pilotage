#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Julien Philippart based on the main.py script of Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

'''This script is based on the main.py scripts to run simulations. Differences are :
- comparing simulation results to imported reference data
- computing performance indicators
- saving selected states variables (exported_BM, exported_N and exported_OM)
- saving metadata associated with the simulation (commit used, date, parameters used)'''

import sys
import os
from datetime import datetime
import numpy as np
import yaml
import subprocess
import pandas as pd
import pickle

# Set project root as working directory and defining and input path to be easy to use with yaml inputs provider
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # file BENCHMARKING/   NB : this command does not work in console because _file_ not found
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT_DIR, '..'))  # Remonte à pase/ -> root of project where the "main.py" is located
os.chdir(PROJECT_ROOT)

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider, Inputs_aggregator
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        get_cache_key,
                                                        Weather_data)
from pase.DATA_MANAGEMENT.OUTPUT.save_csv import save_mean_to_csv
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager
from pase.PHOTOVOLTAICS.configuration import PV_Configuration_3D
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.CROPS.run_crop_simulations import run_crop_simu, visualize_map_of_a_variable
from pase.DATA_MANAGEMENT.input_checker import InputsEvaluator
from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.DATA_MANAGEMENT.plots.generic_time_series import plot_variables
from pase.DATA_MANAGEMENT.benchmarking import save_simulation_metadata
PASE_Logger()

###############
# Load inputs #
###############
# Import of general parameters
Loc_1 = YAML_Inputs_provider(file='Example1_loc.yaml', subpath='SCENARIOS').inputs
# Import PV system and PV modules parameters
AV_1 = YAML_Inputs_provider(file='Example1_AV.yaml', subpath='AV_CENTRAL').inputs
PV_module_1 = YAML_Inputs_provider(file='PV_module_SigueSOL.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).inputs
crop_config = YAML_Inputs_provider(file='grassim_example.yml', subpath=os.path.join('CROPS', 'config')).inputs

# InputsEvaluator is there to safeguard computing time and memory usage by checking some parameters values
input_checker = InputsEvaluator(Loc_1, AV_1)

PV_params_dict = Inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs

om = OutputsManager(Loc_1['LocationName'],
                    Loc_1['SimulationStartingYear'],
                    Loc_1['SimulationEndingYear'])

variant_dir = om.setup_variant(loc=Loc_1,
                               av=AV_1,
                               pv_module=PV_module_1,
                               structure=dict(),  # pass empty dictionary
                               crop_config=crop_config)

cache_key = get_cache_key(Loc_1['Latitude'],
                          Loc_1['Longitude'],
                          Loc_1['SimulationStartingYear'],
                          Loc_1['SimulationEndingYear'])

##################
# Pre-processing #
##################
# Import of weather data and computation of daily weather data
lat = Loc_1['Latitude']
lon = Loc_1['Longitude']
start_year = Loc_1['SimulationStartingYear']
end_year = Loc_1['SimulationEndingYear']

raw_weather = om.load_or_fetch_weather(
    key=cache_key,
    fetch_fn=lambda: fetch_weather_from_pvgis(lat, lon, start_year, end_year)
)

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

# Initiation of the object containing points of interest to compute light
M = Mesh()

# Add of the points of interests on the ground for crop models
M.add_plane_ground_regular_meshes(Loc_1['Xmin_InterestZone'],
                                  Loc_1['Xmax_InterestZone'],
                                  Loc_1['Ymin_InterestZone'],
                                  Loc_1['Ymax_InterestZone'],
                                  Loc_1['dX_InterestZone'],
                                  Loc_1['dY_InterestZone'],
                                  flag="crop")

# Discrete sky model
discrete_sky = ReinhartSky(MF=Loc_1['MF']).reinhart_patches

# Computation of sun and light data
Light_instance = Light(WD.nyears_data, Sun_positions_complete, Loc_1['DiffuseSkyType'])

# Instantiation and run of light ray casting model (direct and diffuse) with points of interest and scene
L = Ray_casting_scene(mesh=M,
                      geometry=PV_1_3Dconfig.PV_central_PD,
                      discrete_sky=discrete_sky)

# Run light ray casting model (direct and diffuse) with points of interest and scene
L.get_light_maps(Sun_positions_samp.solar_vector,
                 visualization=False,
                 Sun_P_map_to_visualize=3)

# Integration of irradiation along days
L.get_daily_irradiation_map(Sun_positions_samp.SP, Light_instance.data,
                            visualization=True,
                            year=Loc_1['SimulationStartingYear'], julian_day=5)

L.visualize_direct_light_map(1)
L.visualize_diffuse_light_map(10)
L.visualize_daily_irrad_map(Loc_1['SimulationStartingYear'], 15)

##############
# Processing #
##############
# PV production model based on a geometric approach
PV_central = PV_Production(PV_params_dict)
PV_central.get_several_years_of_electricity_production(Sun_positions_complete, Light_instance.data, WD.nyears_data)

for _ in range(Loc_1['SimulationStartingYear'], Loc_1['SimulationEndingYear']+1):
    PV_prod = PV_central.production[str(_)]
    print(f'PV production for year {_}: {PV_prod["P_central"].sum():.2f} MW·h')

# CROP MODEL
#Temporary line, this parameter (option_2D) should be in SCENARIOS input files (general parameters)
option_2D = 1 # 0 if no spatialization and 1 for a spatialization of the crop model
agro_results = run_crop_simu(crop_config, option_2D, WD.nyears_daily_data,
                                     L.daily_irr_spat,
                                     Loc_1)

## Visualizing and saving results

if crop_config['CropModel'] == ('simple' or 'stics'):
    visualize_map_of_a_variable(crop_config, agro_results, 'Fresh_yield',
                                PV_1_3Dconfig.PV_central_PD, M, Loc_1['SimulationStartingYear'],
                                MM_DD='10-10', unit='g/m²')
    save_mean_to_csv('mean_data.csv', agro_results, ['Dry_yield', 'Biomass'])
else:
    visualize_map_of_a_variable(crop_config, agro_results,'BM',
                                PV_1_3Dconfig.PV_central_PD, M, Loc_1['SimulationStartingYear'],
                                MM_DD='10-10', unit='t/ha')
    save_mean_to_csv('mean_data_dates.csv', agro_results, ['BM','exported_BM','ST'])

    #choosing variables among variable_to_save.yml

###################################################
#Plots time series"
###################################################

plot_variables([agro_results], ['ST'], '2020-01-01', '2020-12-31')

#################################################################################
"""Functions to compute model performance index and save them in a csv file"""
#################################################################################

#importing observed data as a dataframe
path_csv_obs = os.path.join("BENCHMARKING", "OBSERVED_DATA", "data_observed_RGA_2017.csv")
observed_df= pd.read_csv(path_csv_obs,sep=";", decimal=',',parse_dates=['Date'])
print(observed_df)

#importing simulated data
#NB : I should use directly the dictionary agro_results and not the csv saved before but problem to isolate cut_dates
path_csv_sim = os.path.join("OUTPUTS", "mean_data_dates.csv")
simulated_df = pd.read_csv(path_csv_sim,sep=",", decimal='.',parse_dates=['Date'])
# Filter df2 to keep only dates present in df1 (matching dates, e.g. dates of cut)
simulated_df = simulated_df[simulated_df['Date'].isin(observed_df['Date'])]
print(simulated_df)

def evaluate_model_performance(simulated_df, observed_df, variables, output_file=None):
    """
    Compare simulated value of variables of interest with observed/reference values.
    Root mean square error - RMSE [unit of variable]
    Relative root mean square error - rRMSE [%]
    Normalized deviation - nd [-]
    Model efficiency - ef [-]

    Parameters:
    - simulated_df (pd.DataFrame): DataFrame containing simulated values (dates + variables)
    - observed_df (pd.DataFrame): DataFrame containing observed values (same dates + variables)
    - variables (list): List of variables to compare (ex: ['BM', 'exported_N', 'exported_digestibleOM'])
    - output_file (str, optional): Path to csv file to save results

    Returns:
    - pd.DataFrame: Metrics for each variable of interest
    """

    #Creating dictionary
    performance = []

    #Loop for each variable of interest. Condition to have them in both df simulated and observed.
    for var in variables:
        if var not in simulated_df.columns or var not in observed_df.columns:
            print(f"Variable '{var}' lacking in data. Ignored.")
            continue

        sim_values = simulated_df[var].values
        obs_values = observed_df[var].values

        if len(sim_values) != len(obs_values):
            raise ValueError(f"Different length for simulated and reference data for '{var}'.")

        n = len(obs_values)

        mean_obs = np.mean(obs_values)

        rmse=np.sqrt(np.mean((np.array(obs_values) - np.array(sim_values)) ** 2))
        rrmse = 100*(rmse / mean_obs)
        nd = (np.sum(obs_values) - np.sum(sim_values)) / np.sum(obs_values)
        ef_num = np.sum((obs_values - mean_obs)**2) - np.sum((sim_values - obs_values)**2)
        ef_den = np.sum((obs_values - mean_obs)**2)
        ef = ef_num / ef_den if ef_den != 0 else np.nan

        performance.append({
            "Variable": var,
            "RMSE": rmse,
            "RRMSE": rrmse,
            "ND": nd,
            "EF": ef
        })

    df_perf = pd.DataFrame(performance)

    #Saving in a csv file
    if output_file:
        df_perf.to_csv(output_file, index=False)
        print(f"Résultats enregistrés dans {output_file}")

    return df_perf

variables_to_compare = ['exported_BM', 'exported_N', 'exported_digestibleOM']
# Compute performance index and save them
result_df = evaluate_model_performance(simulated_df, observed_df, variables_to_compare, output_file=os.path.join('OUTPUTS','model_performance.csv'))

print(result_df)