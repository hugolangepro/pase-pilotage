import numpy as np
import copy 
from datetime import datetime

from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization

class Soil():
    def __init__(self, grid, inits, soil_parameters, soil_properties,variables_to_save):
        """
        Initialize the soil.
        Set the grid, the initial variables, the variables to save. 
        Initialize the output dictionary and initialize the spatialized soil.

        Args:
            grid: shape of the grid
            grid type: tuple (x, y)
            inits: initial values of variables
            inity type: dictionary
            soil_properties: pandas DataFrame of soil hydraulic properties
            variables_to_save: names of variables to save in the output dictionary
            variables_to_save type: list
        """
        self.grid = grid
        self.inits = inits
        self.variables_to_save = variables_to_save
        self.nyears_data = {}
        self.soil_properties = soil_properties
        self.soil_parameters = soil_parameters
        self.init_spatialized_soil()
        self.classify_usda_texture()
        self.get_hydraulic_properties()

    def classify_usda_texture(self):
        """
        Classify USDA soil texture class based on sand and clay percentages.
        Silt is computed as 100 - sand - clay.

        Based on https://www.nrcs.usda.gov/resources/education-and-teaching-materials/soil-texture-calculator.

       """
        # Verify that sand and clay are good shape arrays
        if not isinstance(self.sand, np.ndarray) or not isinstance(self.clay, np.ndarray):
            raise TypeError("sand and clay must be numpy arrays for per-cell classification.")

        self.silt = 100 - self.sand - self.clay

        # Conditions d'erreur : s'assurer que les pourcentages sont valides
        if np.any(self.sand < 0) or np.any(self.clay < 0) or np.any(self.silt < 0):
            raise ValueError("Sand, clay, and silt must be >= 0.")

        #if np.any((self.sand + self.clay + self.silt) != 100):
            #raise ValueError("Sand + clay + silt must equal 100 in every cell.")

        # Initialiser tableau vide de texture (object = string)
        self.texture = np.full(self.sand.shape, 'Unknown', dtype=object)

        # Exemple de classification vectorisée
        conditions = [
            (self.clay >= 40) & (self.silt < 40) & (self.sand <= 45),
            (self.clay >= 40) & (self.silt >= 40),
            (self.clay >= 35) & (self.sand >= 45),
            (self.clay >= 27) & (self.clay < 40) & (self.silt <= 20),
            (self.clay >= 27) & (self.clay < 40) & (self.silt > 20) & (self.silt <= 40),
            (self.clay >= 27) & (self.clay < 40) & (self.silt > 40),
            (self.clay >= 20) & (self.clay < 27) & (self.silt >= 28) & (self.sand <= 52),
            (self.clay < 27) & (self.silt >= 50) & (self.clay >= 12),
            (self.clay < 12) & (self.silt >= 80),
            (self.clay >= 20) & (self.clay < 35) & (self.sand > 45) & (self.silt < 28),
            (self.clay < 20) & (self.sand > 52) & ((self.silt + 2 * self.clay) >= 30),
            (self.clay < 7) & (self.silt < 50) & (self.sand > 85),
            (self.sand >= 70) & (self.sand <= 91) &
            ((self.silt + 1.5 * self.clay) >= 15) &
            ((self.silt + 2 * self.clay) < 30),
        ]
        choices = [
            "Clay", "Silty_Clay", "Sandy_Clay", "Sandy_Clay_Loam", "Clay_Loam",
            "Silty_Clay_Loam", "Loam", "Silty_Loam", "Silt", "Sandy_clay_loam",
            "Sandy_Loam", "Sand", "Loamy_Sand"
        ]

        self.texture = np.select(conditions, choices, default="Loam")

    def get_hydraulic_properties(self):
        """
        Assign hydraulic properties (InfRate and SatConD) to each cell based on its texture.
        Assumes self.texture is a numpy array of texture names (same shape as grid).
        Assumes self.soil_properties is a pandas DataFrame with 'texture', 'InfRate', and 'SatConD'.
        """
        # Create empty arrays to store cell properties
        self.InfRate = np.zeros(self.grid)
        self.SatConD = np.zeros(self.grid)

        # Créer un dictionnaire: texture → (InfRate, SatConD)
        texture_map = {
            row['Texture']: (row['InfRate'], row['SatConD'])
            for _, row in self.soil_properties.iterrows()
        }

        # Appliquer ces propriétés cellule par cellule selon la texture
        for texture_name, (inf, sat) in texture_map.items():
            mask = self.texture == texture_name
            self.InfRate[mask] = inf
            self.SatConD[mask] = sat

        # Vérifier s'il reste des cellules sans valeurs assignées
        if np.any(self.InfRate == 0) or np.any(self.SatConD == 0):
            unknown_textures = np.unique(self.texture[(self.InfRate == 0) | (self.SatConD == 0)])
            raise ValueError(f"Some textures not found : {unknown_textures}")

    def init_spatialized_soil(self):
        """
        Initialize the soil at the start of the simulation.
        Create a numpy array attribute for each init variable.
        Compute the N2/N2O repartition [-], the water capacity [mm], the wilting point [mm], the water saturation [mm], the water content [mm], the water content relative to the water capacity [-].
        """

        # Fixed soil parameters (for a simulation)
        for key, value in self.soil_parameters.items():
            setattr(self, key, np.full(self.grid, value))
        # Initialized soil variables
        for key, value in self.inits.items():
            setattr(self, key, np.full(self.grid, value))

        self.repartitionN2N2O = 0.189+(1.171*self.clay/(1+0.136*self.clay))
        # limit soil depth to maximum useful depth (usually 1 meter)
        self.soil_depth = self.soil_depth.clip(0, self.max_soil_depth)
        self.water_capacity = (0.2576 - 0.002 * self.sand + 0.0036 * self.clay + 0.0299 * self.org) * self.soil_depth * (1 - self.coarse/100)
        self.wilting_point = (0.026 + 0.005 * self.clay + 0.0158 * self.org) * self.soil_depth * (1 - self.coarse/100)
        self.water_saturation = (100 / 88) * self.water_capacity

        # Initiate water content (arbitrary)
        self.water = self.water_capacity
        self.W = (self.water - self.wilting_point) / (self.water_capacity - self.wilting_point)


    def init_daily_loop(self, day):
        """
        Initialize the daily loop.
        Set the day, and the year.
        If the first day of the year initialize the output dictionary for the year.

        Args:
            day: today's date
            day type: datetime object
        """
        self.day = day
        self.year = str(day.year)

        if self.day.dayofyear == 1:
            self.nyears_data[self.year] = {}
            self.init_one_year_variables()


    def init_one_year_variables(self):
        """ Initialize the output dictionary of each variable to save for the year. """
        for var in self.variables_to_save:
            self.nyears_data[self.year][var] = {}


    def compute_water_balance(self, PP, AET,method):
        """Compute water balance (water) [mm] and water stress (W) [%].

        Args:
            method : method used to compute water_balance,
                - 'Ruelle2018' were water drainage is a simple proportion of water content, from Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
                - 'Bonnard2025' were ater leaching is dependent on water infiltration capacity (InfRate) [mm/day] and the soil hydraulic conductivity at saturation (SatCond) [cm/day], from Bonnard et al. (2025), https://doi.org/10.1016/j.eja.2025.127520.
            method type : str
            PP: daily precipitations [mm].
            PP type: numpy array of shape (grid)
            AET: daily actual evapotranspiration [mm].
            AET type: numpy array of shape (grid)
        """
        if method=='Ruelle2018':
            self.water += PP - AET + self.not_runoff
            self.water_leached = np.where(self.water < self.water_capacity, 0, 0.2*(self.water - self.water_capacity))
            self.not_runoff = np.where(self.water < self.water_saturation, 0, 0.2*(self.water - self.water_saturation))

            self.water -= self.water_leached
            # water content limits
            self.water = self.water.clip(0, self.water_saturation)

            # Water (%)
            self.W = (self.water - self.wilting_point) / (self.water_capacity - self.wilting_point)
            self.W = self.W.clip(0, 1)

        elif method=='Bonnard2025':
            # Limited infiltration by InfRate
            infiltrated = np.minimum(PP, self.InfRate)
            extra_water = PP - infiltrated

            self.water += infiltrated - AET + self.not_runoff

            # Computing water_leached
            self.water_leached = np.zeros_like(self.water)
            mask_below_sat = (self.water > self.water_capacity) & (self.water < self.water_saturation)
            Below_SatConD = np.zeros_like(self.water)
            Below_SatConD[mask_below_sat] = self.SatConD[mask_below_sat] * np.exp(
                48.2 * (self.water[mask_below_sat] - self.water_saturation[mask_below_sat]) * 1e-7
            )
            self.water_leached[mask_below_sat] = (
                    Below_SatConD[mask_below_sat] / 100 * (self.water[mask_below_sat] - self.water_capacity[mask_below_sat])
            )
            mask_above_sat = self.water >= self.water_saturation
            self.water_leached[mask_above_sat] = (
                    self.SatConD[mask_above_sat] / 100 * (self.water_saturation[mask_above_sat] - self.water_capacity[mask_above_sat])
            )

            # Updating water content
            self.water -= self.water_leached

            # Computing not-runoff as constant proportion of excess water
            excess = self.water + extra_water - self.water_saturation
            self.not_runoff = np.where(excess > 0, 0.2 * excess, 0)

            self.water = self.water.clip(0, self.water_saturation)

            # Computing W
            self.W = (self.water - self.wilting_point) / (self.water_capacity - self.wilting_point)
            self.W = self.W.clip(0, 1)

    def compute_N_mineralization(self, Temp,method):
        """Compute nitrogen mineralization based on water stress (W) air temperature (Temp) and soil organic nitrogen (Norg) [kgNorg ha^-1].

        Args:
            method : method used
                - 'Ruelle2018' rom Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
                - 'Bonnard2025' from Bonnard et al. (2025), https://doi.org/10.1016/j.eja.2025.127520.
            method type : str
            Temp: average daily temperature [°C].
            Temp type: numpy array of shape (grid)
        """
        if method=='Ruelle2018':
            self.g0 = (1 - 0.2) * self.W + 0.2
            self.fT_nitro = np.exp(self.K * (Temp - self.Tref))
            self.Vp = (0.0929 + (0.1833-0.0929) * np.exp(-0.2173*self.Norg/1000)) * (self.Norg/1000)
            self.mineralization = self.g0 * self.fT_nitro * self.Vp

        elif method=='Bonnard2025':
            self.g0 = (1 - 0.2) * self.W + 0.2
            self.g0 = self.g0.clip(0.2, 1)
            self.fT_nitro = np.where(
                Temp < 0,
                0,
                np.where(
                    Temp < 4,
                    (Temp / 4) * 0.28,
                    np.exp(self.K * (Temp - self.Tref))
                )
            )
            self.fT_nitro=self.fT_nitro.clip(0,1)
            self.Vp = (0.0929 + (0.1833-0.0929) * np.exp(-0.2173*self.Norg/1000)) * (self.Norg/1000)
            self.mineralization = self.g0 * self.fT_nitro * self.Vp

    def compute_N_immobilization(self,Temp,method):
        """Compute nitrogen immobilization based on water stress (W), air temperature (Temp) and soil mineral nitrogen (Nmin) [kgN ha^-1].

        Args :
            method : method used
                - 'Ruelle2018' from Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
                - 'Bonnard2025' from Bonnard et al. (2025), https://doi.org/10.1016/j.eja.2025.127520.
            method type : str
            Temp: average daily temperature [°C].
            Temp type: numpy array of shape (grid)
        """
        if method=='Ruelle2018':
            self.Ip = 4. * self.Nmin / 1000
            self.Ip = self.Ip.clip(0, None)
            self.immobilization = self.g0 * self.fT_nitro * self.Ip

        elif method=='Bonnard2025':
            self.Ip = 2.5* 4. * self.Nmin / 1000
            self.Ip = self.Ip.clip(0, None)
            self.fT_immo = np.where(
                Temp <= 0,
                0,
                np.where(
                    Temp < 4,
                    (Temp / 4) * 2,
                    np.exp(-self.K * (Temp - self.Tref))
                )
            )
            self.immobilization = self.g0 * self.fT_immo * self.Ip

    def compute_N_leached(self,method):
        """Compute nitrogen leaching (N_leached) [kgN ha^-1] based on proportion of water leached [mm].

        Args :
            method : method used
                - 'Ruelle2018' from Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
                - 'Bonnard2025', Upper limit of N_leached at 0.7*Nmin, from Bonnard et al. (2025), https://doi.org/10.1016/j.eja.2025.127520.
            method type : str
        """
        if method == 'Ruelle2018':
            self.N_leached = self.Nmin * (self.water_leached / self.water)

        elif method == 'Bonnard2025':
            n_leached_raw = self.Nmin * (self.water_leached / self.water)

            conditions_leached = [
                n_leached_raw > 0.7 * self.Nmin
            ]

            values_leached = [
                0.7 * self.Nmin  # Upper limit
            ]

            self.N_leached = np.select(conditions_leached, values_leached, default=n_leached_raw)

    def compute_N2O_emissions(self):
        """ Compute nitrogen dioxide emission based on mineral nitrogen (Nmin), water stress (W) and temperature (Temp) influencing denitrification.

         From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
        """
        self.globalemission = (self.Nmin/1000) * self.fT_nitro * self.g0
        self.N2Oemisson  =  (1 - self.repartitionN2N2O) * self.globalemission
        self.N2Oemisson = self.N2Oemisson.clip(0, None)
    

    def compute_N_from_rain(self, PP):
        """Compute nitrogen suplly through rain (N_from_rain) [kgN ha^-1].

        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.

        Args:
            PP: daily precipitations [mm].
            PP type: numpy array of shape (grid)
        """
        self.N_from_rain = 0.009 * PP


    def compute_Norg(self, percentageofNmin, N_plant_litter, fert_org):
        """Compute soil organic nitrogen balance with inputs and outputs.

        Args:
            percentageofNmin: part of mineral nitrogen in organic fertilizer [-].
            percentageofNmin type: float
            N_plant_litter: amount of organic nitrogen coming from material undergoing abscission [kgNorg ha^-1].
            N_plant_litter type: numpy array of shape (grid)
            fert_org: amount of nitrogen in organic fertilizer [kgN ha^-1].
            fert_org type: float
        """
        self.Norg += \
                    self.immobilization \
                    - self.mineralization \
                    + (1. - percentageofNmin) * fert_org \
                    + N_plant_litter


    def compute_Nmin(self, percentageofNmin, NH3volatfactor, N_uptake, fert_org, fert_min):
        """Compute soil mineral nitrogen balance with inputs and outputs.

        Args:
            percentageofNmin: part of mineral nitrogen in organic fertilizer [-].
            percentageofNmin type: float
            NH3volatfactor: factor allowing to consider amount of N lost by volatilization [-].
            NH3volatfactor type: float
            N_uptake: mineral nitrogen absorbed by plants [kgN ha^-1].
            N_uptake type: dictionary
            fert_org: amount of nitrogen in organic fertilizer [kgN ha^-1].
            fert_org type: float
            fert_min: amount of mineral nitrogen from mineral fertilization [kgN ha^-1].
            fert_min type: float
        """
        self.Nmin += \
                    self.mineralization \
                    - self.immobilization \
                    + self.N_from_rain \
                    + fert_min \
                    + percentageofNmin * (1 - NH3volatfactor) * fert_org \
                    - N_uptake \
                    - self.N_leached
        

    def save_variables(self):
        """ Save the variables in the output dictionary. """
        for var in self.variables_to_save:
            self.nyears_data[self.year][var][self.day] = copy.deepcopy(getattr(self, var))
            
            
    def visualize_map_of_a_variable(self, variable, scene_3D, meshes, year, MM_DD=None, unit=''):
        """
        Visualize a specific spatialized variable in the 3D scene.

        Parameters
        ----------
        variable : string
            Name of the variable to visualize.
        scene_3D : Pyvista Polydata
            3D scene as a pyvista polydata.
        meshes : Mesh object
            Mesh object containing the coordinates of the points of interest.
        year : int
            Year fo which results will be visualized.
        MM_DD : string
            Date as a format 'MM-DD'
        unit : string
            Unit of the variable to visualize.

        Returns
        -------
        None.

        """ 
        
        if type(scene_3D) == list:
            geo = scene_3D[0]
        else:
            geo = scene_3D
        
        open_pyvista_3D_visualization(meshes.sourcepoints[:,:-1], 
                                      self.nyears_data[str(year)][variable][datetime.strptime(str(year)+'-'+MM_DD+' 00:00:00', '%Y-%m-%d %H:%M:%S')], 
                                      geo,
                                      variable+' map GRASSIM '+str(year)+'-'+MM_DD+' ['+unit+']')
