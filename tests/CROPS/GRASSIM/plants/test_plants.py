import pytest
import numpy as np
from pase.CROPS.GRASSIM.plants.plants import Plants

def test_interval_fT ():
    crop = object.__new__(Plants)
    crop.Temp = 15
    crop.T0=0
    crop.T1=4
    crop.T2=20
    crop.Tlimit=25
    crop.compute_fT()
    assert 0 <= float(crop.fT) <= 1

def test_update_age():
    plant = object.__new__(Plants)
    plant.Temp = np.array([5.0, 15.0, 25.0])
    plant.Tmin = 10.0
    plant.BMGV = np.array([10.0, 20.0, 30.0])
    plant.SENGV = np.array([1.0, 2.0, 3.0])
    plant.GROGV = np.array([2.0, 3.0, 4.0])
    plant.BMGR = np.array([10.0, 20.0, 30.0])
    plant.SENGR = np.array([1.0, 2.0, 3.0])
    plant.GROGR = np.array([2.0, 3.0, 4.0])
    plant.BMDV = np.array([10.0, 20.0, 30.0])
    plant.ABSDV = np.array([1.0, 2.0, 3.0])
    plant.BMDR = np.array([10.0, 20.0, 30.0])
    plant.ABSDR = np.array([1.0, 2.0, 3.0])
    plant.ageGV = np.zeros(3)
    plant.ageGR = np.zeros(3)
    plant.ageDV = np.zeros(3)
    plant.ageDR = np.zeros(3)
    plant.sigmaGV=0.4
    plant.sigmaGR=0.2
    plant.update_age()
    assert np.all(plant.ageGV >= 0)
    assert np.all(plant.ageGR >= 0)
    assert np.all(plant.ageDV >= 0)
    assert np.all(plant.ageDR >= 0)
    assert plant.ageGV.shape == plant.Temp.shape
    assert plant.ageGR.shape == plant.Temp.shape
    assert plant.ageDV.shape == plant.Temp.shape
    assert plant.ageDR.shape == plant.Temp.shape
