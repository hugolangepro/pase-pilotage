# -*- coding: utf-8 -*-
"""
Created on Tue Jan 10 09:03:57 2023

@author: Nicolas.DeCock
"""


import datetime
import math
import numpy as np
import pyvista as pv


"""Definition of the half sphere sampling function

Input: 
* number of sample 
* scale

Output:
* Triplet of coordinates
"""

def fibonacci_half_sphere(samples=18,scale = 1):
    points = []
    phi = math.pi * (3. - math.sqrt(5.))
    for i in range(samples):
        y = (1 - (i/float(samples-1)))
        radius = math.sqrt(1- y*y)
        theta = phi * i
        
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        points.append((x*scale,z*scale,y*scale))
        
    return points


# %% Creation of the scene geometry

# PV PolyData
vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])
faces = np.hstack(
    [
        [3, 0, 1, 2],  # triangle
        [3, 1, 2, 3],  # triangle
    ]
    )
sPV = pv.PolyData(vertices, faces)
#Rotation of the PV
sPV.rotate_x(0)

sPV.plot()

#Ground creation (only for visualisation purpose)
vGround = np.array([[-100, -100, -1], [100, -100, -1], [-100, 100, -1], [100, 100, -1]])
fGround = np.hstack(
    [
        [4, 0, 1, 3,2],  # Rectangle
    ]
)
sGround = pv.PolyData(vGround,fGround)

# Local PV array creation
x,y,z = np.mgrid[-3:3, -3:3, 0:1]
Localmesh = pv.StructuredGrid(x, y, z)
LocalPVArray = Localmesh.glyph(geom=sPV, factor=0.75)

LocalPVArray.rotate_x(90)

LocalPVArray.plot()


# Global PV array creation
x,y,z = np.mgrid[-3:3, -3:3, 1:2]*5
GlobalMesh = pv.StructuredGrid(x, y, z)
GlobalPVArray  = GlobalMesh.glyph(geom=LocalPVArray, factor=0.75)


# %% Single Ray casting


# Sky sampling; sky location toward which a ray will be casted
nSkyRay=72
pTarget = fibonacci_half_sphere(nSkyRay)


# Ground sampling; ground location from which a ray will be casted
xs = np.linspace(-5, 5, 6)
ys = np.linspace(-5, 5, 6)

# Initial variable before the ugly for loop
FirstCast = True
FirstCastN = True
Cast = 0


start = datetime.datetime.now()


dDiffu = {}
for xx in xs:
    for yy in ys:
        intersect = 0
        for Target in pTarget:
            Cast += 1
            pSource = [xx, yy, 0] 
            
            # List comprehension to shift the sky target based on ground location
            # This has to be checked if it's correct
            #TargetC = [Target[i] + pSource[i] for i in range(0,3)] 
            
            # Ray casting returning coordinate if the ray has intercepted the geometry
            points, _ = GlobalPVArray.ray_trace(pSource,Target,first_point=True)

            if len(points)>0:
                intersect += 1
                
        #Dict[(x,y)] giving the ratio of sky seen by the ground location
        dDiffu[(xx,yy)] = 1 - intersect/nSkyRay
stop  = datetime.datetime.now()

#Statistics
print("*"*25)
print("For Loop")
print("Time elapsed: " + str(stop-start) + "s")
print(str(Cast) + " rays casted")
print("Number of PV: " + str(int(GlobalPVArray.GetNumberOfCells()/2)))
print(str(np.around((((stop-start).total_seconds())/nSkyRay*(10**6)),decimals=3)) + " s / 1e6 rays")
print("*"*25)



# %% Multi Ray casting



# Creation of the lSource, lTarget required by the multi_ray_trace
lSource = []
lTarget = []
for xx in xs:
    for yy in ys:
        intersect = 0
        for Target in pTarget:
            lSource.append([xx,yy,0])
            lTarget.append(Target)
Cast = len(lSource)


start = datetime.datetime.now()

_, ind_ray, _ = GlobalPVArray.multi_ray_trace(lSource,lTarget,first_point=True,retry=False)


dDiffu2 = {}
for i in ind_ray:
     try:
         dDiffu2[(lSource[i][0],lSource[i][1])] = dDiffu2[(lSource[i][0],lSource[i][1])] - 1/nSkyRay
     except:
         dDiffu2[(lSource[i][0],lSource[i][1])] = 1 - 1/nSkyRay

stop  = datetime.datetime.now()


#Comparison between the two ray casting to compute the diffuse light for each location
#Raise a lot f errors that have to be checked
for k in dDiffu2:
    if np.around(dDiffu2[k],decimals=4) != np.around(dDiffu[k],decimals=4):
        print("*** ERROR ***")
        print(k)
        print(dDiffu2[k])
        print(dDiffu[k])
        print("*** ERROR ***")

print("*"*25)
print("Multiray")
print("Time elapsed: " + str(stop-start) + "s")
print(str(Cast) + " rays casted")
print("Number of PV: " + str(int(GlobalPVArray.GetNumberOfCells()/2)))
print(str(np.around((((stop-start).total_seconds())/Cast*(10**6)),decimals=3)) + " s / 10e6 rays")
print("*"*25)
