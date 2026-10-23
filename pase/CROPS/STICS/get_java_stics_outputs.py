#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import numpy as np
from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization

class Crop_outputs:
    
    def __init__(self):
        
        self.nyears_data = {}
        
    def initiate_one_year_variables(self, n_positions):
        
        self.dict_variables_one_year = {}
        self.np_fresh_yield = np.zeros(n_positions)
        self.np_dry_yield = np.zeros(n_positions)
        self.np_total_ET = np.zeros(n_positions)
        
    def fill_np_variables_for_each_position(self, position, fresh_yield, dry_yield,
                                            total_ET):
        
        self.np_fresh_yield[position] = fresh_yield
        self.np_dry_yield[position] = dry_yield
        self.np_total_ET[position] = total_ET
        
    def fill_dict_variables_for_each_year(self, year):
        
        self.dict_variables_one_year['Fresh_yield'] = self.np_fresh_yield
        self.dict_variables_one_year['Dry_yield'] = self.np_dry_yield
        self.dict_variables_one_year['Total_ET'] = self.np_total_ET
        
        self.nyears_data[year] = self.dict_variables_one_year


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
                                      self.nyears_data[str(year)][variable], 
                                      geo,
                                      variable+' map STICS at harvest in '+str(year)+' ['+unit+']')
    
