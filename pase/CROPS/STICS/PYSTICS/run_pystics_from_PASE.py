#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2025 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import os
import subprocess
import platform
import pandas as pd
import numpy as np

from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.CROPS.STICS.generate_java_stics_files import \
    generate_weather_data_file, generate_USMS_file
from pase.CROPS.STICS.get_java_stics_outputs import Crop_outputs


def run_independant_usms_in_pystics(config, WD, daily_irr, scenario_P):
    
    Simu_init = YAML_Inputs_provider(f"CROPS/pySTICS/{config['SimuInit']}").inputs
    
    # ============== [HUGO - FIX STICS] ==============
    # BUG PASE 2.0 : la meteo par position etait ecrite dans 'example/' mais relue
    # dans 'pase/' (ligne parametrization_from_stics_example_files(..., work_directory='pase'))
    # -> FileNotFoundError. On ecrit desormais dans 'pase/' (le repertoire de travail,
    # ou sont aussi ecrits les USMS et lus les fichiers STICS).
    WD_files_dict = generate_weather_data_file(WD, daily_irr,
                                               scenario_P['LocationName'],
                                               'pase/CROPS/STICS/PYSTICS/pySTICS/pystics/parametrization_files/pase/')
    # ============== [HUGO - FIX STICS] FIN ==============
    
    Crop_plot = Crop_outputs()
    
    for year, WD_files_positions in WD_files_dict.items():
        
        n_positions = len(daily_irr[str(scenario_P['SimulationStartingYear'])][:,0])
        Crop_plot.initiate_one_year_variables(n_positions)        
        
        if (int(year) == scenario_P['SimulationStartingYear'] 
            and Simu_init['AnnualCropOption'] == 0):         # If bisannual crop and first year of simulation, crop development can not be computed as it was sown on the previous year
            pass
        
        else:                 
            
            count = 0                               
            for WD_file in WD_files_positions:
                
                if Simu_init['AnnualCropOption'] == 0:
                    WD_file_previous_year = WD_files_dict[str(int(year)-1)][count]
                else:
                    WD_file_previous_year = WD_file
                
                # Write the usms file containing this unit of simulation (for one position of one year)
                generate_USMS_file(WD_file, WD_file_previous_year,
                                   Simu_init, year, 'pase/CROPS/STICS/PYSTICS/pySTICS/pystics/parametrization_files/pase/')
                
                os.chdir("pase/CROPS/STICS/PYSTICS/pySTICS")
                
                from pystics.params import parametrization_from_stics_example_files
                from pystics.simulation import run_pystics_simulation
                
                # Read input files from pystics/parametrization_files/example folder for the USM associated to chosen species and variety
                weather, crop, manage, soil, station, constants, initial = parametrization_from_stics_example_files(WD_file, Simu_init['Variety'], work_directory='pase')
                ## !! WARNING: check ETP calculation parameter !!!! To do this, set it to 2.
                # Run the simulation
                pystics_df, pystics_mat_list = run_pystics_simulation(weather, crop, soil, constants, manage, station, initial)
                
                Fresh_yield = np.nan
                Dry_yield = max(pystics_df['mafruit'])
                Total_ET = sum(pystics_df['et'])
                
                Crop_plot.fill_np_variables_for_each_position(count, Fresh_yield,
                                                              Dry_yield, Total_ET)
                count+=1    
                
                os.chdir("../../../../..")
                
            Crop_plot.fill_dict_variables_for_each_year(year)
                
    return Crop_plot
        
