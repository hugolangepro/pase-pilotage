# -*- coding: utf-8 -*-
"""
Created on Fri Jan 27 15:06:37 2023

@author: Nicolas.DeCock
"""


import matplotlib.pyplot as plt
import numpy as np

#PVCoord on the PV
PVCoord = np.array([[0,0,0],[1,0,0],[1,0,1],[0,0,1]])
v_sun = [.5,0.5,0.5]
v_ground = [0,0,1]

def Get_Shade_Coordinate(PVCoord,v_sun,v_ground):
    
    
    norm = np.dot(v_sun, v_ground)
    
    # calcul de la PVCoordonée selon x
    x_fr_term = v_ground[1] * (
            PVCoord[:,0] * v_sun[1] - PVCoord[:,1] * v_sun[0])
    x_sc_term = v_ground[2] * (
            PVCoord[:,0] * v_sun[2] - PVCoord[:,2] * v_sun[0])
    x = (x_fr_term + x_sc_term) / norm
    
    # calcul de la PVCoordonnées selon y
    y_fr_term = v_ground[0] * (
            PVCoord[:,1] * v_sun[0] - PVCoord[:,0] * v_sun[1])
    y_sc_term = v_ground[2] * (
            PVCoord[:,1] * v_sun[2] - PVCoord[:,2] * v_sun[1])
    y = (y_fr_term+ y_sc_term) / norm
    # création du vecteur final
    shade_vertice = np.column_stack([x, y])
    
    return  [(i[0],i[1]) for i in shade_vertice]

#Mesh function to find if a point is within polygon drawn by vertices
# (cf https://stackoverflow.com/questions/63527698/determine-if-points-are-within-a-rotated-rectangle-standard-python-2-7-library)
def is_on_right_side(x, y, xy0, xy1):
    x0, y0 = xy0
    x1, y1 = xy1
    a = float(y1 - y0)
    b = float(x0 - x1)
    c = - a*x0 - b*y0
    return a*x + b*y + c >= 0

def test_point(x, y, vertices):
    num_vert = len(vertices)
    is_right = [is_on_right_side(x, y, vertices[i], vertices[(i + 1) % num_vert]) for i in range(num_vert)]
    all_left = not any(is_right)
    all_right = all(is_right)
    return all_left or all_right


#Mesh
xMesh = np.linspace(-5,5,500)
yMesh = np.linspace(-5,5,500)

#Get the vertice of the shade on the ground
shade_vertice = Get_Shade_Coordinate(PVCoord,v_sun,v_ground)

#Computation and drawing of the grid
gShade1 = np.array([0 if test_point(x,y,shade_vertice) else 1 for y in yMesh for x in xMesh ])
gShade = gShade1.reshape([len(xMesh),len(yMesh)])


plt.imshow(gShade)
plt.show()




