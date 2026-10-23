# Gras-Sim model (Kokah et al., 2023)
DOI: 10.1016/j.jafr.2023.100875

# Configuration Guide

## Save variables
Runtime objects are not saved in the results dictionnaries. Only variables specified in https://gitlab.uliege.be/deal-public/pase/-/blob/main/INPUTS/CROPS/GRASSIM/variables_to_save.yml (or other path specified in [the config file](https://gitlab.uliege.be/deal-public/pase/-/blob/main/INPUTS/CROPS/config/grassim_example.yml)) will be saved.

`variables_to_save.yml` should have 3 fields : `soil_variables`, `crop_variables` and `management_variables`, containing attribute names of classes `Soil`, `Plants` and `Management`, respectively.

## Management Configuration (Refer to `management_dates_example.yml`)
This YAML file defines management practices such as cutting, rotation, and fertilization.

### 1. Cutting Management (`cutType`)
Determines how biomass is removed:

- `None`: No cutting occurs.
- `graze`: Biomass is grazed, with nitrogen restitution proportional to the exported (eaten) nitrogen content.
- `mow`: Biomass is mowed with no nitrogen restitution.

#### Cutting Decision (`cutDecisionType`)
Specifies when cutting takes place:

- `None`: No cutting.
- `dates`: Cutting occurs on specified dates.
  - Requires:
    - `cut_dates` (list of strings in `dd-mm` format, e.g., `['15-04', '15-05']`).
- `sward_height`: Cutting is triggered when sward height exceeds a threshold.
  - Requires:
    - `max_sward_height` (meters).
- `frequency`: Cutting follows a fixed schedule.
  - Requires:
    - `number_of_cutting_periods`.
  - Additional parameters for each period:
    - `cutting_start_X` (dd-mm format): Start date.
    - `cutting_end_X` (dd-mm format): End date.
    - `cutting_frequency_X` (days): Frequency of cutting.

#### Biomass Removal Type (`biomassRemovalType`)
Defines the extent of biomass removal:

- `None`: No biomass is removed.
- `max_BM`: Removes a fixed maximum amount of biomass per day, simulating maximum grazing capacity based on animal load.
  - Requires:
    - `max_BM` (kg/ha): Maximum biomass removal per day.
    - `min_available_height` (meters): Minimum height at which biomass is available; cutting (grazing) is not possible below this height.
- `cut_height`: Cuts grass to a specified height, removing all biomass above it.
  - Requires:
    - `cut_height` (meters).

### 2. Rotation Management (`rotationType`)
Specifies when rotation occurs :
* `None` : No rotation.
* `dates` : Rotation happens on specifc dates.
    * Requires : 
        - `rotation_dates` (list of string dd-mm format. Ex : ['15-04', '15-05'])
* `sward_height` : Rotation happens when sward_height exceeds a threshold.
    * Requires : 
        - `max_sward_height` (m)
* `frequency` : Rotation follows a fixed schedule.
    * Requires : 
        - `number_of_rotation_periods`
    * Additional required parameters per period : 
        - `rotation_start_X` (dd-mm format) : Start date. 
        - `rotation_end_X` (dd-mm format) : End date.
        - `rotation_frequency_X` (days) : Rotation frequency.

### 3. Fertilization Management (`rotationType`)
Specifies when rotation occurs :
* `None` : No rotation.
* `dates` : Rotation happens on specifc dates.
    * Requires : 
    - `fert_dates` (list of string dd-mm format. Ex : ['15-04', '15-05'])
* `days_after_cut` : Fertilization occurs a set number of days after cutting.
    * Requires : 
        - `cut_to_fert_days` (days) : Number of days to wait after cutting for fertilization.
#### Additional Fertilization Parameters:
* `fert_org` (kg/ha) : Organic nitrogen amount added to soil.
* `fert_min` (kg/ha) : Mineral nitrogen amount added to soil.

### 4. Paddock Configuration (`paddock_map`)
Defines paddock layout for cutting and rotation :

* List if paddock IDs. Cells with the same ID are grouped in a single paddock (Ex: [1, 1, 1, 2, 2, 2] -> two paddocks with 3 cells each). Must be the same lenght as `grid` (shape of the irradiance input). 

* If omitted, the default is one full paddock (`grid`*[1]).

## PFT parameters (see Parameters_values_PFT.csv)

| Parameter Name     | Units        | Description                                       |Example|
|--------------------|--------------|---------------------------------------------------|---------| 
| PFT              | -              | PFT type abreviation (letter)                         | A |
| SLA              | m²/g         | Specific Leaf Area.                                   |0.023|
| percentageLAM    | [-]            | Percentage of laminae                                 |0.68| 
| ST1              | °C.d       | Initial reproductive growth temperature               |500|     
| ST2              | °C.d       | End reproductive growth T                             |900| 
| maxSEA           | [-]            | maximum seasonal effect                               |1| 
| minSEA           | [-]            | minimum seasonal effect                               |0.8| 
| LLS              | °C.d       | leaf lifespan                                         |800| 
| maxOMDGV         | [-]            | Max organic matter digestibility of green vegetative  |0.9| 
| minOMDGV         | [-]            | Min organic matter digestibility of green vegetative  |0.75| 
| maxOMDGR         | [-]            | Max organic matter digestibility of green reproductive|0.9| 
| minOMDGR         | [-]            | Min organic matter digestibility of green reproductive|0.65| 
| BDGV             | g/m³         | bulk density of green vegetative                      |800 | 
| BDDV             | g/m³         | bulk density of dead vegetative                       |500| 
| BDGR             | g/m³         | bulk density of green reproductive                    |300| 
| BDDR             | g/m³         | bulk density of dead reproductive                     |150| 
| RUEmax           | g/MJ         | Maximum radiation use efficiency                      |2.6| 
| sigmaGV          | [-]            | Critical nitrogen concentration alpha coefficient     |0.4| 
| sigmaGR          | [-]            | Critical nitrogen concentration beta coefficient      |0.2| 
| T0               | °C           | Minimum mean air temperature for growth               |4| 
| T1               | °C           | Plateau mean air temperature                          |10| 
| T2               | °C           | Mean air temperature at which growth starts decreasing|20| 
| Tlimit           | °C           | Mean air temperature at which growth ends             |25| 
| STmin            | °C.d        | Minimum sum of temperature for growth                 |200| 
| KGV              | °C-1         | Basic senescence rate for green vegetative            |0.0002| 
| KGR              | °C-1         | Basic senescence rate for green reproductive          |0.0001| 
| KlDV             | °C-1         | Basic senescence rate for dead vegetative             |0.0001| 
| KlDR             | °C-1         | Basic senescence rate for dead reproductive           |0.0005| 
| OMDDV            | [-]            | Organic matter digestibility of dead vegetative       |0.4| 
| OMDDR            | [-]            | Organic matter digestibility of dead reproductive     |0.45|
| Tref             | °C       | Reference T for fT (nitrogen soil activity)               |15| 
| K                | [-]       | parameter for fT (nitrogen soil activity)                  |0.115| 
| percentageofNmin | [-]       | Proportion of N min in the organic fertilizer              |0.02| 
| NH3volatfactor   | [-]       | Proportion of volatile (lost) NH3 depending on the quality of the fertiliser application methods and conditions |0.045| 
| a_Ncrit          | [-]       | Critical nitrogen concentration alpha coefficient          |4.8| 
| b_Ncrit          | [-]       | Critical nitrogen concentration beta coefficient           |0.32| 
| a_Nmax           | [-]       | Maximum plant N proportion at 1000 kg/ha                   |6.145| 
| b_Nmax           | [-]       | Maximum pattern of decrease of N proportion during increased shoot biomass  |0.418| 
| FNH_coef1        | [-]       | coefficient 1 of the Maximum value of N fraction absorbed that remains in the above-ground biomass |0.5| 
| FNH_coef2        | [-]       | coefficient 2 of the Maximum value of N fraction absorbed that remains in the above-ground biomass |0.45|

## Initialization
### Plants (see crop_init_example.yml)
| Variable Name     | Units         | Description                                                   |Example|
|-------------------|---------------|---------------------------------------------------------------|-------| 
|BM_init_type       | [-]           |Type of biomass initialization. "InitialHeight" or "InitialBM".|"InitialBM"|
|InitialHeight      | m             |Initial sward height. Required if "InitialHeight".             |0.05|
|BMGV               | kg/ha         |Initial green vegetative biomass. Required if "InitialBM"      |1000|
|BMDV               | kg/ha         |Initial dead vegetative biomass. Required if "InitialBM"       |250|
|BMGR               | kg/ha         |Initial green reproductive biomass. Required if "InitialBM"    |0|
|BMDR               | kg/ha         |Initial dead reproductive biomass. Required if "InitialBM"     |0|
|ageGV              | °C.d          |Initial green vegetative biomass mean age.                     |0|
|ageDV              | °C.d          |Initial dead vegetative biomass mean age.                      |0|
|ageGR              | °C.d          |Initial green reproductive biomass mean age.                   |0|
|ageDR              | °C.d          |Initial dead reproductive biomass mean age.                    |0|
|apex_grazed        | boolean       |1 if reproductive apex is grazed. 0 else.                      |0|
|Tmin               | °C            |Base temperature for ST calculation.                           |0|
|Tmax               | °C            |Maximum temperature for ST calculation.                        |18|

### soil (see soil_init_example.yml)
| Variable Name     | Units         | Description                                       |Example|
|-------------------|---------------|---------------------------------------------------|-------| 
|not_runoff         | mm            | Water above soil                                  |0      |
|Nmin               | kg/ha         | Mineral nitrogen in soil                          |50     |
|Norg               | kg/ha         | Organic nitrogen in soil                          |50     |
|sand               | % volume      | soil sand proportion                              |15     |
|clay               | % volume      | soil clay proportion                              |10     |
|coarse             | % volume      | soil coarse fragments proportion                  |10     |
|org                | % mass        | soil organic matter content                       |10     |
|soil_depth         | mm            | soil depth                                        |500    |
|max_soil_depth     | mm            | maximum useful soil depth                         |1000   |
|albedo             | [-]           | soil albedo                                       |0.2    |

