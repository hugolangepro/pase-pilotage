# -*- coding: utf-8 -*-
"""
Created on Tue Sep 23 11:00:20 2025

@author: joran
"""
from pase.ENVIRONMENT.aerodynamics import get_wind_speed_specific_height
import numpy as np

def test_wind_speed_vector_length_coherence():
    velocity_test = np.array([3, 6, 9])
    assert get_wind_speed_specific_height(velocity_test, 2, 0.1).shape == velocity_test.shape
    
def test_wind_speed_at_specific_height_value():
    assert np.isclose(get_wind_speed_specific_height(10, 2, 0.1),10/np.log(10/0.1) * np.log(2/0.1), rtol=1e-05)
    assert np.isclose(get_wind_speed_specific_height(10, 15, 0.1),10/np.log(10/0.1) * np.log(15/0.1), rtol=1e-05)
    assert np.isclose(get_wind_speed_specific_height(10, 8 , 3),10/np.log(10/3) * np.log(8/3), rtol=1e-05)