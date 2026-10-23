import numpy as np
import pytest
import pandas as pd
from pase.ENVIRONMENT.light import get_sun_vector

def make_series(values):
    """Helper : converts a list into pd. Series as pvlib would do"""
    return pd.Series(values)

def test_zenith():
    beta  = make_series([90.0])
    gamma = make_series([0.0])
    v = get_sun_vector(beta, gamma)
    np.testing.assert_allclose(v[0], [0, 0, 1], atol=1e-10)

def test_east():
    beta  = make_series([0.0])
    gamma = make_series([90.0])
    v = get_sun_vector(beta, gamma)
    np.testing.assert_allclose(v[0], [1, 0, 0], atol=1e-10)

def test_north():
    beta  = make_series([0.0])
    gamma = make_series([0.0])
    v = get_sun_vector(beta, gamma)
    np.testing.assert_allclose(v[0], [0, 1, 0], atol=1e-10)

def test_output_shape():
    n = 5
    beta  = make_series([10.0] * n)
    gamma = make_series([45.0] * n)
    v = get_sun_vector(beta, gamma)
    assert v.shape == (n, 3)

def test_below_horizon_no_error():
    beta  = make_series([-10.0])
    gamma = make_series([90.0])
    v = get_sun_vector(beta, gamma)
    assert v.shape == (1, 3)