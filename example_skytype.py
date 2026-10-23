#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#This file is part of the PASE software, and is distributed under the MIT license.

# Example script: runs the program up to get_daily_sky_type and prints the result.
# weather data is fetched from PVGIS

import os

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.DATA_MANAGEMENT.weather_data_provider import fetch_weather_from_pvgis, Weather_data
from pase.ENVIRONMENT.light import Sun_positions, Light

PASE_Logger()

###############
# Load inputs #
###############
Loc_1 = YAML_Inputs_provider(file='Example1_loc.yaml', subpath='SCENARIOS').inputs

lat        = Loc_1['Latitude']
lon        = Loc_1['Longitude']
start_year = Loc_1['SimulationStartingYear']
end_year   = Loc_1['SimulationEndingYear']
timezone   = Loc_1['TimeZone']

###################
# Weather data    #
###################
print("Fetching weather data from PVGIS ...")
raw_weather = fetch_weather_from_pvgis(lat, lon, start_year, end_year)

WD = Weather_data(
    lat,
    lon,
    start_year,
    end_year,
    WD_option=1,                    #PVGIS
    raw_weather=raw_weather,
    file=Loc_1['WeatherFileName'],
    daily_file=Loc_1['DailyWeatherFileName']
)

###################
# Sun positions   #
###################
print("Computing sun positions ...")
freq_deter = len(WD.nyears_data[str(start_year)])

SP = Sun_positions(lat, lon, freq_deter, timezone)

###################
# Light / sky     #
###################
print("Computing per-timestep CIE sky types ...")
light = Light(
    WD.nyears_data,
    SP,
    sky_type_source='From weather data'
)

###################
# Results         #
###################
print("\n--- Daily CIE Sky Type ---")
for year, daily_series in light.daily_sky_type.items():
    print(f"\nYear {year}  ({len(daily_series)} days)")
    print(daily_series.to_string())
