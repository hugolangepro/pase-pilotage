# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Nicolas De Cock (nicolas.decock1@gmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd


def get_wind_speed(windSpeed10m=10, height=2, roughness=0.25):    
    wind_speed = windSpeed10m*(np.log(height/roughness)/np.log(10/roughness))  
    return wind_speed

def WindBreak_Wind_Profile_Upstream(porosity):
    a = 1.14*porosity-0.16
    b = (1-porosity)/0.6*0.054
    return a,b

def WindBreak_Wind_Profile_Downstream():
    a = 0.69
    b = 0.042
    return a,b

def Get_u(porosity,DH,relative_wind_angle=0):
    #Condition a adapter mais l idee est de verifier dans quel cadran est le vent
    #Sur le cercle trigonometrique le pare-vent est l'axe Y donc on doit separer
    # les angles du 1 & 4eme quadrant et ceux du 2 et 3eme. Le signe du cos
    # permet de realiser cela. 
    indSwitch = (np.sin(WindAngle*np.pi/180)<0).astype(int)  ### NE DEVRAIT-CE PAS ETRE SINUS ????
    indSwitch[indSwitch==0] = -1
    
    DH = DH*indSwitch
    # if np.cos(relative_wind_angle*np.pi/180)>0:
    #     DH = -DH
    up_a,up_b = WindBreak_Wind_Profile_Upstream(porosity)
    down_a,down_b = WindBreak_Wind_Profile_Downstream()
    u = up_a + DH*up_b
    
    #Les DH<0 correspondent aux positions downstream et >0 aux positions downstream
    u[DH<0] = down_a + np.abs(DH[DH<0])*down_b

    #Cap de l'equation 
    u[u<0] = 0
    u[u>1] = 1
    
    return u

def Get_v(DH):
    down_a,down_b = WindBreak_Wind_Profile_Downstream()
    v = down_a + np.abs(DH)*down_b
    v[v<0] = 0
    v[v>1] = 1
    return v

def Get_Ru(porosity,DH,WindAngle):
   # DH = np.tile(dh,(len(WindAngle),1))
   #TODO sortir la hauteur du panneau du code ecrit en dur
    DH = DH/(1.134*2+0.9)
    u = Get_u(porosity,DH,WindAngle)
    v = Get_v(DH)
    U = u*np.sin(WindAngle*np.pi/180)
    V = v*np.cos(WindAngle*np.pi/180)
    ru = np.sqrt(U**2+V**2)
    return ru

def get_ru_Chanco(WindAngle,porosity,DH,WindSpeed,yrep=15,PanelSpace=14,multiply=False):
    ru1 = Get_Ru(porosity,DH-PanelSpace/2,WindAngle)
    ru2 = Get_Ru(porosity,DH-PanelSpace*3/2,WindAngle)
    ru3 = Get_Ru(porosity,DH+PanelSpace/2,WindAngle)
    ru4 = Get_Ru(porosity,DH+PanelSpace*3/2,WindAngle)     # Ce sont les définitions du maillage central dans le repère des différentes rangées de panneaux

    if multiply == True:
        ru = ru1*ru2*ru3*ru4
    else:
        ru = np.min(np.array([ru1,ru2,ru3,ru4]),0)
    Reduction_coeff = np.mean(ru,axis=2)    
    WindMap = np.mean(WindSpeed*ru,axis=2)
    WindMap = np.tile(WindMap, reps=(yrep,1,1)).transpose(1,0,2)
    return WindMap




porosity = 0.284
#X & Y MESHES
DH = np.arange(-14,14,0.2)
nY = len(np.arange(-16.4,16.4,0.2))

#Reading of the meteo DB
DB = pd.read_csv(os.path.join('INPUTS', 'WEATHER_FILES', 'Chanco_Chile_WD.csv')).drop(columns=['date','G(h)', 'T2m', 'RH2m',  'PRECIP', 'Gb(n)','Gd(h)'])
WindAngle = np.tile(DB['WD10m'].to_numpy(),(len(DH),1)).reshape((len(DH),365,96))
WindSpeed = np.tile(DB['WS10m'].to_numpy(),(len(DH),1)).reshape((len(DH),365,96))
#WindAngle(DH,quarter/hour,day)

#Projection of the windspeed at 2m
WindSpeed = get_wind_speed(WindSpeed)

#Creation of the 2D vector of DH
DH_2D = np.tile(DH,(96,365,1)).transpose()

#Computation of the 2D map of windspeed
WindMap_2D = get_ru_Chanco(WindAngle,porosity,DH_2D,WindSpeed,yrep=nY)


#Visualization of the results
import matplotlib.pyplot as plt
plt.imshow(np.mean(WindMap_2D,2).transpose())
ax = plt.gca();

plt.colorbar()
ax.plot()
print('average windspeed at 2m: ' + str(np.mean(WindSpeed)))
print('average windspeed at 2m with the windbreaks :'  + str(np.mean(WindMap_2D)))


