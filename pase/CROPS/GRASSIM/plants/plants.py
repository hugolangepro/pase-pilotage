import numpy as np
import copy
from datetime import datetime

from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization

class Plants():
    def __init__(self, grid, pft_composition, inits, kc_values, pft_values, variables_to_save):
        """
        Initialize the plants.
        Set the grid, the PFT composition, the initial variables, the Kc values, the PFT values, and the variables to save.

        Args:
            grid: tuple of (x, y), shape of the grid
            pft_composition: dictionary of PFT composition
            inits: dictionary of initial variables
            kc_values: dictionary of Kc values
            pft_values: pandas DataFrame of PFT values
            variables_to_save: list of strings of variables to save
        """

        self.grid = grid
        self.pft_composition = pft_composition
        self.inits = inits
        self.kc_values = kc_values
        self.pft_values = pft_values
        self.variables_to_save = variables_to_save

        self.nyears_data = {}
        
        self.compute_pft_params()
        self.init_spatialized_crop()


    def compute_pft_params(self):
        """ Compute the weighted sum of PFT parameters based on PFT composition. """
        self.pft_values['Weight'] = self.pft_values['PFT'].map(self.pft_composition)
        self.pft_params = self.pft_values.drop(columns=['PFT']).multiply(self.pft_values['Weight'], axis=0).sum().to_dict()
        self.pft_params.pop('Weight', None)
        for key, value in self.pft_params.items():
            setattr(self, key, value)


    def init_spatialized_crop(self):
        """
        Initialize the crop at the start of the simulation.
        If the biomass initialization type is "InitialHeight", the crop biomass is initialized with the initial height using init_with_height().
        If the biomass initialization type is "InitialBM", the crop biomass is initialized with the initial biomass using init_with_BM().
        for each variable, a numpy array is created with the same size as the grid.
        Compute organic matter digestability [-], N content [kgN/ha], N concentration [kgN/kgDM]
        Compute Leaf Area Index [-] based on surface area [m²/gDM], green vegetative biomass [kgDM/ha], unit correction factor [1/10 = (1000 [g/kg]) / (10000 [m²/ha])], percentage of leaf area in the total surface area.
        """
        if self.inits['BM_init_type'] == "InitialHeight":
            self.init_with_height()
        elif self.inits['BM_init_type'] == "InitialBM":
            self.init_with_BM()
        else :
            raise ValueError(f"BM_init_type '{self.inits['BM_init_type']}' is not valid")
        
        for variable_name in ['ageGV', 'ageGR', 'ageDV', 'ageDR', 'apex_grazed','Tmin','Tmax','Tstop']:
            setattr(self, variable_name, np.full(self.grid, self.inits[variable_name]))
        
        self.BM = self.BMGV+self.BMGR+self.BMDV+self.BMDR
        self.OMDGV = self.maxOMDGV-(self.ageGV*(self.maxOMDGV-self.minOMDGV)/self.LLS) #organic mater digestibility of green vegetative biomass
        self.OMDGR = self.maxOMDGR-(self.ageGR*(self.maxOMDGR-self.minOMDGR)/(self.ST2-self.ST1)) #organic mater digestibility of green reproductive biomass
        
        #we assume that at the beginning of the season the plant has at least the minimum amount of N needed for maximum growth
        self.NconcGV = self.a_Ncrit*0.01 #*(BMGV+BMGR/1000)^-b_Ncrit
        self.NconcGR = self.a_Ncrit*0.01

        #We assume that at the beginning of the season the N concentration is the same for the both green compartments. Same for the dead ones.
        self.QNGV = self.NconcGV*self.BMGV
        self.QNGR = self.NconcGR*self.BMGR
        self.QNDV = self.NconcDV*self.BMDV
        self.QNDR = self.NconcDR*self.BMDR

        self.NGV = np.divide(self.QNGV, self.BMGV, where=self.BMGV > 0, out=np.zeros_like(self.BMGV)) # GV grass N concentration (kg N/kgDM)
        self.NGR = np.divide(self.QNGR, self.BMGR, where=self.BMGR > 0, out=np.zeros_like(self.BMGR)) # GR grass N concentration (kg N/kgDM)
        self.NDV = np.divide(self.QNDV, self.BMDV, where=self.BMDV > 0, out=np.zeros_like(self.BMDV)) # DV grass N concentration (kg N/kgDM)
        self.NDR = np.divide(self.QNDR, self.BMDR, where=self.BMDR > 0, out=np.zeros_like(self.BMDR)) # DR grass N concentration (kg N/kgDM)
        
        self.LAI = (self.SLA*self.BMGV/10*self.percentageLAM)

        self.ST = np.zeros(self.grid)


    def init_with_height(self):
        """ Initialize the crop biomass with the initial height [m]. """
        self.sward_height = np.full(self.grid, self.inits['InitialHeight']) # sward height
        self.BMGV = self.sward_height*10*self.BDGV # Green vegetative biomass
        self.BMGR = self.sward_height*10*self.BDGR  # Green reproductive biomass
        self.BMDV = self.sward_height*10*self.BDDV  # Dead vegetative biomass
        self.BMDR = self.sward_height*10*self.BDDR  # Dead reproductive biomass


    def init_with_BM(self):
        """ Initialize the crop biomass with the initial biomass [kgDM/ha]. """
        self.BMGV = np.full(self.grid, self.inits['BMGV'])
        self.BMDV = np.full(self.grid, self.inits['BMDV'])
        self.BMGR = np.full(self.grid, self.inits['BMGR'])
        self.BMDR = np.full(self.grid, self.inits['BMDR'])
        self.sward_height = np.maximum.reduce([
            self.BMGV/10/self.BDGV, 
            self.BMGR/10/self.BDGR, 
            self.BMDV/10/self.BDDV, 
            self.BMDR/10/self.BDDR
            ])


    def init_daily_loop(self, day, WD, ET0, day_irr):
        """ 
        Initialize the daily loop. Set the day, the year, the weather data, today's irradiance and the potential evapotranspiration. 
        If the first day of the year, reset ST to zero and initialize the output dictionary for the year.

        Args:
            day: today's date
            day type: datetime object
            WD: weather data (Rain [mm], Avg_temp [°C], Max_Temp [°C])
            WD type: dictionary
            ET0: potential evapotranspiration [mm]
            ET0 type: float
            day_irr: today's irradiance [MJ/m²]
            day_irr type: numpy array of shape grid
        """
        self.day = day
        self.year = str(day.year)
        self.PP = np.full(self.grid, WD['Rain'])
        self.Temp = np.full(self.grid, WD['Avg_temp'])
        self.PARi = day_irr*0.48
        self.ET0 = ET0
        self.Tmax = np.full(self.grid, WD['Max_temp'])

        if self.day.dayofyear == 1:
            self.ST = np.zeros(self.grid)
            self.nyears_data[self.year] = {}
            self.init_one_year_variables()


    def init_one_year_variables(self):
        """ Initialize the output dictionary of each variable to save for the year. """
        for var in self.variables_to_save:
            self.nyears_data[self.year][var] = {}


    def compute_aet(self):
        """Compute actual evapotranspiration (AET) [mm].

        Multiply potential evapotranspiration (ET0) [mm] by an average monthly crop coefficient (Kc) [-].
        From Liu et al. (2017), http://dx.doi.org/10.5194/hess-2016-237.
        """
        month = self.day.month_name()
        self.kc = self.kc_values[month]

        self.AET = self.ET0*self.kc


    def compute_potential_growth(self):
        """Compute potential growth of the crop (PGRO) [kgDM ha^-1].

        Multiply incident photosynthetically active radiation (PARi, MJ m^-2) by maximal radiation use efficiency (RUEmax)  [g DM MJ^-1]
        and a function of leaf area index (LAI) [m^2 m^-2].
        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        self.PGRO = self.PARi*self.RUEmax*(1-np.exp(-0.6*self.LAI))*10


    def compute_st(self,method='T_fixed'):
        """Compute sum of temperature (ST) [°C day] from January 1.

        Args:
            method = method used to compute ST, differs on the source and number of T° thresholds used
                - T_fixed : use parameters Tmin and Tmax from yaml file (default)
                - STICS : use parameters Tmin, Tmax and Tstop from yaml file, linear decrease after Tmax (Brisson et al., 2009 ; ISBN 978-2-7592-0169-3)
                - T_from_PFT : use T0 adn Tlimit from the csv file with PFT_parameters
            method type : str

        T0 or Tmin = minimal temperature for plant growth [°C]. Temp below do not influence ST.
        Tlimit or Tmax = ceiling temperature for plant growth [°C]. Temp above Tlimit do not influence ST. Even linear decrease until Tstop in STICS method.
        Tstop = maximal temperature where no more development and no ST contribution [°C]£
        NB : GRASSIM phenological stages are parametrized with Tmin=0°C
        """
        if method == 'STICS':
            mask_in_range = (self.Temp >= self.Tmin) & (self.Temp <= self.Tmax)
            mask_above_Tmax = (self.Temp > self.Tmax) & (self.Temp < self.Tstop)

            self.ST[mask_in_range] += self.Temp[mask_in_range] - self.Tmin[mask_in_range]
            self.ST[mask_above_Tmax] += ((self.Tmax[mask_above_Tmax] - self.Tmin[mask_above_Tmax]) /
                                         (self.Tmax[mask_above_Tmax] - self.Tstop[mask_above_Tmax]) *
                                         ( self.Temp[mask_above_Tmax] - self.Tstop[mask_above_Tmax]))

        elif method == 'T_from_PFT':
            mask_in_range = (self.Temp >= self.T0) & (self.Temp <= self.Tlimit)
            mask_above_Tlimit = (self.Temp > self.Tlimit)

            self.ST[mask_in_range] += self.Temp[mask_in_range] - self.T0
            self.ST[mask_above_Tlimit] += self.Tlimit - self.T0

        elif method == 'T_fixed' :
            mask_in_range = (self.Temp >= self.Tmin) & (self.Temp <= self.Tmax)
            mask_above_Tmax = (self.Temp > self.Tmax)
            self.ST[mask_in_range] += self.Temp[mask_in_range] - self.Tmin[mask_in_range]
            self.ST[mask_above_Tmax] += self.Tmax[mask_above_Tmax] - self.Tmin[mask_above_Tmax]

    def compute_fAge(self):
        """Compute a function (fage) representing the effect of compartment age (AGE) [°C day] on senescence (SEN) and abscission (ABS) functions.

        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        ratioGV = self.ageGV / self.LLS
        conditions_GV = [ratioGV < 1/3, ratioGV < 1]
        values_GV = [1, 3 * ratioGV]
        self.fageGV = np.select(conditions_GV, values_GV, default=3)
        
        ratioGR = self.ageGR / (self.ST2 - self.ST1)
        conditions_GR = [ratioGR < 1/3, ratioGR < 1]
        values_GR = [1, 3 * ratioGR]
        self.fageGR = np.select(conditions_GR, values_GR, default=3)

        ratioDV = self.ageDV / self.LLS
        conditions_DV = [ratioDV < 1/3, ratioDV < 2/3]
        values_DV = [1, 2]
        self.fageDV = np.select(conditions_DV, values_DV, default=3)

        ratioDR = self.ageDR / (self.ST2 - self.ST1)
        conditions_DR = [ratioDR < 1/3, ratioDR < 2/3]
        values_DR = [1, 2]
        self.fageDR = np.select(conditions_DR, values_DR, default=3)


    def compute_senescence_abscission(self):
        """Compute senescence functions (SEN) [kg DM ha^-1] and abscission functions (ABS) [kg DM ha^-1].

        Multiply biomass (BM) [kgDM ha^-1] by basic senescence/abscission rate (K or Kl) [°C^-1], daily mean temperature (Temp) [°C]
        and a function representing the effect of age (fage).
        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        conditions_ABS = [self.Temp > 0]
        values_ABSDV = [self.KlDV * self.BMDV * self.Temp * self.fageDV]
        values_ABSDR = [self.KlDR * self.BMDR * self.Temp * self.fageDR]

        self.ABSDV = np.select(conditions_ABS, values_ABSDV, default=0)
        self.ABSDR = np.select(conditions_ABS, values_ABSDR, default=0)

        conditions_SEN = [self.Temp > self.T0, self.Temp < 0]
        values_SENGV = [
            self.KGV * self.BMGV * self.Temp * self.fageGV,   # Case: Temp > T0
            self.KGV * self.BMGV * abs(self.Temp)          # Case: Temp < 0
        ]
        values_SENGR = [
            self.KGR * self.BMGR * self.Temp * self.fageGR,   # Case: Temp > T0
            self.KGR * self.BMGR * abs(self.Temp)        # Case: Temp < 0
        ]

        self.SENGV = np.select(conditions_SEN, values_SENGV, default=0)
        self.SENGR = np.select(conditions_SEN, values_SENGR, default=0)


    def compute_N_plant_litter(self):
        """Compute nitrogen content [kgN ha-1] of vegetation undergoing abscission.

        Assume that N concentration of dead material is 0.008 kgN kgDM-1 (cf. PFT parameters value)
        From Ruelle et al. (2018), http://dx.doi.org/10.1016/j.eja.2018.06.010.
        """
        self.N_plant_litter = (self.ABSDV*self.NDV) + (self.ABSDR * self.NDR)


    def compute_fT(self):
        """Compute a growth reduction function (fT) based on daily mean temperature (Temp) [°C].

        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        conditions_fT = [
        self.Temp <= self.T0,                     # Temp <= T0
        self.Temp <= self.T1,                     # Temp <= T1
        self.Temp <= self.T2,                     # Temp <= T2
        self.Temp <= self.Tlimit                  # Temp <= Tlim
            ]
        
        values_fT = [
        0,                                                      # Case: Temp <= T0
        (self.Temp - self.T0) / (self.T1 - self.T0),            # Case: T0 < Temp <= T1
        1,                                                      # Case: T1 < Temp <= T2
        (self.Tlimit - self.Temp) / (self.Tlimit - self.T2),    # Case: T2 < Temp <= Tlim
            ]
        
        self.fT = np.select(conditions_fT, values_fT, default=0)


    def compute_fPARi(self):
        """Compute a growth reduction function (fPARi) based on photosynthetically active radiation (PARi) [MJ m^-2].

        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        conditions_fPARi = [self.PARi <= 5]

        values_fPARi = [
            1,                              # Case: PARi <= 5
        ]

        self.fPARi = np.select(conditions_fPARi, values_fPARi, default=(1 / 22 * -self.PARi) + 27 / 22)

    def compute_fW(self, W, method):
        """Compute a growth reduction function (fW) based on water stress (W) [-].

        Args:
            method : method used
                - 'Jouven2006' , default, from Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
                - 'Bonnard2025', quadratic function not dependent from ET0, from Bonnard et al. (2025), https://doi.org/10.1016/j.eja.2025.127520.
            method type : str
            W: water stress
            W type: Numpy array of shape (grid)
        """

        if method == 'Jouven2006':
            conditions_fW = [
                self.ET0 < 3.81,                        # ET0 < 3.81
                (self.ET0 >= 3.81) & (self.ET0 < 6.35),  # 3.81 <= ET0 < 6.35
            ]

            # Define corresponding values for each condition
            values_fW = [
                np.select(
                    [
                        W < 0.2,                # W < 0.2
                        W < 0.4,                # 0.2 <= W < 0.4
                        W < 0.6,                # 0.4 <= W < 0.6
                    ],
                    [
                        4 * W,                  # W < 0.2
                        0.75 * W + 0.65,        # 0.2 <= W < 0.4
                        0.25 * W + 0.85,        # 0.4 <= W < 0.6
                    ],
                    default=1                           # W >= 0.6
                ),
                np.select(
                    [
                        W < 0.2,                # W < 0.2
                        W < 0.4,                # 0.2 <= W < 0.4
                        W < 0.6,                # 0.4 <= W < 0.6
                        W < 0.8,                # 0.6 <= W < 0.8
                    ],
                    [
                        2 * W,                  # W < 0.2
                        1.5 * W + 0.1,          # 0.2 <= W < 0.4
                        W + 0.3,                # 0.4 <= W < 0.6
                        0.5 * W + 0.6,          # 0.6 <= W < 0.8
                    ],
                    default=W                    # W >= 0.8
                )
            ]

            # Apply np.select for the final result
            self.fW = np.select(conditions_fW, values_fW, default=W)

        elif method == 'Bonnard2025':
            self.fW=(-1.2387 * (W ** 2) + 2.2387 * W - 0.0056)* (18/self.Tmax)
            self.fW = np.clip(self.fW, 0, 1)

    def compute_N_supply(self, Nmin, FNAmax, NSc):
        """Compute potential nitrogen supply of the soil [kgN ha^-1].

        From Bonesmo et Bélanger (2002), https://doi.org/10.2134/agronj2002.3450.

        Args:
            Nmin: soil mineral nitrogen [kgN ha^-1]
            Nmin type: Numpy array of shape (grid)
            FNAmax: maximal soil nitrogen availability factor [-]
            FNAmax type: float
            NSc: soil mineral nitrogen content for maximal N availability [kgN ha^-1]
            NSc type: int
        """
        FNA = FNAmax*(Nmin/NSc)
        FNA = np.clip(FNA, a_min=None, a_max=FNAmax)
        
        self.N_supply = FNA*Nmin


    def compute_fN(self):
        """Compute a growth reduction function (fN) based on crop N status (RNC) [-].

        Compute critical nitrogen plant concentration (Ncrit) [kgN kgDM^-1]
        From Lemaire et al. (1984), http://dx.doi.org/10.1051/agro:19840503.
        Compute maximal nitrogen plant concentration (Nmax) [kgN kgDM^-1]
        From Marino et al. (2004), https://doi.org/10.2134/agronj2004.0601.
        Compute actual nitrogen plant concentration (Nact) [kgN kgDM^-1].
        Compute nitrogen status (RNC) [-] as the ratio of Nact to Ncrit.
        Compute the fN function from the RNC.
        From Bonesmo et Bélanger (2002), https://doi.org/10.2134/agronj2002.3450.
        """
        cut_off_BMGV = 0.05*10*self.BDGV
        cut_off_BMDV = 0.05*10*self.BDGR
        cut_off_BMGR = 0.05*10*self.BDDV
        cut_off_BMDR = 0.05*10*self.BDDR
        cut_off_BM = cut_off_BMGV + cut_off_BMDV + cut_off_BMGR + cut_off_BMDR
        
        BMGV_over5 = np.where(self.BMGV>cut_off_BMGV, self.BMGV-cut_off_BMGV, 0)
        BMGR_over5 = np.where(self.BMGR>cut_off_BMGR, self.BMGR-cut_off_BMGR, 0)
        BMDV_over5 = np.where(self.BMDV>cut_off_BMDV, self.BMDV-cut_off_BMDV, 0)
        BMDR_over5 = np.where(self.BMDR>cut_off_BMDR, self.BMDR-cut_off_BMDR, 0)
        self.BMover5 = np.where(self.BM>cut_off_BM, self.BM-cut_off_BM, 0)

        self.Ncrit = np.where(self.BMover5<=1000, self.a_Ncrit*0.01, self.a_Ncrit*0.01*(self.BMover5/1000)**(-self.b_Ncrit))
        self.Nmax = np.where(self.BMover5<=1000, self.a_Nmax*0.01, self.a_Nmax*0.01*(self.BMover5/1000)**(-self.b_Nmax))
        
        RNCmax = 0.9
        RNCmin = 0.4
        
        self.Nact = np.where(self.BMover5<=0, RNCmin*self.Ncrit, (self.NGV*BMGV_over5+self.NGR*BMGR_over5+self.NDV*BMDV_over5+self.NDR*BMDR_over5)/self.BMover5)
        Nactlim = self.Ncrit*RNCmax
        self.Nact = np.clip(self.Nact, a_min=None, a_max=Nactlim)
        
        self.RNC = (self.Nact/self.Ncrit)
        self.RNC= self.RNC.clip(min=RNCmin, max=RNCmax)
        
        self.fN = 0.99*(1-(3.78*np.exp(-5.36*self.RNC)))
        self.fN = self.fN.clip(min=0, max=1)
        
        self.RNC = 0.4
        self.fN = 1


    def compute_N_demand(self):
        """Compute nitrogen demand (N_demand) [kgN ha^-1].

        Compute fraction of N absorbed remaining in above-ground biomass (FNH) [-].
        Compute N_demand based on the difference between Nmax and Nact.
        From Bonesmo et Bélanger (2002), https://doi.org/10.2134/agronj2002.3450.
        """
        FNHmax = 0.8
        self.FNH = FNHmax * np.maximum(self.FNH_coef1, self.FNH_coef2 * (1 + self.RNC))
        self.N_demand = self.BMover5 * (self.Nmax - self.Nact) / self.FNH


    def compute_N_uptake(self):
        """Compute nitrogen uptake (N_uptake) [kgN ha^-1] as the minimum between N_demand and N_supply.
        """
        self.N_uptake = np.minimum(self.N_demand, self.N_supply)


    def compute_environmental_stress(self):
        """Compute environmental stress function (ENV) influencing actual growth.

        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        self.fWfN = np.minimum(self.fN, self.fW)
        self.ENV = self.fPARi * self.fT * self.fWfN

    def compute_seasonal_effect(self):
        """Compute the seasonal effect (SEA) influencing actual growth.

        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        conditions_SEA = [
            self.ST < self.STmin,                                       # ST < STmin
            (self.ST >= self.STmin) & (self.ST <= self.ST1 - 200),      # STmin <= ST <= ST1 - 200
            (self.ST > self.ST1 - 200) & (self.ST <= self.ST1 - 100),   # ST1 - 200 < ST <= ST1 - 100
            (self.ST > self.ST1 - 100) & (self.ST <= self.ST2),         # ST1 - 100 < ST <= ST2
        ]

        values_SEA = [
            self.minSEA,  # Case: ST < STmin
            (self.maxSEA - self.minSEA) / (self.ST1 - 100 - self.STmin) * (self.ST - self.STmin) + self.minSEA,  # Case: STmin <= ST <= ST1 - 200
            self.maxSEA,  # Case: ST1 - 200 < ST <= ST1 - 100
            (self.minSEA - self.maxSEA) / (self.ST2 - self.ST1) * (self.ST - self.ST1) + self.maxSEA,  # Case: ST1 - 100 < ST <= ST2
        ]

        self.SEA = np.select(conditions_SEA, values_SEA, default=self.minSEA)

    def compute_actual_growth(self):
        """Compute actual growth (GRO) [kgDM ha^-1]

        Multiply potential growth (PGRO) by the environmental stress function (ENV) and the seasonal effect (SEA).
        From Jouven et al. (2006), https://doi.org/10.1111/j.1365-2494.2006.00515.x.
        """
        self.GRO = self.PGRO * self.ENV * self.SEA

        conditions_REP = [
        self.ST < self.ST1,
        (self.ST >= self.ST1) & (self.ST < self.ST2) & np.logical_not(self.apex_grazed) & (self.RNC > 0.35)
        ]

        values_REP = [
            0,  # Case: ST < ST1
            0.25 + ((1 - 0.25) * (self.RNC - 0.35)) / (1 - 0.35),  # Case: ST1 <= ST < ST2, apex_grazed is False, RNC > 0.35
        ]       

        self.REP = np.select(conditions_REP, values_REP, default=0)

        self.GROGV = self.GRO * (1 - self.REP)
        self.GROGR = self.GRO * self.REP
            
    def update_balance(self):
        """Update state and auxiliary variables."""
        self.update_green_biomass()
        self.update_dead_biomass()
        self.update_total_biomass_and_sward_height()
        self.update_age()
        self.update_digestibility()
        self.compute_digestible_organic_matter()
        self.update_nitrogen_content()
        self.update_nitrogen_concentration()

    def update_green_biomass(self):
        """Update green biomass with growth and senescence [kgDM ha^-1]."""
        self.BMGV += self.GROGV - self.SENGV
        self.BMGR += self.GROGR - self.SENGR

    def update_dead_biomass(self):
        """Update dead biomass with senescence and abscission [kgDM ha^-1]."""
        self.BMDV += (1 - self.sigmaGV) * self.SENGV - self.ABSDV
        self.BMDR += (1 - self.sigmaGR) * self.SENGR - self.ABSDR

    def update_total_biomass_and_sward_height(self):
        """Update total biomass and compute sward height [m] from biomass and bulk density [g m^-3]."""
        self.BM = self.BMGV + self.BMGR + self.BMDV + self.BMDR
        self.sward_height = np.maximum.reduce([
            self.BMGV / 10 / self.BDGV,
            self.BMGR / 10 / self.BDGR,
            self.BMDV / 10 / self.BDDV,
            self.BMDR / 10 / self.BDDR
        ])

    def update_apex_grazed (self, cut_height, day, cut_dates) :
        """Update apex_grazed from 0 to one if topping (cut) during reproductive growth (REP>0).
        Once apex_grazed = 1, it remains 1, preventing future reproductive growth.

        Args:
            day: today's date
            day type: datetime object"""

        if day in cut_dates:
            # condition : apex non encore brouté, croissance reproductive en cours, et hauteur > cut_height
            condition = (
                    (self.apex_grazed == 0)
                    & (self.REP > 0)
                    & ((self.BMGR / 10 / self.BDGR) > cut_height)
            )

            self.apex_grazed = np.where(condition, 1, self.apex_grazed)

    def update_age(self):
        """Update age of compartments [°C day] from biomass,growth,senescence, abscission and Temp [kgDM ha^-1]."""
        mask_above_Tmin = self.Temp > self.Tmin

        self.ageGV[mask_above_Tmin] = (
                (self.BMGV[mask_above_Tmin] - self.SENGV[mask_above_Tmin])
                / (self.BMGV[mask_above_Tmin] - self.SENGV[mask_above_Tmin] + self.GROGV[mask_above_Tmin])
                * (self.ageGV[mask_above_Tmin] + self.Temp[mask_above_Tmin])
        )
        self.ageGV = np.maximum(self.ageGV, 0)  #to avoid negatives values because of floating point

        self.ageGR[mask_above_Tmin] = (
                (self.BMGR[mask_above_Tmin] - self.SENGR[mask_above_Tmin])
                / (self.BMGR[mask_above_Tmin] - self.SENGR[mask_above_Tmin] + self.GROGR[mask_above_Tmin])
                * (self.ageGR[mask_above_Tmin] + self.Temp[mask_above_Tmin])
        )
        self.ageGR = np.maximum(self.ageGR, 0)

        self.ageDV[mask_above_Tmin] = (
                (self.BMDV[mask_above_Tmin] - self.ABSDV[mask_above_Tmin])
                / (self.BMDV[mask_above_Tmin] - self.ABSDV[mask_above_Tmin] + (1 - self.sigmaGV) * self.SENGV[mask_above_Tmin])
                * (self.ageDV[mask_above_Tmin] + self.Temp[mask_above_Tmin])
        )
        self.ageDV = np.maximum(self.ageDV, 0)

        self.ageDR[mask_above_Tmin] = (
                (self.BMDR[mask_above_Tmin] - self.ABSDR[mask_above_Tmin])
                / (self.BMDR[mask_above_Tmin] - self.ABSDR[mask_above_Tmin] + (1 - self.sigmaGR) * self.SENGR[mask_above_Tmin])
                * (self.ageDR[mask_above_Tmin] + self.Temp[mask_above_Tmin])
        )
        self.ageDR = np.maximum(self.ageDR, 0)

    def update_digestibility(self):
        """Update digestibility (OMD) [g g^-1] based on age and seasonal temperature."""
        self.OMDGV = self.maxOMDGV - (self.ageGV * (self.maxOMDGV - self.minOMDGV)) / self.LLS

        conditions_OMDGR = [
            self.ST < self.ST1,
            self.ST > self.ST2,
        ]

        values_OMDGR = [
            self.maxOMDGR,
            self.minOMDGR,
        ]

        self.OMDGR = np.select(
            conditions_OMDGR,
            values_OMDGR,
            default=self.maxOMDGR - (self.ageGR * (self.maxOMDGR - self.minOMDGR) / (self.ST2 - self.ST1))
        )

    def compute_digestible_organic_matter(self):
        """Compute digestible organic matter [kgDM ha^-1] from biomass and OMD."""
        self.digestibleOM = (
            self.BMGV * self.OMDGV +
            self.BMGR * self.OMDGR +
            self.BMDV * self.OMDDV +
            self.BMDR * self.OMDDR
        )

    def update_nitrogen_content(self):
        """Update nitrogen content (QN) [kgN ha^-1] based on senescence and abscission."""
        self.QNDV += ((1 - self.sigmaGV) * self.SENGV - self.ABSDV) * self.NDV
        self.QNDR += ((1 - self.sigmaGR) * self.SENGR - self.ABSDR) * self.NDR

        mask = self.GRO > 0.0001
        self.QNGV[mask] += (
            self.N_uptake[mask] * self.FNH * self.GROGV[mask] / self.GRO[mask]
            - self.SENGV[mask] * self.NDV[mask]
        )
        self.QNGV[~mask] -= self.SENGV[~mask] * self.NDV[~mask]

        self.QNGR[mask] += (
            self.N_uptake[mask] * self.FNH * self.GROGR[mask] / self.GRO[mask]
            - self.SENGR[mask] * self.NDR[mask]
        )
        self.QNGR[~mask] -= self.SENGR[~mask] * self.NDR[~mask]

        self.QNGV = self.QNGV.clip(min=0)
        self.QNGR = self.QNGR.clip(min=0)

        TotalplantN = self.QNDV + self.QNDR + self.QNGV + self.QNGR
        self.PropNplant = TotalplantN / self.BM

    def update_nitrogen_concentration(self):
        """Update nitrogen concentration (N) [kgN kgDM^-1] in plant compartments."""
        self.NGV = np.divide(self.QNGV, self.BMGV, where=self.BMGV > 0, out=np.zeros_like(self.BMGV))
        self.NGR = np.divide(self.QNGR, self.BMGR, where=self.BMGR > 0, out=np.zeros_like(self.BMGR))
        self.NDV = np.divide(self.QNDV, self.BMDV, where=self.BMDV > 0, out=np.zeros_like(self.BMDV))
        self.NDR = np.divide(self.QNDR, self.BMDR, where=self.BMDR > 0, out=np.zeros_like(self.BMDR))


    def save_variables(self):
        """ Save the variables in the output dictionary. """
        for var in self.variables_to_save:
            try:
                self.nyears_data[self.year][var][self.day] = copy.deepcopy(getattr(self, var))
            except AttributeError:
                pass
            
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
