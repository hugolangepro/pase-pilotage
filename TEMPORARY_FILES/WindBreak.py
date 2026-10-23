# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 08:26:50 2023

@author: Nicolas.DeCock
"""

import numpy as np
import matplotlib.pyplot as plt


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
    if np.cos(relative_wind_angle*np.pi/180)>0:
        DH = -DH
    up_a,up_b = WindBreak_Wind_Profile_Upstream(porosity)
    down_a,down_b = WindBreak_Wind_Profile_Downstream()
    u = up_a + DH*up_b
    u[DH<0] = down_a + np.abs(DH[DH<0])*down_b
    u[u<0] = 0
    u[u>1] = 1
    
    return u

def Get_v(DH):
    down_a,down_b = WindBreak_Wind_Profile_Downstream()
    v = down_a + np.abs(DH)*down_b
    v[v<0] = 0
    v[v>1] = 1
    return v



DH = np.linspace(-20,20,81)
#
porosity = 0.2
uW = Get_u(porosity,DH,True)
uE = Get_u(porosity,DH,False)
v = Get_v(DH)


#
WindVelocity = 10 #m/s

for WindAngle in [0,15,45,65,90]:
#WindAngle = 90 #°
    U = uE*np.cos(WindAngle*np.pi/180)*WindVelocity
    V = v*np.sin(WindAngle*np.pi/180)*WindVelocity
    U_V = np.sqrt(U**2+V**2)/10
    
    plt.plot(DH,U_V,label=str(WindAngle))
plt.legend()
plt.xlabel('D/H')
plt.ylabel('U/U_{moyen)')
plt.show()




