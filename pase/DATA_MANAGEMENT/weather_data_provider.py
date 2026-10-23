#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Authors : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com) and Benoît Stalport
#This file is part of the PASE software, and is distributed under the MIT license.

from datetime import datetime, timedelta
import pandas as pd
import csv
import json
import requests
import time
import math
import numpy as np
import os

from pase.user_support_tools import PASE_Logger
from pase.ENVIRONMENT.aerodynamics import get_wind_speed_specific_height
from pase.DATA_MANAGEMENT.helpers import (aggregate_lat_lon, unpack_latlon,
                                          parse_date_range, get_sampling_period)


def get_cache_key(latitude, longitude, sim_starting_year, sim_ending_year):
    return f'{latitude}_{longitude}_{sim_starting_year}-{sim_ending_year}'

def fetch_weather_from_pvgis(latitude, longitude, start_year, end_year):
    nyears = {}

    for year in range(start_year, end_year + 1):
        pvgis = PvGis()
        pvgis.latitude = latitude
        pvgis.longitude = longitude
        pvgis.start_date = datetime(year, 1, 1, 0, 0, 0)
        pvgis.end_date   = datetime(year, 12, 31, 23, 59, 59)
        pvgis.rad_Database = 'PVGIS-SARAH3'

        pvgis.request_hourly_time_series()
        df = pvgis.pandas_data_frame()

        # Give the dataframe a serializable form
        # nyears[str(year)] = {
        #     "index": df.index.astype(str).tolist(),
        #     "columns": df.columns.tolist(),
        #     "values": df.values.tolist()
        # }
        df['DateTime'] = df['DateTime'].astype(str)
        nyears[year] = df.to_dict(orient='records')

    return nyears


class Weather_data:

    def __init__(self, latitude, longitude, sim_starting_year, sim_ending_year, 
                 WD_option, raw_weather: dict, file=None, daily_file=None):

        self.latitude = latitude
        self.longitude = longitude
        self.sim_starting_year = sim_starting_year
        self.sim_ending_year = sim_ending_year

        self.nyears_data = {}

        if WD_option == 2:  # Read weather data file
            self.get_n_years_WD_from_csvfile(file)
            self.get_n_years_daily_WD(len(self.nyears_data[str(sim_starting_year)]))

        else:  # Data from PVGIS ; digest raw_weather that is passed as a dict to the constructor
            # Convert dict back into pandas DataFrame
            for year, serialized_df in raw_weather.items():  # year, serialized_df is key, value pair
                df = pd.DataFrame.from_records(serialized_df)
                df['DateTime'] = pd.to_datetime(df['DateTime'])
                new_index = pd.date_range(
                    f"01-01-{year} 00:10:00",
                    f"31-12-{year} 23:10:00",
                    freq='1h')
                df = df.set_index(new_index)
                rename_df = {'GHI': 'G(h)', 'DNI': 'Gb(n)', 'DHI': 'Gd(h)',
                             "TAmb": "T2m", "Ws": 'WS10m'}
                df = df.rename(columns=rename_df)

                self.nyears_data[str(year)] = df

            self.get_n_years_daily_WD(len(self.nyears_data[str(sim_starting_year)]),
                                      daily_file)

    def get_n_years_hourly_WD_PVGis(self):

        for year in range(self.sim_starting_year, self.sim_ending_year+1):
            msg = 'Get hourly weather data for year '+str(year)+' from PvGis'
            PASE_Logger(msg, 'INFO')
            pvgis = PvGis()
            pvgis.latitude, pvgis.longitude = self.latitude, self.longitude
            pvgis.start_date = datetime(year, 1, 1, 00, 00, 00)
            pvgis.end_date = datetime(year, 12, 31, 23, 59, 59)
            pvgis.rad_Database = 'PVGIS-SARAH3'
            pvgis.request_hourly_time_series()
            one_year_dataframe = pvgis.pandas_data_frame()
            new_index = pd.date_range("01-01-"+str(year)+" 00:10:00", "31-12-"+str(year)+" 23:10:00",
                                      freq='1h')
            one_year_dataframe = one_year_dataframe.set_index(new_index)
            rename_df = {'GHI': 'G(h)', 'DNI': 'Gb(n)', 'DHI': 'Gd(h)',
                "TAmb": "T2m", "Ws": 'WS10m'}            
            one_year_dataframe = one_year_dataframe.rename(columns=rename_df)
            
            self.nyears_data[str(year)] = one_year_dataframe

    def get_n_years_WD_from_csvfile(self, file):
        
        WD = pd.read_csv(os.path.join('INPUTS', 'WEATHER_FILES', file + '.csv'),
                         delimiter=',|;', engine='python')

        # Get the sampling period as str to use below in pd.date_range
        sampling_period = get_sampling_period(WD['date'])

        new_index = pd.date_range("01-01-" + str(self.sim_starting_year)
                                  + " 00:00:00",
                                  "31-12-" + str(self.sim_ending_year)
                                  + " 23:59:59",
                                  freq=sampling_period)

        WD = WD.set_index(new_index)

        for year in range(self.sim_starting_year, self.sim_ending_year+1):
            one_year_df = WD
            self.nyears_data[str(year)] = one_year_df
            
    def get_n_years_daily_WD(self, freq_deter, csv_file=None):
        
        self.nyears_daily_data = {}
        
        if csv_file is not None:
            rain_vap_pressure = self.parse_agri4cast_weather_file(csv_file)
                   
        if freq_deter == 8760 or freq_deter == 8784:
            n = 1
        elif freq_deter == 35040 or freq_deter == 35136:
            n = 4
        elif freq_deter == 52560 or freq_deter == 52704:
            n = 6

        for year in self.nyears_data.keys():
            
            msg = 'Computation of daily weather data for year '+str(year)
            PASE_Logger(msg, 'INFO')
            
            if csv_file is not None:
                mask = ((rain_vap_pressure.index >= '01-01-'+year+' 00:00:00') &
                       (rain_vap_pressure.index < '01-01-'+str(int(year)+1)+' 00:00:00'))
                
                daily_rain = rain_vap_pressure['PRECIPITATION'][mask].tolist()
                try:
                    vap_press = rain_vap_pressure['VAPOR_PRESSURE'][mask].tolist()
                except KeyError as e:
                    vap_press = rain_vap_pressure['VAPOURPRESSURE'][
                        mask].tolist()

            
            data_to_resample = self.nyears_data[year]
            
            new_index = pd.date_range("01-01-"+year+" 00:00:00",
                                      "31-12-"+year+" 00:00:00",
                                      freq='D')
           
            daily_rad = ((data_to_resample['G(h)'].resample('D').sum())
                         *60*(60/n)*10**-6).tolist()                          # W/m² to MJ/m²            
            min_temp = data_to_resample['T2m'].resample('D').min().tolist()
            max_temp = data_to_resample['T2m'].resample('D').max().tolist()
            mean_temp = data_to_resample['T2m'].resample('D').mean().tolist()
            mean_CO2 = 5*np.sin(new_index.month*(2*np.pi/12))+(415*np.ones((len(mean_temp))))
            mean_WS = data_to_resample['WS10m'].resample('D').mean().tolist() 
            WS_crop_2m = get_wind_speed_specific_height(np.array(mean_WS)).tolist()
            
            if csv_file is None:
                vap_press = data_to_resample['VAPOR_PRESSURE'].resample('D').mean().tolist()
                daily_rain = data_to_resample['PRECIP'].resample('D').sum()
            
            try:
                daily_weather = pd.DataFrame({'Daily_rad': daily_rad,
                                              'Avg_temp': mean_temp,
                                              'Min_temp': min_temp,
                                              'Max_temp': max_temp,
                                              'CO2': mean_CO2,
                                              'Rain': daily_rain,
                                              'Avg_WS_2m': WS_crop_2m,
                                              'Vap_press': vap_press},
                                             index=new_index)
            except ValueError as e:
                msg = (f'There is an error in the date range of the daily'
                       f' weather data ; mismatch with the simulation period.'
                       f'\nCheck that the daily weather data file covers the '
                       f'same years as SimulationStartingYear and '
                       f'SimulationEndingYear.')
                PASE_Logger(msg=msg,
                            level='ERROR')
                raise ValueError(msg)

            self.nyears_daily_data[year] = daily_weather
           
    def parse_agri4cast_weather_file(self, fname):
        # File as downloaded from Agri4Cast
        daily_csv = pd.read_csv(os.path.join('INPUTS',
                                             'WEATHER_FILES',
                                             fname + '.csv'),
                                sep=',|;', engine='python')

        try:
            # Filter the df to find the closest weather station
            local_weather = self.filter_closest_station(daily_csv)
        except KeyError as e:
            # In the old suggested file format, there is no column "LATITUDE"
            # or "LONGITUDE" (because the user was supposed to prepare the file
            # by hand), which raises a KeyError. This except block handles
            # retrocompatibility with this old format.
            local_weather = daily_csv

        date_range = parse_date_range(local_weather)

        rain_vap_pressure = local_weather.set_index(date_range)

        return rain_vap_pressure

    def filter_closest_station(self, df):
        """
        Filter the Agri4Cast dataframe to extract only the data relevant to the
        simulation site. If there is only one weather station, return the full
        dataframe.

        :param df: Agri4Cast data Dataframe.
        :return:
            filt_df: a dataframe that only contains the rows corresponding to
                the weather station closest to the simulation location.
        """
        # Concat latitude and longitude
        df['LATLON'] = aggregate_lat_lon(df['LATITUDE'], df['LONGITUDE'])

        # Find unique lat-lon couples
        latlon_uniques, latlon_ind, latlon_inv, latlon_counts = np.unique(
            df['LATLON'],
            return_index=True,
            return_inverse=True,
            return_counts=True)

        if len(latlon_uniques) > 1:
            # If there are several stations, filter to find the closest one to
            # the site
            lat_uniques, lon_uniques = unpack_latlon(latlon_uniques)

            # Compute the distance between the site (self) and the stations
            dists = np.sqrt((lat_uniques - self.latitude) ** 2
                            + (lon_uniques - self.longitude) ** 2)

            # Find the minimum distance
            min_dist, id_min_dist = np.min(dists), np.argmin(dists)
            closest_lat, closest_lon = lat_uniques[id_min_dist], lon_uniques[
                id_min_dist]

            # Create a logical mask on the closest lat-lon couple
            mask_lat_lon = df['LATLON'].values == aggregate_lat_lon(
                closest_lat, closest_lon)

            filt_df = df[mask_lat_lon].sort_values(['DAY'])

            return filt_df
        else:
            return df.sort_values(['DAY'])

             
class PvGis:
# Source : https://github.com/MechatronicsBlog/Weather_data_Python_PVGIS/blob/master/PvGis.py    

    # Request API
    API_HOURLY_TIME_SERIES = 'http://re.jrc.ec.europa.eu/api/seriescalc'

    # API parameters
    PARAM_LATITUDE = 'lat'
    PARAM_LONGITUDE = 'lon'
    PARAM_RAD_DATABASE = 'raddatabase'
    PARAM_AUTO_HORIZON = 'useHorizon'
    PARAM_USER_HORIZON = 'userHorizon'
    PARAM_START_YEAR = 'startyear'
    PARAM_END_YEAR = 'endyear'
    PARAM_COMPONENTS = 'components'
    PARAM_OUTPUT_FORMAT = 'outputformat'

    # Data headers
    HEADER_DATE_TIME = 'DateTime'
    HEADER_GHI = 'GHI'
    HEADER_DNI = 'DNI'
    HEADER_DHI = 'DHI'
    HEADER_TA = 'TAmb'
    HEADER_WS = 'Ws'

    # PVGIS json keys
    # https://ec.europa.eu/jrc/en/PVGIS/tools/hourly-radiation
    KEY_JSON_OUTPUTS = 'outputs'
    KEY_JSON_HOURLY = 'hourly'
    KEY_JSON_TIME = 'time'
    KEY_JSON_GB = 'Gb(i)'
    KEY_JSON_GD = 'Gd(i)'
    KEY_JSON_GR = 'Gr(i)'
    KEY_JSON_TA = 'T2m'
    KEY_JSON_WS = 'WS10m'

    # Request codes
    REQUEST_OK = 200

    # Latitude, in decimal degrees, south is negative
    DEF_LATITUDE = 36
    # Longitude, in decimal degrees, west is negative
    DEF_LONGITUDE = 2
    # 'PVGIS-SARAH' for Europe, Africa and Asia
    # 'PVGIS-NSRDB' for the Americas between 60°N and 20°S
    # 'PVGIS-ERA5' and 'PVGIS-COSMO' for Europe (including high-latitudes)
    # 'PVGIS-CMSAF' for Europe and Africa(will be deprecated)
    DEF_RAD_DATABASE = 'PVGIS-SARAH3'
    # Calculate taking into account shadows from high horizon. Value of 1 for "yes"
    DEF_AUTO_HORIZON = 1
    # Height of the horizon at equidistant directions around the point of interest, in degrees.
    # Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean
    # the horizon height is 0 due north, 10 for north-east, 20 for east, 30 for south-east, etc
    DEF_USER_HORIZON = ''
    # Starting year of the output of monthly averages (Available from 2007 to 2016)
    DEF_START_DATE = datetime(2016, 1, 1, 00, 00, 00)
    # Final year of the output of monthly averages (Available from 2007 to 2016)
    DEF_END_DATE = datetime(2016, 12, 31, 23, 59, 59)
    # If "1" outputs beam, diffuse and reflected radiation components. Otherwise, it outputs only global values
    DEF_COMPONENTS = 1
    # Date format
    DATE_FORMAT = '%Y%m%d:%H%M'
    # Output formats: 'basic', 'csv' and 'json'
    DEF_OUTPUT_FORMAT = 'json'

    def __init__(self):
        self._latitude = self.DEF_LATITUDE
        self._longitude = self.DEF_LONGITUDE
        self._radDatabase = self.DEF_RAD_DATABASE
        self._autoHorizon = self.DEF_AUTO_HORIZON
        self._userHorizon = self.DEF_USER_HORIZON
        self._startDate = self.DEF_START_DATE
        self._endDate = self.DEF_END_DATE
        self._verbose = False
        self._data_parsed = False
        self._data = None

    @property
    def latitude(self): return self._latitude

    @property
    def longitude(self): return self._longitude

    @property
    def rad_database(self): return self._radDatabase

    @property
    def auto_horizon(self): return self._autoHorizon

    @property
    def user_horizon(self): return self._userHorizon

    @property
    def start_date(self): return self._startDate

    @property
    def end_date(self): return self._endDate

    @property
    def verbose(self): return self._verbose

    @latitude.setter
    def latitude(self, value): self._latitude = value

    @longitude.setter
    def longitude(self, value): self._longitude = value

    @rad_database.setter
    def rad_database(self, value): self._radDatabase = value

    @auto_horizon.setter
    def auto_horizon(self, value): self._autoHorizon = value

    @user_horizon.setter
    def user_horizon(self, value): self._userHorizon = value

    @start_date.setter
    def start_date(self, value): self._startDate = value

    @end_date.setter
    def end_date(self, value): self._endDate = value

    @verbose.setter
    def verbose(self, value): self._verbose = value

    def parse_json(self, value):

        data = []
        pvgis_json = json.loads(value)

        start_date = self.start_date
        end_date = self.end_date
        key_pv_gis_date = self.KEY_JSON_TIME
        date_format = self.DATE_FORMAT
        key_pv_gis_gb = self.KEY_JSON_GB
        key_pv_gis_gd = self.KEY_JSON_GD
        key_pv_gis_gr = self.KEY_JSON_GR
        key_pv_gis_ta = self.KEY_JSON_TA
        key_pv_gis_ws = self.KEY_JSON_WS

        for json_obj in pvgis_json[self.KEY_JSON_OUTPUTS][self.KEY_JSON_HOURLY]:
            date = datetime.strptime(json_obj[key_pv_gis_date], date_format)
            if date > end_date:
                break

            if start_date <= date:
                dni = float(json_obj[key_pv_gis_gb])
                dhi = float(json_obj[key_pv_gis_gd])
                ghi = float(json_obj[key_pv_gis_gr]) + dni + dhi
                ta = float(json_obj[key_pv_gis_ta])
                ws = float(json_obj[key_pv_gis_ws])

                data.append(self.data_row(date, ghi, dni, dhi, ta, ws))

        # Dictionary
        return data

    def request_hourly_time_series(self):

        if self._verbose:
            print("Processing request")
            start = time.time()

        result = None

        payload = {self.PARAM_LATITUDE:     self.latitude,
                   self.PARAM_LONGITUDE:    self.longitude,
                   self.PARAM_RAD_DATABASE: self.rad_database,
                   self.PARAM_AUTO_HORIZON: self.auto_horizon,
                   self.PARAM_USER_HORIZON: self.user_horizon,
                   self.PARAM_START_YEAR:   self.start_date.year,
                   self.PARAM_END_YEAR:     self.end_date.year,
                   self.PARAM_COMPONENTS:   self.DEF_COMPONENTS,
                   self.PARAM_OUTPUT_FORMAT: self.DEF_OUTPUT_FORMAT}

        if self._verbose:
            print("Request send")

        try:
            res = requests.get(self.API_HOURLY_TIME_SERIES, params=payload)
        except requests.exceptions.ConnectionError as e:
            msg = (f'{e} \nThe connection to the PVGIS server is down. '
                   f'Either the PVGIS server is having issues, or you do not '
                   f'have an internet connection. If you keep seeing this '
                   f'message, run simulations with WeatherDataOption: 2 and '
                   'provide a weather data csv file or wait for the PVGIS '
                   'situation to be resolved.')
            PASE_Logger(msg=msg,
                        level='ERROR')
            raise ConnectionError(msg)

        if self._verbose:
            print('Request:', res.url)

        if res.status_code == self.REQUEST_OK:
            self._data_parsed = True
            self._data = self.parse_json(res.text)
        else:
            self._data_parsed = False

        if self._verbose:
            end = time.time()
            print("Request processed:", timedelta(seconds=end-start))

        return result

    def save_csv(self, filename):

        if self._data_parsed:

            with open(filename, 'w', newline='') as csvfile:

                fieldnames = [self.HEADER_DATE_TIME, self.HEADER_GHI,
                              self.HEADER_DNI, self.HEADER_DHI, self.HEADER_TA, self.HEADER_WS]
                csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                csv_writer.writeheader()

                # Write each row
                for data_row in self._data:

                    csv_writer.writerow({self.HEADER_DATE_TIME: data_row['date_time'],
                                         self.HEADER_GHI: data_row['ghi'],
                                         self.HEADER_DNI: data_row['dni'],
                                         self.HEADER_DHI: data_row['dhi'],
                                         self.HEADER_TA: data_row['ta'],
                                         self.HEADER_WS: data_row['ws']})
        else:
            print('Not available data')

    def pandas_data_frame(self):

        if self._data_parsed:

            dt = {self.HEADER_DATE_TIME: [d['date_time'] for d in self._data],
                  self.HEADER_GHI: [d['ghi'] for d in self._data],
                  self.HEADER_DNI: [d['dni'] for d in self._data],
                  self.HEADER_DHI: [d['dhi'] for d in self._data],
                  self.HEADER_TA: [d['ta'] for d in self._data],
                  self.HEADER_WS: [d['ws'] for d in self._data]}

            return pd.DataFrame(data=dt)

        else:
            print('Not available data')
            
    def data_row(self, date_time, ghi, dni, dhi, ta, ws):
        
        data_r = {}
        data_r['date_time'] = date_time
        data_r['ghi'] = ghi
        data_r['dni'] = dni
        data_r['dhi'] = dhi
        data_r['ta'] = ta
        data_r['ws'] = ws
        
        return data_r
  
