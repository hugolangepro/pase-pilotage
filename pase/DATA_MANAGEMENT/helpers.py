from datetime import datetime
import numpy as np
import pandas as pd


def aggregate_lat_lon(latitude, longitude):
    if isinstance(latitude, float) and isinstance(longitude, float):
        return f'{latitude}; {longitude}'

    if isinstance(latitude, pd.Series) and isinstance(longitude, pd.Series):
        return latitude.astype(str) + "; " + longitude.astype(str)


def unpack_latlon(latlon):
    if isinstance(latlon, pd.Series):
        lat_lon = latlon.str.split("; ", expand=True).astype(float)

        return lat_lon[0].values, lat_lon[1].values

    if isinstance(latlon, np.ndarray):
        latlon_series = pd.Series(latlon)
        lat_lon = latlon_series.str.split("; ", expand=True).astype(float)

        return lat_lon[0].values, lat_lon[1].values

def parse_date_range(df):
    dates = pd.to_datetime(df['DAY'], format="%Y%m%d")
    return pd.date_range(start=dates.min(), end=dates.max(), freq="D")

def get_sampling_period(series, format = '%d/%m/%Y %H:%M'):
    """

    :param series: pandas Series object containing timestamp strings
    :return:
    """
    t1 = datetime.strptime(series[1], format)
    t0 = datetime.strptime(series[0], format)
    dt = t1 - t0

    return f'{dt.seconds}s'


def _to_native(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_native(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(_to_native(v) for v in obj)
    elif isinstance(obj, np.generic):
        return obj.item()  # converts numpy scalar to Python scalar
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
