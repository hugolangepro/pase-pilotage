#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
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


def run_independant_usms(config, WD, daily_irr, scenario_P):
    
    Simu_init = YAML_Inputs_provider(f"CROPS/STICS/{config['SimuInit']}").inputs
    
    WD_files_dict = generate_weather_data_file(WD, daily_irr,
                                               scenario_P['LocationName'],
                                               'INPUTS/CROPS/STICS/param_files/')
    
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
                
                generate_USMS_file(WD_file, WD_file_previous_year,
                                   Simu_init, year, 'INPUTS/CROPS/STICS/param_files/')
                
                os.chdir("INPUTS/CROPS/STICS") #Mettre le chemin d'accès avant l'exécutable pour ne pas devoir naviguer dans les dossiers.

                if platform.system() == "Linux" or platform.system() == "Darwin":
                    subprocess.call(["java", "-jar","JavaSticsCmd.exe",
                                     "--run", "param_files", WD_file])
                else : 
                    subprocess.call(["JavaSticsCmd.exe", "--run", "param_files",
                                     WD_file], shell=True)
                
                
                daily_results_stics = pd.read_csv('param_files/mod_s'+WD_file+'.sti', sep=';', decimal='.')
                daily_results_stics['jul_day'] = daily_results_stics['jul']
                nd_year = max(daily_results_stics['ian'])
                st_year = min(daily_results_stics['ian'])
                if st_year%4==0:
                    supp_day = 1
                else:
                    supp_day = 0
                    
                if Simu_init['AnnualCropOption'] == 0:
                    daily_results_stics.loc[daily_results_stics['ian']
                                                   ==nd_year, 'jul_day'] = (daily_results_stics.loc[daily_results_stics['ian']==nd_year, 'jul_day'] 
                                                                                         + 365 + supp_day)
                else:
                    pass
                harvest_jul_day = max(daily_results_stics['irecs'])
                sowing_jul_day = min(daily_results_stics['iplts'])

                daily_results_stics = daily_results_stics.set_index('jul_day')

                Fresh_yield = float(daily_results_stics.loc[daily_results_stics.index==harvest_jul_day, 'pdsfruitfrais'])
                H2Ocontent_fruit = float(daily_results_stics.loc[daily_results_stics.index==harvest_jul_day, 'H2Orec'])
                Dry_yield = float(daily_results_stics.loc[daily_results_stics.index==harvest_jul_day, 'mafruit'])
                Total_ET = sum(daily_results_stics.loc[(daily_results_stics.index<=harvest_jul_day) & 
                                                       (daily_results_stics.index>=sowing_jul_day), 'et'])
                
                Crop_plot.fill_np_variables_for_each_position(count, Fresh_yield,
                                                              Dry_yield, Total_ET)
                
                count+=1
                
                os.chdir("../../..")
                
                """os.chdir("..")
                os.chdir("..")"""
                
            Crop_plot.fill_dict_variables_for_each_year(year)
    
    
    return Crop_plot
        
