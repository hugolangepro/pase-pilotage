import pytest 
import numpy as np
import pandas as pd
from pase.CROPS.GRASSIM.soil.soil import Soil

def test_compute_N_immobilization():
    grid=(1,1)
    init=dict(Nmin=50,Norg=50)
    variables_to_save=[]
    soil_parameters=dict(not_runoff=0,sand=25,clay=25,coarse=15,org=3,soil_depth=1000,max_soil_depth=1000,albedo=0.2,K=0.115,Tref=15,FNAmax=0.4,NSc=200)
    soil_properties=pd.DataFrame({
        "Texture": [
            "Sand", "Loamy_Sand", "Sandy_Loam", "Loam", "Silty_Loam",
            "Sandy_Clay_Loam", "Clay_Loam", "Silty_Clay_Loam",
            "Sandy_Clay", "Silty_Clay", "Clay"
        ],
        "Code": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "SatConD": [504.00, 146.64, 62.16, 31.68, 16.32, 10.32,
                    5.52, 3.60, 2.88, 2.16, 1.44],
        "InfRate": [696, 600, 696, 360, 288, 240,
                    168, 168, 120, 96, 24]
    })
    soil=Soil(grid,init,soil_parameters, soil_properties,variables_to_save)
    soil.compute_water_balance(2, 0.2,method='Ruelle2018')
    soil.compute_N_mineralization(13,method='Ruelle2018') #K=0.115, Tref= 15, Temp=13
    soil.compute_N_immobilization(13, method='Ruelle2018')
    assert np.isclose(soil.immobilization[0,0],0.158906720500667,rtol=1e-8)