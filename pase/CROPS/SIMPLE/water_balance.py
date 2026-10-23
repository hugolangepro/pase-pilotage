#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

"""
Equations used were entirely taken from "Crop evapotranspiration - Guidelines for computing
crop water requirements - FAO Irrigation and drainage paper 56" (Allen. R, Pereira. L et al.,1998)
available at the following link:
<http://www.fao.org/3/x0490e/x0490e07.htm#latent%20heat%20of%20vaporization%20(l)>.
They are used to compute the referance evapotranspiration used to get the ARID index
in the SIMPLE crop model.
The ARID index was formulated using physiological principles
that are used in crop models to reduce growth when root water uptake is not adequate
to meet the transpiration demand of the atmosphere. It is explained in the paper:
Agricultural reference index for drought (ARID), Woli, Prem, Jones, James W.,
Ingram, Keith T. and Fraisse, Clyde W, 2012, Agronomy journal.
"""
# importation of public packages
import numpy as np

from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization

class Soil:
    
    def __init__(self, soil_par=None):
        
        self.params = soil_par
        self.init_soil()
        self.nyears_data = {}
        
    def initiate_one_year_data_dictionaries(self):
        
        self.dict_rain = {}
        self.dict_drain = {}
        self.dict_run_off = {}
        self.dict_ET0 = {}
        self.dict_transpi = {}
        self.dict_avlbl_water = {}
        
        self.data_dict = {}
        
    def fill_nyears_data_dict(self, year):
        
        self.data_dict['Rain'] = self.dict_rain
        self.data_dict['Deep_drain'] = self.dict_drain
        self.data_dict['Run_off'] = self.dict_run_off
        self.data_dict['ET0'] = self.dict_ET0
        self.data_dict['Transpi'] = self.dict_transpi
        self.data_dict['Avlbl_water'] = self.dict_avlbl_water
        
        self.nyears_data[year] = self.data_dict
        
    def init_soil(self):
        
        self.available_water_RZ_previousday = self.params['InitialAmountOfAvailableWater']
            
    def hydric_balance(self, rain, ET0, irrigation, day_index):
        
        transpiration = self.get_transpiration(ET0)
        surface_runoff = self.get_surface_runoff(rain)
        deep_drainage = self.get_deep_drainage(rain, irrigation, transpiration,
                                               surface_runoff)
        
        available_water_RZ = self.available_water_RZ_previousday + rain \
                + irrigation - transpiration - surface_runoff - deep_drainage
                
        self.available_water_RZ_previousday = available_water_RZ
        
        self.dict_rain[str(day_index)] = rain
        self.dict_drain[str(day_index)] = deep_drainage
        self.dict_run_off[str(day_index)] = surface_runoff
        self.dict_ET0[str(day_index)] = ET0
        self.dict_transpi[str(day_index)] = transpiration
        self.dict_avlbl_water[str(day_index)] = available_water_RZ           
        
    def get_transpiration(self, ET0):
        
        generic_root_water_uptake_constant = 0.096   # maximum fraction of available water extracted by root in a day
        transpi = np.minimum(generic_root_water_uptake_constant
                             *self.available_water_RZ_previousday, ET0)

        return transpi
    
    def get_surface_runoff(self, rain):

        potential_maximum_retention = (25400/self.params['RunoffCurveNumber'])-254
        initial_abstraction = 0.2*potential_maximum_retention

        if rain <= initial_abstraction :
            surface_runoff = 0
        else :
            surface_runoff = ((rain-initial_abstraction)**2)\
            /(rain-initial_abstraction+potential_maximum_retention)

        return surface_runoff
    
    def get_deep_drainage(self, rain, irrig, transpi, surf_runoff):

        available_water_before_drainage = self.available_water_RZ_previousday\
                                          + rain + irrig - transpi - surf_runoff
        
        if type(available_water_before_drainage) is np.float64:
            if self.params['WaterHoldingCapacity'] >= (available_water_before_drainage/self.params['RootZoneDepth']) :
                deep_drainage = 0
            else :
                deep_drainage = self.params['DrainageCoeff']*self.params['RootZoneDepth']\
                    *((available_water_before_drainage/self.params['RootZoneDepth'])
                      -self.params['WaterHoldingCapacity'])
        else:
            deep_drainage = np.zeros(len(available_water_before_drainage))
            ind = np.where(self.params['WaterHoldingCapacity'] < (available_water_before_drainage/self.params['RootZoneDepth']))
            deep_drainage[ind] = self.params['DrainageCoeff']*self.params['RootZoneDepth']\
                    *((available_water_before_drainage[ind]/self.params['RootZoneDepth'])
                      -self.params['WaterHoldingCapacity'])         

        return deep_drainage
    
    def visualize_map_of_a_variable(self, variable, scene_3D, meshes, year, MM_DD=None, unit=''):
        """
        Visualize a specific spatialized variable in the 3D scene.

        Parameters
        ----------
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
        
        open_pyvista_3D_visualization(meshes.sourcepoints[:,:-1], 
                                      self.nyears_data[str(year)][variable][str(year)+'-'+MM_DD+' 00:00:00'], 
                                      geo,
                                      variable+' map SIMPLE '+str(year)+'-'+MM_DD+' ['+unit+']')
