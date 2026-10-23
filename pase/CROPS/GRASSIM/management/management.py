import numpy as np 
import pandas as pd
import warnings
from datetime import datetime
from pase.CROPS.GRASSIM.utils.utils import subtract_with_min_values
from pase.DATA_MANAGEMENT.visualization_in_3D import open_pyvista_3D_visualization
import copy 

class Management():
    def __init__(self, grid, config, variables_to_save):
        """
        Initialize the management object.
        Set the grid, the config, the variables to save, the years data, the paddock ids and masks, the current paddock id and mask.
        Check the mandatory parameters depending on the config values.

        Args:
            grid: shape of the grid
            grid type: tuple (x, y)
            config: config of the management
            config type: dictionary
            variables_to_save: names of variables to save in the output dictionary
            variables_to_save type: list
        """
        self.grid = grid
        self.config = config
        self.variables_to_save = variables_to_save
        self.nyears_data = {}
        self.paddock_ids, self.paddock_masks = self.create_paddock_masks()

        self.current_paddock_id = min(self.paddock_masks.keys())
        self.current_mask = self.paddock_masks[self.current_paddock_id]

        # Dictionary linking rule types to required parameters
        self.MANDATORY_PARAMETERS = {
            "cutType": {
                "None":         [],
                "mow":          ["cutDecisionType"],
                "graze":        ["cutDecisionType"]
            },
            "cutDecisionType": {
                "None":         [],
                "dates":        ["biomassRemovalType", "cut_dates"],
                "sward_height": ["biomassRemovalType", "max_sward_height"],
                "frequency":    ["biomassRemovalType", "number_of_cutting_periods"]
            },
            "biomassRemovalType": {
                "None":         [],
                "max_BM":       ["max_BM", "min_available_height", "priority_order"],
                "cut_height":   ["cut_height"]
            },
            "rotationType": {
                "None":         [],
                "dates":        ["rotation_dates"],
                "sward_height": ["max_rotation_sward_height"],
                "frequency":    ["number_of_rotation_periods"]
            },
            "fertilizationType": {
                "None":         [],
                "dates":        ["fert_dates"],
                "days_after_cut": ["cut_to_fert_days"],
            },
        }

        self.validate_management_options()
        self.days_since_cut = -1
        self.days_since_rotation = 0
        self.days_since_fert = 0


    def validate_management_options(self):
        """
        Check mandatory parameters depending on config values and the MANDATORY_PARAMETERS dictionary.
        Raise an error if missing parameters.
        """
        missing_params = []

        for rule_type, dependencies in self.MANDATORY_PARAMETERS.items():
            selected_option = self.config.get(rule_type, None)  # Get value or default to "None"

            # If an option exists in the dictionary, check its required parameters
            if selected_option in dependencies.keys():
                required_params = dependencies[selected_option]

                for param in required_params:
                    # If the required param is another rule type, ensure it's present before checking its params
                    if param not in self.config:
                        missing_params.append(param)

            # Handle dynamic cases separately for grazing and rotation
            if selected_option == "frequency":
                dynamic_keys = {
                    "number_of_cutting_periods": ("cutting", "cutting_start_", "cutting_end_", "cutting_frequency_"),
                    "number_of_rotation_periods": ("rotation", "rotation_start_", "rotation_end_", "rotation_frequency_"),
                }
                for key, (prefix, start_key, end_key, freq_key) in dynamic_keys.items():
                    if key in self.config:
                        try:
                            n = int(self.config[key])
                            for i in range(1, n + 1):
                                for param in [f"{start_key}{i}", f"{end_key}{i}", f"{freq_key}{i}"]:
                                    if param not in self.config:
                                        missing_params.append(param)
                        except (ValueError, KeyError):
                            missing_params.append(f"Invalid or missing value for {key} (should be an integer)")
        
        if missing_params:
            raise ValueError(f"Missing required configuration parameters: {', '.join(missing_params)}")
        

    def init_daily_loop(self, day, crop, soil):
        """
        Initialize the daily loop.
        Set the day and the year.
        Initialize the fertilization and exported quantities.
        If the first day of the year, initialize the output dictionary for the year.
        Compute the cutting, rotation and fertilization decisions for today.
        Args:
            day: today's date
            day type: datetime object
            crop: spatialized crop 
            crop type: Plants object
            soil: spatialized soil
            soil type: Soil object
        """
        self.day = day
        self.year = str(day.year)
        self.fert_org = 0
        self.NH3volatfactor=0
        self.percentageofNmin=0
        self.fert_min = 0
        self.exported_BM = np.zeros(self.grid)
        self.exported_digestibleOM = np.zeros(self.grid)
        self.exported_N = np.zeros(self.grid)


        if self.day.dayofyear == 1:
            self.nyears_data[self.year] = {}
            self.init_one_year_variables()
            self.cut_dates = self.get_cut_dates()
            self.cut_periods = self.get_cut_periods()
            self.rotation_dates = self.get_rotation_dates()
            self.rotation_periods = self.get_rotation_periods()
            self.fert_dates = self.get_fert_dates()
            self.fert_periods = self.get_fert_periods()
            self.cum_exported_BM = np.zeros(self.grid)

        self.cut_today_ = self.cut_today(day, crop)
        self.fert_today_ = self.fert_today(day)
        self.rotate_today_ = self.rotate_today(day, crop)

        if self.cut_today_:
            crop.update_apex_grazed(
                cut_height=self.config.get('cut_height', np.nan),
                day=day,
                cut_dates=self.cut_dates
            )

        if self.rotate_today_:
            self.update_paddock()
        if self.cut_today_:
            self.cut(crop, soil)
        if self.fert_today_:
            self.fertilize()


    def init_one_year_variables(self):
        """ Initialize the output dictionary of each variable to save for the year. """
        for var in self.variables_to_save:
            self.nyears_data[self.year][var] = {}


    def cut_today(self, day, crop) -> bool:
        """
        Compute the cutting decision for today depending on the config values.
        Args:
            day: today's date
            day type: datetime object
            crop: spatialized crop 
            crop type: Plants object
        Returns:
            cutting decision for today
            cutting decision type: boolean
        """
        if self.config['cutDecisionType'] == "None":
            return False
        
        elif self.config['cutDecisionType'] == "dates":
            if day not in self.cut_dates:
                if self.days_since_cut >= 1:
                    self.days_since_cut += 1
                    return False
                else :
                    return False
            else:
                self.days_since_cut = 1
                return True
            
        elif self.config['cutDecisionType'] == "frequency":
            for n in range(1, self.config['number_of_cutting_periods'] + 1):
                if self.cut_periods['start'][n] <= day <= self.cut_periods['end'][n]: # If day is in a cutting period
                    if self.days_since_cut < self.cut_periods['frequency'][n]:
                        if self.days_since_cut >= 1:
                            self.days_since_cut += 1
                            return False
                        else :
                            self.days_since_cut = 1
                            return True
                    else:
                        self.days_since_cut = 1 # cut if last cut happened more than (self.cut_periods['frequency'][n]) days ago
                        return True
            if self.days_since_cut >= 1:
                self.days_since_cut += 1
                return False
            else:
                return False
                    
        elif self.config['cutDecisionType'] == "sward_height":
            mean_paddock_sward_height = np.mean(crop.sward_height[self.current_mask])
            if mean_paddock_sward_height < self.config['max_sward_height']:
                if self.days_since_cut >= 1:
                    self.days_since_cut += 1
                    return False
                else:
                    return False
            else:
                self.days_since_cut = 1
                return True


    def rotate_today(self, day, crop) -> bool:
        """
        Compute the rotation decision for today depending on the config values.
        Args:
            day: today's date
            day type: datetime object
            crop: spatialized crop 
            crop type: Plants object
        Returns:
            rotation decision for today
            rotation decision type: boolean
        """
        if self.config['rotationType'] == "None":
            return False
        
        elif self.config['rotationType'] == "dates":
            if day not in self.rotation_dates:
                self.days_since_rotation += 1
                return False
            else:
                self.days_since_rotation = 1
                return True
            
        elif self.config['rotationType'] == "frequency":
            for n in range(1, self.config['number_of_rotation_periods'] + 1):
                if self.rotation_periods['start'][n] <= day <= self.rotation_periods['end'][n]:
                    if self.days_since_rotation < self.rotation_periods['frequency'][n]:
                        self.days_since_rotation += 1
                        return False
                    else:
                        self.days_since_rotation = 1
                        return True
            self.days_since_rotation += 1
            return False
                    
        elif self.config['rotationType'] == "sward_height":
            mean_paddock_sward_height = np.mean(crop.sward_height[self.current_mask])
            if mean_paddock_sward_height > self.config['max_rotation_sward_height']:
                self.days_since_rotation += 1
                return False
            else:
                self.days_since_rotation = 1
                return True
            

    def fert_today(self, day) -> bool:
        """
        Compute the fertilization decision for today depending on the config values.
        Args:
            day: today's date
            day type: datetime object
        Returns:
            fertilization decision for today
            fertilization decision type: boolean
        """
        if self.config['fertilizationType'] == "None":
            return False
        
        elif self.config['fertilizationType'] == "dates":
            if day not in self.fert_dates:
                self.days_since_fert += 1
                return False
            else:
                self.days_since_fert = 1
                return True
        
        elif self.config['fertilizationType'] == 'cut_to_fert_days':
            try:
                if self.days_since_cut == self.config['cut_to_fert_days']:
                    self.days_since_fert = 1
                    return True
                else:
                    self.days_since_fert += 1
                    return False
            except TypeError:
                return False
            

    def get_cut_dates(self):
        """
        Get the cutting dates.
        """
        if self.config['cutDecisionType'] == "dates":
            return pd.to_datetime([d + '-' + str(self.year) for d in self.config['cut_dates']], format='%d-%m-%Y')
        else:
            return []
        

    def get_rotation_dates(self):
        """
        Get the rotation dates.
        """
        if self.config['rotationType'] == "dates":
            return pd.to_datetime([d + '-' + str(self.year) for d in self.config['rotation_dates']], format='%d-%m-%Y')
        else:
            return []
        

    def get_fert_dates(self):
        """
        Get the fertilization dates.
        """
        if self.config['fertilizationType'] == "dates":
            return pd.to_datetime([d + '-' + str(self.year) for d in self.config['fert_dates']], format='%d-%m-%Y')
        else:
            return []
        
    
    def get_cut_periods(self):
        """
        Get the cutting periods.
        """
        cut_periods = {}
        cut_periods['start'] = {}
        cut_periods['end'] = {}
        cut_periods['frequency'] = {}

        if self.config['cutDecisionType'] == "frequency":
            for n in range(1, self.config['number_of_cutting_periods'] + 1):
                start = self.config['cutting_start_'+str(n)]
                end = self.config['cutting_end_'+str(n)]

                cut_periods['start'][n] = pd.to_datetime(start + '-' + str(self.year), format='%d-%m-%Y')
                cut_periods['end'][n] = pd.to_datetime(end + '-' + str(self.year), format='%d-%m-%Y')
                cut_periods['frequency'][n] = self.config['cutting_frequency_'+str(n)]

        return cut_periods
    
    def get_rotation_periods(self):
        """
        Get the rotation periods.
        """
        rotation_periods = {}
        rotation_periods['start'] = {}
        rotation_periods['end'] = {}
        rotation_periods['frequency'] = {}

        if self.config['rotationType'] == "frequency":
            for n in range(1, self.config['number_of_rotation_periods'] + 1):
                start = self.config['rotation_start_'+str(n)]
                end = self.config['rotation_end_'+str(n)]

                rotation_periods['start'][n] = pd.to_datetime(start + '-' + str(self.year), format='%d-%m-%Y')
                rotation_periods['end'][n] = pd.to_datetime(end + '-' + str(self.year), format='%d-%m-%Y')
                rotation_periods['frequency'][n] = self.config['rotation_frequency_'+str(n)]

        return rotation_periods
    
    def get_fert_periods(self):
        """
        Get the fertilization periods.
        """
        fert_periods = {}
        fert_periods['start'] = {}
        fert_periods['end'] = {}
        fert_periods['frequency'] = {}

        if self.config['fertilizationType'] == "frequency":
            for n in range(1, self.config['number_of_fert_periods'] + 1):
                start = self.config['fert_start_'+str(n)]
                end = self.config['fert_end_'+str(n)]

                fert_periods['start'][n] = pd.to_datetime(start + '-' + str(self.year), format='%d-%m-%Y')
                fert_periods['end'][n] = pd.to_datetime(end + '-' + str(self.year), format='%d-%m-%Y')
                fert_periods['frequency'][n] = self.config['fertilization_frequency_'+str(n)]

        return fert_periods
    

    def create_paddock_masks(self):
        """
        Create the paddock masks based on the paddock map.
        """
        if "paddock_map" in self.config:
            paddock_map = np.array(self.config["paddock_map"])  # ex [1, 1, 1, 2, 2, 2]
            paddock_ids = np.unique(paddock_map)
            return paddock_ids, {pid: paddock_map == pid for pid in paddock_ids}
        return [1], {1:np.full(self.grid, True)} # default : only one full paddock
    

    def update_paddock(self):
        """
        Rotation : Update the current paddock.
        """
        paddock_ids = sorted(self.paddock_masks.keys())
        current_index = paddock_ids.index(self.current_paddock_id)
        self.current_paddock_id = paddock_ids[(current_index + 1) % len(paddock_ids)]
        self.current_mask = self.paddock_masks[self.current_paddock_id]


    def cut(self, crop, soil):
        """
        Cut the crop depending on the config values. 
        If the biomass removal type is 'cut_height', the crop is cut to the cut_height.
        If the biomass removal type is 'max_BM', a maximum biomass is removed with the subtract_with_min_values() function.

        Args:
            crop: spatialized crop
            crop type: Plants object
            soil: spatialized soil
            soil type: Soil object
        """
        compartments = ['GV', 'DV', 'DR', 'GR']
        if self.config['biomassRemovalType'] == 'cut_height':
            for compartment in compartments:
                cropBM = getattr(crop, f'BM{compartment}')
                cutBM = cropBM.copy()
                cutBM[self.current_mask] = self.config['cut_height'] * 10 * getattr(crop, f'BD{compartment}')
                resBM = np.minimum(cropBM, cutBM)
                setattr(crop, f'resBM{compartment}', resBM)
                setattr(crop, f'resQN{compartment}', resBM * getattr(crop, f'N{compartment}'))

        elif self.config['biomassRemovalType'] == 'max_BM':
            resBMs = []
            BMs_to_cut = []
            min_cutBMs = []
            self.max_BM = self.config['max_BM']
            self.min_available_height = self.config['min_available_height']

            for compartment in self.config['priority_order']:
                resBMs.append(getattr(crop, f'BM{compartment}').copy())
                BMs_to_cut.append(getattr(crop, f'BM{compartment}')[self.current_mask])
                min_cutBMs.append(self.min_available_height *10 * getattr(crop, f'BD{compartment}'))

            cutBMs = subtract_with_min_values(input_list=BMs_to_cut, amount=self.max_BM, min_values=min_cutBMs)

            for i in range(len(resBMs)):
                resBMs[i][self.current_mask] = cutBMs[i]

            for i, compartment in enumerate(self.config['priority_order']):
                setattr(crop, f'resBM{compartment}', resBMs[i])
                setattr(crop, f'resQN{compartment}', resBMs[i] * getattr(crop, f'N{compartment}'))

        crop.sward_height[self.current_mask] = np.maximum.reduce([crop.resBMGV/10/crop.BDGV, crop.resBMGR/10/crop.BDGR, crop.resBMDV/10/crop.BDDV, crop.resBMDR/10/crop.BDDR])[self.current_mask]
        self.exported_BM = crop.BMGV - crop.resBMGV + crop.BMDV - crop.resBMDV + crop.BMGR - crop.resBMGR + crop.BMDR - crop.resBMDR
        self.exported_digestibleOM = (crop.BMGV - crop.resBMGV)*crop.OMDGV + (crop.BMDV - crop.resBMDV)*crop.OMDDV + (crop.BMGR - crop.resBMGR)*crop.OMDGR + (crop.BMDR - crop.resBMDR)*crop.OMDDR
        self.exported_N = crop.QNGV - crop.resQNGV + crop.QNDV - crop.resQNDV + crop.QNGR - crop.resQNGR + crop.QNDR - crop.resQNDR
        self.cum_exported_BM += self.exported_BM
        
        for compartment in compartments:
            setattr(crop, f'BM{compartment}', getattr(crop, f'resBM{compartment}')) # update BM of compartments
            setattr(crop, f'QN{compartment}', getattr(crop, f'resQN{compartment}')) # update QN of compartments
        crop.BM = crop.BMGV + crop.BMGR + crop.BMDV + crop.BMDR 
        crop.digestibleOM = crop.BMGV * crop.OMDGV + crop.BMGR * crop.OMDGR + crop.BMDV * crop.OMDDV + crop.BMDR * crop.OMDDR

        if self.config['cutType'] == "graze":
            # Add N from dung and urine to soil based on the amount that was exported (Ruelle et al., 2018)
            Ndung = 0.3 * 0.7 * self.exported_N
            Nurine = 0.7 * 0.7 * self.exported_N

            Ndung_to_Nmin = Ndung * 0.22 
            Ndung_to_Norg = Ndung * 0.75 
            Nurine_to_Nmin = Nurine * 0.85

            soil.Nmin += Ndung_to_Nmin + Nurine_to_Nmin
            soil.Norg += Ndung_to_Norg


    def fertilize(self):
        """
        Fertilize the crop depending on the config values.
        """
        if "fert_org" in self.config:
            self.fert_org += self.config['fert_org']
            self.NH3volatfactor +=self.config['NH3volatfactor']
            self.percentageofNmin +=self.config['percentageofNmin']

        if "fert_min" in self.config:
            self.fert_min += self.config['fert_min']
        
        if not "fert_org" in self.config and not "fert_min" in self.config:
            warnings.warn(f"{self.day} - No 'fert_org' nor 'fert_min' in config. No fertilizer added.")


    def save_variables(self):
        """
        Save the variables in the output dictionary.
        """
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
