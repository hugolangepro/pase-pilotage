#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import numpy as np

def get_wind_speed_specific_height(windSpeed10m=10, height=2, roughness=0.25):    
    wind_speed = windSpeed10m*(np.log(height/roughness)/np.log(10/roughness))  
    return wind_speed
