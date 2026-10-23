#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

from datetime import datetime
import numpy as np

from pase.CROPS.SIMPLE.run_simple import run_independant_years_of_crop
from pase.CROPS.STICS.JAVASTICS.run_java_stics import run_independant_usms
from pase.CROPS.STICS.PYSTICS.run_pystics_from_PASE import run_independant_usms_in_pystics
from pase.CROPS.GRASSIM.run_grassim import run_grassim
from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization




def run_crop_simu(config, option_2D, WD, daily_irr, scenario_P):

    results = {}
        
    if config['CropModel'] == 'simple':
        Soil_plot, Crop_plot = run_independant_years_of_crop(config, option_2D, WD, daily_irr, 
                                                             scenario_P['Latitude'],
                                                             scenario_P['Altitude'])
        results = merge_results([Soil_plot, Crop_plot])
        
    if config['CropModel'] == 'stics':
        Crop_plot = run_independant_usms(config, WD, daily_irr, scenario_P)  
        results = Crop_plot.nyears_data      
        
    if config['CropModel'] == 'pystics':
        Crop_plot = run_independant_usms_in_pystics(config, WD, daily_irr, scenario_P)
        results = Crop_plot.nyears_data

    if config['CropModel'] == 'grassim':
        Soil_plot, Crop_plot, Management_plot = run_grassim(config, WD, daily_irr, scenario_P['Latitude'], scenario_P['Altitude'])
        results = merge_results([Soil_plot, Crop_plot, Management_plot])
    
    return results


def merge_results(objects):
    results = {}
    years = objects[0].nyears_data.keys()
    for year in years:
        merged_dict = {}
        for object in objects:
            merged_dict.update(object.nyears_data[year])
        results[year] = merged_dict
    return results


def visualize_map_of_a_variable(config, results, variable, scene_3D, meshes, year, MM_DD=np.nan, unit=''):
    """
    Visualize a specific spatialized variable in the 3D scene.

    Parameters
    ----------
    config : dict
        Dictionnary with the configuration parameters of the crop model
    results : dict
        Dictionnary with the output of the crop model
    variable : string
        Name of the variable to visualize.
    scene_3D : Pyvista Polydata
        3D scene as a pyvista polydata.
    meshes : Mesh object
        Mesh object containing the coordinates of the points of interest.
    year : int
        Year fo which results will be visualized.
    MM_DD : string
        Date as a format 'MM-DD'
    unit : string
        Unit of the variable to visualize.

    Returns
    -------
    None.

    """
    
    if type(scene_3D) == list:
        geo = scene_3D[0]
    else:
        geo = scene_3D
        
    if config['CropModel'] == 'simple':
        data = results[str(year)][variable][str(year)+'-'+MM_DD+' 00:00:00']
        
    if config['CropModel'] == 'grassim':
        data = results[str(year)][variable][datetime.strptime(str(year)+'-'+MM_DD+' 00:00:00', '%Y-%m-%d %H:%M:%S')]
        
    if config['CropModel'] == 'stics':
        data = results[str(year)][variable]

    if config['CropModel'] == 'pystics':
        data = results[str(year)][variable]

    open_pyvista_3D_visualization(meshes.sourcepoints[:,:],
                                  data, 
                                  geo,
                                  variable+' map '+ config['CropModel']+' '+ str(year)+'-'+MM_DD+' ['+unit+']')
