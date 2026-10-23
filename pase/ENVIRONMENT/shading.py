# -*- coding: utf-8 -*-


import pvlib
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

FULL_CIRCLE_DEG = 360

class Horizon:
    """
    Class managing the far shadings / horizon profile.
    
    It allows to:
    1. Fetch horizon data (e.g. from PVGIS via pvlib)
    2. Store the horizon profile (Azimuth vs Elevation)
    3. Check visibility of points (Sun positions or Sky patches) against this horizon.
    """
    
    def __init__(self, lat, lon):
        """
        Initialize the Horizon object with location coordinates.
        
        Parameters:
            lat (float): Latitude of the location
            lon (float): Longitude of the location
        """
        self.lat = lat
        self.lon = lon
        self.horizon_profile = None
        self.interp_func = None
        
    def get_horizon_pvgis(self, timeout=30):
        """
        Fetch horizon profile from PVGIS using pvlib.
        
        Parameters:
            timeout (int): Timeout for the API request in seconds.
            
        Returns:
            pd.DataFrame: The horizon profile data.
        """
        try:

            data, metadata = pvlib.iotools.get_pvgis_horizon(self.lat, 
                                                             self.lon, 
                                                             timeout=timeout)
            

            self.horizon_profile = pd.DataFrame({'azimuth': data.index,
                                                 'elevation': data.values.flatten()}).sort_values('azimuth')

            azimuths = self.horizon_profile['azimuth'].values
            elevations = self.horizon_profile['elevation'].values
            
            # Ensure strictly increasing azimuths for interpolation
            if azimuths[-1] < FULL_CIRCLE_DEG:
                 azimuths = np.append(azimuths, 
                                      FULL_CIRCLE_DEG)
                 elevations = np.append(elevations, 
                                        elevations[0])
                 
            self.interp_func = interp1d(azimuths, 
                                        elevations, 
                                        kind='linear', 
                                        fill_value="extrapolate")
            
            return self.horizon_profile
            
        except Exception as e:
            print(f"Error fetching PVGIS horizon data: {e}")
            raise

    def get_horizon_mask(self, azimuths, elevations):
        """
        Compute a boolean mask for a set of points (azimuth, elevation).
        Returns True if the point is VISIBLE (above horizon), False otherwise.

        Convention: azimuths are measured from North (0°) clockwise to East (90°),
        consistent with PVGIS data and the solar vectors in light.py
        (where azimuth = arctan2(X_east, Y_north)).

        Parameters:
            azimuths (np.array): Array of azimuths [degrees] (0=North, 90=East)
            elevations (np.array): Array of elevations [degrees]

        Returns:
            np.array: Boolean mask (True=Visible, False=Shaded)
        """
        if self.interp_func is None:
            print("Warning: No horizon profile loaded. Assuming clear horizon.")
            return np.ones_like(azimuths, 
                                dtype=bool)
        
        az_norm = np.mod(azimuths, FULL_CIRCLE_DEG)
        
        horizon_el = self.interp_func(az_norm)
        
        is_visible = elevations > horizon_el
        
        return is_visible

    def is_sun_visible(self, solar_az, solar_el):
        """
        Check if the sun is visible for single or multiple positions.
        Wrapper around get_horizon_mask.
        """
        return self.get_horizon_mask(np.array(solar_az), 
                                     np.array(solar_el))

    def get_visualization_mesh(self, radius=500):
        """
        Generate a PyVista mesh representing the horizon (a 360° circular "wall").
        
        Parameters:
            radius (float): Distance of the horizon wall from the center.
            
        Returns:
            pyvista.StructuredGrid: The horizon mesh.
        """
        import pyvista as pyv
        
        if self.interp_func is None:
            return None
        
        # Azimuths: 0=North, 90=East (consistent with PVGIS and light.py convention)
        azimuths = np.linspace(0, FULL_CIRCLE_DEG, FULL_CIRCLE_DEG + 1)  # 1 degree resolution
        elevations = self.interp_func(azimuths)
        
        bottom_el = 0.0
        
        az_rad = np.radians(azimuths)
        el_rad = np.radians(elevations)
        bot_rad = np.radians(np.full_like(azimuths, bottom_el))
        
        x_top = radius * np.sin(az_rad) * np.cos(el_rad)
        y_top = radius * np.cos(az_rad) * np.cos(el_rad)
        z_top = radius * np.sin(el_rad)

        x_bot = radius * np.sin(az_rad) * np.cos(bot_rad)
        y_bot = radius * np.cos(az_rad) * np.cos(bot_rad)
        z_bot = radius * np.sin(bot_rad)

        n_points = len(azimuths)
        
        points = np.zeros((2 * n_points, 3))
        points[:n_points, 0] = x_top
        points[:n_points, 1] = y_top
        points[:n_points, 2] = z_top
        points[n_points:, 0] = x_bot
        points[n_points:, 1] = y_bot
        points[n_points:, 2] = z_bot

        faces = []
        for i in range(n_points - 1):
            p1 = i
            p2 = i + 1
            p3 = i + 1 + n_points
            p4 = i + n_points
            faces.extend([4, p1, p2, p3, p4])
            
        mesh = pyv.PolyData(points, faces)
        return mesh
