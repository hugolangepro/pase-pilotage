#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import numpy as np
import math

def get_ET0(avg_T, min_T, max_T, avg_WS, vap_press, irrad, LAI, Jday,
            ndays, lat, alt, soil_albedo):
    
    specific_heat = 1.013*10**-3
    latent_heat_vaporization = 2.45
    ratio_molecul_weight_watervap_dryair = 0.622
    solar_constant = 0.0820
    stefan_boltzmann_constant = 4.903*10**-9
    soil_heat_flux_density = 0          # Negligable for daily calculations (see Woli et al, 2012, chap 3)
    crop_albedo = 0.25
    
    avg_T_K = avg_T+273.16
    max_T_K = max_T+273.16
    min_T_K = min_T+273.16
    
    if type(LAI) is np.float64 or type(LAI) is int:
        if LAI < 3:
            albedo = ((LAI/3)*crop_albedo + (1-(LAI/3))*soil_albedo)
        else:
            albedo = crop_albedo
    else:
        albedo = np.ones(len(LAI))*crop_albedo
        ind = np.where(LAI<3)
        albedo[ind] = ((LAI[ind]/3)*crop_albedo + (1-(LAI[ind]/3))*soil_albedo)
        
    slope_vap_pressure_curve = (4098*0.6108*math.exp(
        (17.27*avg_T)/(avg_T+237.3)))/(avg_T+237.3)**2

    atmospheric_pressure = 101.3*((293-(0.0065*alt))/293)**5.26
    
    psychometric_constant = (specific_heat*atmospheric_pressure)\
           /(latent_heat_vaporization*ratio_molecul_weight_watervap_dryair)
           
    mean_sat_vap_press = (0.6108*(math.exp((17.27*max_T)/(max_T+237.3))
                                  +math.exp((17.27*min_T)/(min_T+237.3))))/2
    
    actual_vap_press = vap_press/10
    
    diff_vap_press = mean_sat_vap_press-actual_vap_press
    if diff_vap_press < 0 :  #https://hal.inrae.fr/hal-02593413/document, chap 3.3.6, Seuillage des différents termes de l'ET0
        diff_vap_press = 0
        
    inverse_rel_dist_earth_sun = 1+(0.033*math.cos((2*math.pi*Jday)/ndays))
    solar_decination = 0.409*math.sin(((2*math.pi*Jday)/ndays)-1.39)
    sunset_hour_angle = math.acos(-math.tan(lat*(math.pi/180))
                                  *math.tan(solar_decination))

    extraterre_radiation = ((24*60)/math.pi)*solar_constant \
    *inverse_rel_dist_earth_sun*(sunset_hour_angle
                                 *math.sin(lat*(math.pi/180))
                                 *math.sin(solar_decination)
                                 +math.cos(lat*(math.pi/180))
                                 *math.cos(solar_decination)
                                 *math.sin(sunset_hour_angle))

    clear_sky_solar_radiation = (0.75+((2*10**-5))*alt)*extraterre_radiation
    
    relative_shortwave_radiation = irrad/clear_sky_solar_radiation
    
    net_longwave_radiation_out = (stefan_boltzmann_constant
                                  *(((max_T_K**4)+(min_T_K**4))/2)
                                  *(0.34-0.14*math.sqrt(actual_vap_press))
                                  *(1.35*relative_shortwave_radiation-0.35))
    
    net_shortwave_radiation_in = (1-albedo)*irrad
    
    net_radiation_in = net_shortwave_radiation_in-net_longwave_radiation_out

    # Computation of reference evapotranspiration (ETo)
    ET0 = ((0.408*slope_vap_pressure_curve
            *(net_radiation_in-soil_heat_flux_density))
           /(slope_vap_pressure_curve+(psychometric_constant
                                       *(1+0.34*avg_WS))))\
        +((psychometric_constant*(900/avg_T_K)*avg_WS*(diff_vap_press))
          /(slope_vap_pressure_curve+(psychometric_constant*(1+0.34*avg_WS))))
    
    if type(ET0) is np.float64:
        if ET0 < 0:     # if net_radiation_in is negative or first term of Penman < second term
            ET0 = 0     #https://hal.inrae.fr/hal-02593413/document, chap 3.3.6, Seuillage des différents termes de l'ET0
    else:
        ind = np.where(ET0<0)
        ET0[ind] = 0          # In north hemisphere, net radiation is negative in winter (https://earthobservatory.nasa.gov/global-maps/CERES_NETFLUX_M#:~:text=Earth's%20net%20radiation%2C%20sometimes%20called,the%20top%20of%20the%20atmosphere.&text=Places%20where%20more%20energy%20was,negative%20net%20radiation)%20are%20purple.)
    
    
    return ET0

    # These climatic methods to calculate ETo were all calibrated for ten-day or monthly calculations, 
    # not for daily or hourly calculations ==> problem of negative values. 
    # (<http://www.fao.org/3/x0490e/x0490e07.htm#latent%20heat%20of%20vaporization%20(l)>.)
