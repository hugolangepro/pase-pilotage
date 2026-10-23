#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import os

import logging
import numpy as np
import yaml

from pase.user_support_tools import PASE_Logger

logger = logging.getLogger(__name__)

VALID_TYPES = ['float', 'integer', 'string', 'boolean', 'list']

# Repetition distances whose limit check is superfluous when the governing count is <= 1
# (a repetition distance is only meaningful with more than one element along that axis).
# Maps each repetition-distance parameter to the count parameter that governs it.
CONDITIONAL_LIMIT_GOVERNORS = {
    'RepetitionDistanceOfPanelsX': 'NumberOfPanelsX',
    'RepetitionDistanceOfPanelsY': 'NumberOfPanelsY',
    'RepetitionDistanceOfPVBlocksX': 'NumberOfPVBlocksX',
    'RepetitionDistanceOfPVBlocksY': 'NumberOfPVBlocksY',
}

class YAML_Inputs_provider:
    
    def __init__(self, file=None, path='INPUTS', subpath=None, parentdir=None):
        if subpath is not None:
            if parentdir is not None:
                fname = os.path.join('..', '..', path, subpath, file)
            else:
                fname = os.path.join(path, subpath, file)
        else:
            if parentdir is not None:
                fname = os.path.join('..', '..', path, file)
            else:
                fname = os.path.join(path, file)


        with open (fname, 'r') as inputs_file:

            inputs = yaml.load(inputs_file, Loader=yaml.FullLoader)
            
        self.inputs = {}
   
        for key, data in inputs.items():

            if data['Type'] not in VALID_TYPES:
                msg = (f'Type not correctly defined for parameter {key} in file '
                       f'{inputs_file.name}. \nType was: {data["Type"]}'
                       f'\nType should be one of the '
                       f'following: {VALID_TYPES}.')
                raise ValueError(msg)

            if data['Value'] is not list:
                if data['Type'] == 'float':
                    self.check_value_float(key, data, inputs)
            
                elif data['Type'] == 'integer':
                    self.check_value_int(key, data, inputs)
                
                elif data['Type'] == 'string':
                    self.check_value_str(key, data, inputs)
                    
                elif data['Type'] == 'boolean':
                    self.check_value_bool(key, data, inputs)
                
                elif data['Type'] == 'list':
                    self.check_value_list(key, data, inputs)
        
        PASE_Logger('Input values from '+file+' have been imported successfully', 'INFO')

                
            
    def error_message(self, var_name=None, var_type=None, var_limit=None):
       
        if var_type is not None:        
            self.msg = 'Input "' + var_name + '" value should be a ' + str(var_type)        
        else:        
            self.msg = 'Input "' + var_name + '" value is outside the limits: ' + str(var_limit)
            
    
    def check_value_float(self, key, data, inputs):
        
        if (type(data['Value']) is not int) and (type(data['Value']) is not float):           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']
            
        self.check_limits(key, data, inputs)

        if 'Possibilities' in data:
            self.check_possibilities(key, data) 

                
    def check_value_int(self, key, data, inputs):
        
        if type(data['Value']) is not int:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']
            
        self.check_limits(key, data, inputs)

        if 'Possibilities' in data:
            self.check_possibilities(key, data)        


    def check_value_str(self, key, data, inputs):
            
        if type(data['Value']) is not str:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']    

        if 'Possibilities' in data:
            self.check_possibilities(key, data)            


    def check_value_bool(self, key, data, inputs):
            
        if type(data['Value']) is not bool:           
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value'] 

        if 'Possibilities' in data:
            self.check_possibilities(key, data) 

    
    def check_value_list(self, key, data, inputs):
        
        if type(data['Value']) is not list:
            self.error_message(key, data['Type'])
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = data['Value']

        if 'Possibilities' in data:
            self.check_possibilities(key, data)


    def check_possibilities(self, key, data):
        value = data['Value']
        possibilities = data['Possibilities']

        if not isinstance(possibilities, list):
            raise TypeError(f'Input "{key}": Possibilities must be a YAML list (use square brackets). '
                            f'Got {type(possibilities).__name__}: {possibilities!r}\n'
                            f'  Wrong:   Possibilities: a, b, c\n'
                            f'  Correct: Possibilities: [a, b, c]')

        if isinstance(value, str):
            value = value.strip().lower()
            normalized_possibilities = [p.lower() if isinstance(p, str) else p for p in possibilities]
        else:
            normalized_possibilities = possibilities

        if value not in normalized_possibilities:
            self.msg = (f'Input "{key}" value should be one of the following possibilities: '
                        f'{possibilities}, got: {data["Value"]}')
            PASE_Logger(self.msg, 'ERROR', 'value')
        else:
            self.inputs[key] = value


    def check_limits(self, key, data, inputs):

        # Skip the range check for a repetition distance when its governing count is <= 1:
        # with a single element the distance is geometrically unused, so an out-of-range value
        # is harmless and must not abort the run. The value is still stored.
        governor = CONDITIONAL_LIMIT_GOVERNORS.get(key)
        if governor is not None and governor in inputs:
            if inputs[governor]['Value'] <= 1:
                self.inputs[key] = data['Value']
                return

        ## In the case there is an input paramater that has the upper and lower limits
        ## that are other inputs value    
        #if ((type(data['Limit'][0]) is str) and (type(data['Limit'][1]) is str)):
        #    if ((data['Value']<inputs[data['Limit'][0]]['Value']) or 
        #        (data['Value']>inputs[data['Limit'][1]]['Value'])):               
        #        self.error_message(key, None, data['Limit'])
        #        PASE_Logger(self.msg, 'ERROR', 'value')
        #    else:
        #        i[key] = data['Value']

        if ((type(data['Limit'][0]) is str) and (type(data['Limit'][1]) is not str)):
            
            if '*' in data['Limit'][0]:
                factors = data['Limit'][0].split('*')
                if (data['Value']<(inputs[factors[0]]['Value']*inputs[factors[1]]['Value']) or
                    data['Value']>data['Limit'][1]):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                    
            elif '/' in data['Limit'][0]:
                factors = data['Limit'][0].split('*')
                if (data['Value']<(inputs[factors[0]]['Value']/inputs[factors[1]]['Value']) or
                    data['Value']>data['Limit'][1]):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                
            else:
                if data['Value']<inputs[data['Limit'][0]]['Value'] or data['Value']>data['Limit'][1]:                
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                   self.inputs[key] = data['Value']
    
        elif ((type(data['Limit'][0]) is not str) and (type(data['Limit'][1]) is str)):
            
            if '*' in data['Limit'][1]:
                factors = data['Limit'][1].split('*')
                if (data['Value']<data['Limit'][0] or
                    data['Value']>(inputs[factors[0]]['Value']*inputs[factors[1]]['Value'])):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                    
            elif '/' in data['Limit'][1]:
                factors = data['Limit'][1].split('*')
                if (data['Value']<data['Limit'][0] or
                    data['Value']>(inputs[factors[0]]['Value']/inputs[factors[1]]['Value'])):
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']

            else:
                if ((data['Value']<data['Limit'][0]) or (data['Value']>inputs[data['Limit'][1]]['Value'])):               
                    self.error_message(key, None, data['Limit'])
                    PASE_Logger(self.msg, 'ERROR', 'value')
                else:
                    self.inputs[key] = data['Value']
                
        else:
            if ((data['Value'] > float(data['Limit'][1])) or (data['Value'] < float(data['Limit'][0]))):
                self.error_message(key, None, data['Limit'])
                PASE_Logger(self.msg, 'ERROR', 'value')
            else:
                self.inputs[key] = data['Value']


class Inputs_aggregator:

    def __init__(self, inputs: list):
        self.aggregated_inputs = dict()

        self.aggregate_inputs(inputs)

        self.inputs_sanity_check()  # check validity of input parameters

    def aggregate_inputs(self, inputs):

        for input in inputs:
            self.aggregated_inputs.update(input)

    def inputs_sanity_check(self):
        self._check_panel_spacing()
        self._check_panel_ground_clearance()
        self._check_structure_ground_clearance()

    def _check_panel_spacing(self):
        """Check that panel repetition distances are not shorter than panel dimensions.

        The per-axis check is skipped when that axis holds a single panel
        (``NumberOfPanelsX``/``NumberOfPanelsY`` <= 1), since a lone panel cannot clip into a
        (non-existent) neighbour and its repetition distance is geometrically unused.
        """
        if self.aggregated_inputs['NumberOfPanelsX'] > 1 and \
                self.aggregated_inputs['RepetitionDistanceOfPanelsX'] < \
                self.aggregated_inputs['PanelDimensionX']:
            raise ValueError(
                "Repetition distance between panels in axis X is too short, "
                "panels are clipping into each other. Fix it in yaml config file.")

        if self.aggregated_inputs['NumberOfPanelsY'] > 1 and \
                self.aggregated_inputs['RepetitionDistanceOfPanelsY'] < \
                self.aggregated_inputs['PanelDimensionY']:
            raise ValueError(
                "Repetition distance between panels in axis Y is too short, "
                "panels are clipping into each other. Fix it in yaml config file.")

    def _check_panel_ground_clearance(self):
        """Check that the lowest panel edge clears the ground (strictly positive clearance)."""
        span_x = ((self.aggregated_inputs["NumberOfPanelsX"] - 1) * self.aggregated_inputs["RepetitionDistanceOfPanelsX"]
                  + self.aggregated_inputs["PanelDimensionX"])
        ground_clearance = (self.aggregated_inputs["Height"]
                            - span_x / 2 * np.sin(np.deg2rad(self.aggregated_inputs["TiltY"])))

        if ground_clearance <= 0:
            msg = (f"The current combination of NumberOfPanelsX, RepetitionDistanceOfPanelsX, PanelDimensionX, TiltY "
                   "and Height results in an invalid geometry where the panels would be partially underground.\n"
                   f"Current ground clearance: {ground_clearance:.3f} m (must be > 0). "
                   "Please revise the geometry of the central.")
            logger.error(msg)
            raise ValueError(msg)

    def _check_structure_ground_clearance(self):
        """Check that the lowest point of the PV structure clears the ground (strictly positive clearance).

        The lowest point is the tip of the lower rafter edge, reduced by the half-thickness of the
        purlin profile sitting beneath the rafter. The purlin characteristic dimension is computed
        following the same logic as PVStructure.get_characteristic_dim (pase/PHOTOVOLTAICS/structure.py).

        This check is skipped when no structure inputs are present or in the case of Agrivoltaic fence, since there
        is no upper part of the structure that could collide with the ground (as opposed to HSATS or PV table).
        """
        if 'RafterLength' not in self.aggregated_inputs:
            return

        # Characteristic half-dimension of the purlin cross-section
        # (mirrors PVStructure.get_characteristic_dim logic)
        purlin_shape = self.aggregated_inputs['PurlinShape'].lower()
        if purlin_shape == 'cylinder':
            purlin_dim = self.aggregated_inputs['PurlinRadius']
        elif purlin_shape == 'rectangle':
            purlin_dim = self.aggregated_inputs['PurlinHeight'] / 2
        elif purlin_shape == 'square':
            purlin_dim = self.aggregated_inputs['PurlinSide'] / 2
        else:
            purlin_dim = 0.0

        ground_clearance = (self.aggregated_inputs["Height"]
                            - self.aggregated_inputs["RafterLength"] / 2 * np.sin(np.deg2rad(self.aggregated_inputs["TiltY"]))
                            - purlin_dim)

        if ground_clearance <= 0:
            msg = (f"The current combination of RafterLength, TiltY, Height and PurlinShape results in "
                   "an invalid geometry where the structure would be partially underground.\n"
                   f"Current structure ground clearance: {ground_clearance:.3f} m (must be > 0). "
                   "Please revise the structure geometry.")
            logger.error(msg)
            raise ValueError(msg)
