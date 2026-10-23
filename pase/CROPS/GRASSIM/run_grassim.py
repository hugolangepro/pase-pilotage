# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Louis Lemaire (Louis.Lemaire@uliege.be)
#This file is part of the PASE software, and is distributed under the MIT license.

import os
import pandas as pd
import yaml
from pase.CROPS.GRASSIM.plants.plants import Plants
from pase.CROPS.GRASSIM.soil.soil import Soil
from pase.CROPS.GRASSIM.management.management import Management
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.CROPS.evapotranspiration_FAO56_PM import get_ET0

def run_grassim(config, WD, daily_irr, lat, alt):
    """
    Run the GRASSIM model.

    Args:
        config: dictionary of configuration filenames
        WD: dictionary of daily weather data
        daily_irr: dictionary of daily irradiance [MJ/m²]
        lat: latitude [°] for ET0 computation
        alt: altitude [m] for ET0 computation
    """

    soil_init = YAML_Inputs_provider(file=f"CROPS/GRASSIM/soil/{config['SoilInit']}").inputs
    soil_hydraulic_properties = pd.read_csv(f"INPUTS/CROPS/GRASSIM/soil/{config['SoilHydraulicProperties']}",header=0, sep=";", decimal='.')
    soil_parameters=YAML_Inputs_provider(file=f"CROPS/GRASSIM/soil/{config['SoilParameters']}").inputs
    crop_init = YAML_Inputs_provider(file=f"CROPS/GRASSIM/crop/{config['CropInit']}").inputs
    kc_values = YAML_Inputs_provider(file=f"CROPS/GRASSIM/crop/{config['Kc_values']}").inputs
    pft_composition = YAML_Inputs_provider(file=f"CROPS/GRASSIM/crop/{config['PFT_composition']}").inputs
    pft_values = pd.read_csv(f"INPUTS/CROPS/GRASSIM/crop/{config['PFT_values']}",header=0, sep=";", decimal='.')
    management = YAML_Inputs_provider(file=f"CROPS/GRASSIM/management/{config['Management']}").inputs

    with open(f"INPUTS/CROPS/GRASSIM/{config['VariablesToSave']}", "r") as file:
        variables_to_save = yaml.safe_load(file)

    simulation_dates = get_sim_dates(WD)

    grid = get_grid_shape(daily_irr)
    soil = Soil(grid=grid, inits=soil_init, soil_parameters=soil_parameters,soil_properties= soil_hydraulic_properties,variables_to_save=variables_to_save['soil_variables'])
    crop = Plants(grid=grid, pft_composition=pft_composition, inits=crop_init, kc_values=kc_values, pft_values=pft_values, variables_to_save=variables_to_save['crop_variables'])
    management = Management(grid=grid, config=management, variables_to_save=variables_to_save['management_variables'])

    for year in simulation_dates.keys():
        for day in simulation_dates[year]:
            day_irr = daily_irr[year][:,day.dayofyear-1]
            ET0 = get_ET0(WD[year]['Avg_temp'][day],
                                WD[year]['Min_temp'][day],
                                WD[year]['Max_temp'][day],
                                WD[year]['Avg_WS_2m'][day],
                                WD[year]['Vap_press'][day],
                                day_irr,
                                crop.LAI,
                                day.day_of_year,
                                len(WD[year]['Avg_temp']),
                                lat,
                                alt,
                                soil.albedo)

            run_daily_loop(day, ET0, WD[year].loc[day], day_irr, soil, crop, management)

    return soil, crop, management


def run_daily_loop(day, ET0, WD, day_irr, soil, crop, management):
    """
    Run the daily loop.

    Args:
        day: datetime object
        ET0: potential evapotranspiration [mm]
        WD: weather data
        day_irr: numpy array of today's spatialized irradiance [MJ/m²]
        soil: soil object
        crop: crop object
        management: management object
    """

    crop.init_daily_loop(day=day, WD=WD, ET0=ET0, day_irr=day_irr)
    soil.init_daily_loop(day=day)
    management.init_daily_loop(day=day, crop=crop, soil=soil)
    # computation sequence : equivalent of grassim.py
    crop.compute_aet() # Uses Kc (BMGV in the future), needed for soil water balance
    crop.compute_potential_growth()

    crop.compute_st(method='T_fixed')
    crop.compute_fAge() # need st, used for SEN & ABS
    crop.compute_senescence_abscission()
    crop.compute_N_plant_litter()

    crop.compute_fT()
    crop.compute_fPARi()
    crop.compute_fW(W=soil.W,method='Jouven2006')
    crop.compute_N_supply(Nmin=soil.Nmin, FNAmax=soil.FNAmax, NSc=soil.NSc)
    crop.compute_fN()
    crop.compute_N_demand()
    crop.compute_N_uptake()
    crop.compute_N_plant_litter()
    crop.compute_environmental_stress() # fPAR*fT*fWfN, used for GRO
    crop.compute_seasonal_effect() # need st, used for GRO

    crop.compute_actual_growth()
    crop.update_balance() # update BM compartments, OMD, sward height, age, based on actual growth

    soil.compute_water_balance(PP=crop.PP, AET=crop.AET,method='Ruelle2018')
    soil.compute_N_mineralization(Temp=crop.Temp,method='Ruelle2018') # parameters for soil activity (Ruelle et al., 2018)
    soil.compute_N_immobilization(Temp=crop.Temp,method='Ruelle2018')
    soil.compute_N_leached(method='Ruelle2018')
    soil.compute_N2O_emissions()
    soil.compute_N_from_rain(crop.PP)
    soil.compute_Norg(percentageofNmin=management.percentageofNmin, N_plant_litter=crop.N_plant_litter, fert_org=management.fert_org)
    soil.compute_Nmin(percentageofNmin=management.percentageofNmin, NH3volatfactor=management.NH3volatfactor, N_uptake=crop.N_uptake, fert_org=management.fert_org, fert_min=management.fert_min)

    crop.save_variables()
    soil.save_variables()
    management.save_variables()


def get_sim_dates(weather_data):
    """
    Get the simulation dates.

    Args:
        weather_data: Weather_data object from weather_data_provider

    Returns:
        simulation_dates: list of simulation days
    """
    simulation_dates = {}

    for year in weather_data.keys():
        simulation_dates[year] = []
        for day in weather_data[year].index:
            simulation_dates[year].append(day)

    return simulation_dates


def get_yaml_params(filename):
    """
    Get the parameters from a YAML file.

    Args:
        filename: string of the filename

    Returns:
        parameters: dictionary of parameters
    """
    return YAML_Inputs_provider(file=filename).inputs


def get_grid_shape(daily_irradiance):
    """
    Get the shape of the grid.

    Args:
        daily_irradiance: dictionary of daily irradiance [MJ/m²]

    Returns:
        grid_shape: shape of the grid
    """
    return daily_irradiance[next(iter(daily_irradiance))].shape[0]
