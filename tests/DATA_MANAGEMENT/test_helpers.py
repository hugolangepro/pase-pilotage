import numpy as np
import pandas as pd
import pytest

from pase.DATA_MANAGEMENT.helpers import (aggregate_lat_lon, unpack_latlon,
                                          parse_date_range, get_sampling_period)


def test_aggregate_lat_lon_floats():
    latitude = 50.123
    longitude = 4.56789

    assert aggregate_lat_lon(latitude, longitude) == '50.123; 4.56789'


def test_aggregate_lat_lon_pd_series():
    latitude = pd.Series([50.123, 45.6789])
    longitude = pd.Series([4.56789, 10.111213])

    assert (aggregate_lat_lon(latitude, longitude) == pd.Series(['50.123; 4.56789', '45.6789; 10.111213'])).all()


def test_unpack_latlon_uniques_pd_series():
    latlon_series = pd.Series(['50.123; 4.56789', '45.6789; 10.111213'])

    lat, lon = unpack_latlon(latlon_series)

    assert (lat == np.array([50.123, 45.6789])).all()
    assert (lon == np.array([4.56789, 10.111213])).all()

def test_unpack_latlon_uniques_ndarray():
    latlon_ndarray = np.array(['50.123; 4.56789', '45.6789; 10.111213'])

    lat, lon = unpack_latlon((latlon_ndarray))

    assert (lat == np.array([50.123, 45.6789])).all()
    assert (lon == np.array([4.56789, 10.111213])).all()

def test_parse_date_range():
    df = pd.DataFrame(['20050101', '20081231'], columns=['DAY'])

    date_range = parse_date_range(df)
    assert (date_range == pd.date_range('01-01-2005 00:00:00',
                                      '31-12-2008 00:00:00',
                                      freq='D')).all()

def test_get_sampling_period():
    series = pd.Series(['01/01/2021 00:00', '01/01/2021 00:15'])

    sampling_period = get_sampling_period(series)

    # assert sampling_period == datetime.timedelta(0, 900)
    assert sampling_period == '900s'

