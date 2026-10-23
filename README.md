> ## ⚠️ Fork — travail de stage sur le pilotage des panneaux
>
> **Ce dépôt n'est pas le dépôt officiel de PASE.** C'est un fork personnel de
> **PASE 2.0.0**, développé par Hugo Lange durant un stage au **G2ELab**, pour
> étudier l'impact du **pilotage de l'inclinaison des panneaux** (tracking /
> anti-tracking / stratégies mixtes) sur les rendements énergétique et agricole.
>
> ### 👉 Vous voulez juste essayer le programme ?
>
> Suivez le **[GUIDE_UTILISATION.md](GUIDE_UTILISATION.md)** (aussi disponible en
> [PDF](GUIDE_UTILISATION.pdf)) : il explique pas à pas, **sans prérequis en
> informatique**, comment installer et lancer une comparaison de stratégies de
> pilotage. Comptez ~45 min la première fois, puis 30 s par simulation.
>
> - **Dépôt officiel de PASE** : https://gitlab.uliege.be/deal-public/pase
> - **Ce qui a été ajouté ici** : voir [`NOTES/`](NOTES/) — en particulier
>   [`NOUVEAUTES_COMPARAISON_PILOTAGE.md`](NOTES/NOUVEAUTES_COMPARAISON_PILOTAGE.md)
>   (présentation), [`MODIFICATIONS_PILOTAGE.md`](NOTES/MODIFICATIONS_PILOTAGE.md)
>   (documentation technique) et
>   [`SYNTHESE_RESULTATS.md`](NOTES/SYNTHESE_RESULTATS.md) (résultats chiffrés).
> - **Retrouver toutes les modifications** : `grep -rn "HUGO - PILOTAGE" .`
>   Seuls 2 fichiers PASE existants ont été modifiés (`configuration.py`,
>   `production.py`) ; tout le reste est en fichiers nouveaux.
> - **Ces travaux n'ont pas été soumis à l'équipe PASE** et n'engagent qu'eux-mêmes.
>
> PASE est distribué sous [licence MIT](LICENSE) — Copyright (c) 2020-2024
> University of Liège, Digital Energy and Agriculture Lab (DEAL). Cette mention et
> le fichier `LICENSE` sont conservés conformément à ses termes.

---

# PASE Framework Overview

The **PASE** framework is designed to simulate an agrivoltaic system, calculating both photovoltaic and agricultural outputs. It leverages the HDKR model to compute the global tilted irradiance on the PV panels and uses a ray casting algorithm to estimate the light reaching crops beneath the panels. These irradiance data are then used with crop models to simulate crop growth and yield.

## Binder
Try the PASE notebooks on Binder (**no installation required**):

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/git/https%3A%2F%2Fgitlab.uliege.be%2Fdeal-public%2Fpase/152-pase-training-session)

Note: Currently, the above Binder button points to a feature branch. 
The link is subject to change in the near future, as we continue improving the framework and notebooks, as well as keep creating new notebooks. 
Visit regularly to access the most up-to-date versions. 

## Installation

### Install with pip

PASE is published on PyPI as **`pase-agrivoltaics`** — note the distribution name
differs from the import name (as with `scikit-learn` / `sklearn`):

```bash
pip install pase-agrivoltaics
```

```python
import pase
```

This installs the core library: the PV, light and environment modules, plus the
pure-Python **SIMPLE** and **GRASSIM** crop models. The **STICS** and
**CPlantBox** crop backends are not distributed on PyPI (they rely on external
tools) and are set up separately. To run the bundled **examples and notebooks**,
or for a full development environment, use the conda setup below — it also brings
the repository's `INPUTS/` and example scripts.

### Install with conda
> **⚠ Breaking change (issue [#256](https://gitlab.uliege.be/deal-public/pase/-/issues/256), July 2026):** the conda environment files were rebuilt: Python `3.10` → `3.12`, `pyembree` replaced by `embreex`, and the `pyvista`/`vtk`/`pvlib`/`trimesh` pins were updated. This pulls in pandas 2.2+, which removed the uppercase `"H"` hourly frequency alias in favor of lowercase `"h"`. **If your own scripts or notebooks call PASE functions with `freq="H"`** (e.g. weather-data resampling) **or use pandas directly with `"H"`**, update them to `freq="h"` or they will error after rebuilding your environment. See the wiki's [Installation](https://gitlab.uliege.be/deal-public/pase/-/wikis/documentation/installation) page for full details.

The repository provides environment files for setting up a conda virtual environment with all necessary dependencies. There are two separate files:

- One for Windows users (`environment_windows.yml`)
- One for Unix-based systems (macOS and GNU/Linux, such as Ubuntu, Debian, etc.) (`environment_unix.yml`)



If you haven’t installed Conda, we recommend following the [Conda installation guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). Here are some options to consider:

- **Good option:** Install **Anaconda** for a comprehensive installation.
- **Better option:** Install **Miniconda** for a lighter, customizable setup.
- **Best option:** Install **Miniforge** (optimized for Conda-forge) and consider using [Mamba](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html), which is faster and more efficient than Conda.

### Windows Installation

1. Create the `pase` virtual environment:
   
   ```bash
   conda env create -f environment_windows.yml
   ```

2. Activate the environment (the name comes from the `name:` field in the yml file, currently `pase-2026-07`; feel free to override it at creation time with `conda env create -f environment_windows.yml -n <your-name>`):
   
   ```bash
   conda activate pase-2026-07
   ```

3. The framework is now ready for use (for advanced crop modeling, see section [Installing JavaStics](#installing-javastics)).

### Unix-based Installation

1. Create the `pase` virtual environment:
   
   ```bash
   conda env create -f environment_unix.yml
   ```

2. Activate the environment (the name comes from the `name:` field in the yml file, currently `pase-2026-07`; feel free to override it at creation time with `conda env create -f environment_unix.yml -n <your-name>`):
   
   ```bash
   conda activate pase-2026-07
   ```

3. The framework is now ready for use (for advanced crop modeling, see section [Installing JavaStics](#installing-javastics)).

## Installing JavaStics

Due to license incompatibilities, the JavaStics 1.5.1 executable is not included in the PASE repository.

If you want to use the crop model STICS, download JavaStics 1.5.1 : https://stics.inrae.fr/telechargement and place the executable "JavaSticsCmd.exe" under INPUTS/CROPS/STICS.

## Getting Started

### Quick start

New users should get familiar with PASE via the `example.py` script. No coding is required to run it and visualize results.

To easily configure the PASE framework, only modify the input files with `Example1`in their names (e.g. `Example1_AV.yaml`). These files are located in the **INPUTS** folders. There are three main types of files:

1. **General and Location Parameters:** configure the location, time settings, weather data, and simulation parameters for a photovoltaic and agrivoltaic system. It sets the location name, time zone, coordinates (latitude, longitude, altitude), and options for retrieving weather data from PvGis or a local file. The user specifies the simulation years, with options for daily or hourly weather data. The precision level of sun position calculations ranges from monthly averages to daily specifics. It also defines a zone of interest with x and y boundaries and increments for light and crop modeling in the simulation. These files are ocated in **INPUTS/SCENARIOS**.
2. **Agrivoltaic Configuration Files:** configures the layout and orientation of PV panel blocks within a photovoltaic installation. It sets the number of panels along each axis of a block, the spacing between them, and their tilt. It also defines the number and spacing of blocks across the installation, their height from the ground, and rotation parameters. Additionally, it includes settings for modules with two facets and central azimuth orientation. These parameters control the arrangement and positioning of the PV panel arrays in the simulation.. These files are ocated in **INPUTS/AV_CENTRAL**.
3. **Modules Configuration files**: Configure key properties of a PV panel for simulation, including its dimensions, peak power output, and whether it is bifacial. It also specifies if the panel has thickness and includes a 3D model file. These settings define the panel’s physical and operational characteristics in the simulation environment. These files are ocated in **INPUTS/PV_MODULES**.

Each parameter in these files includes detailed information such as:

- **Value Type:** Specifies the type of input required (e.g., integer, string, etc.).
- **Limits:** Provides acceptable ranges for the parameter values.
- **Unit:** Indicates the unit of measurement.
- **Definition:** Brief explanation of the parameter to clarify its purpose.

To update a parameter, change only the field labeled **"Value:"**. This helps ensure consistent formatting and preserves the contextual information about each parameter.

## PASE Workflow Overview

The PASE framework operates in three main steps:

1. **Agrivoltaic System Configuration**
2. **Microclimate Modeling**
3. **Photovoltaic and Crop Production Calculation**

You can find an example workflow in the `example.py` file.

### 1. Agrivoltaic System Configuration

#### Data Management Module:

The data management module in PASE includes the `YAML_Inputs_provider` class, 
found in the `yaml_inputs_provider.py` module, which reads YAML input files and 
converts them into dictionaries. This class features various methods to validate
user-entered values and to identify any anomalies present. 

Additionally, the `Weather_data` class processes weather data provided in CSV 
format, converting it into Pandas DataFrames or importing it through the 
[PVGIS](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en) class based on user-defined location and time parameters. 
The resulting weather DataFrames are organized in a dictionary by year. 
Since the [PVGIS](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en) class does not supply rainfall and air vapor pressure 
data, users must provide a separate daily data file for these parameters if 
they are needed for the simulations. 

See the wiki page on [Daily weather files](https://gitlab.uliege.be/deal-public/pase/-/wikis/documentation/tutorial#daily-weather-files---precipitation-and-vapour-pressure-data) 
for more information on the contents and structure of the data file for precipitation and vapor pressure.

#### Agrivoltaic System Configuration Module:

The agrivoltaic system configuration module in PASE utilizes the PyVista library, which is a Python wrapper for VTK, to create 3D scenes primarily featuring photovoltaic (PV) installations and the ground. [PyVista]([https://docs.pyvista.org/](https://docs.pyvista.org/)) employs a PolyData object for creating 3D geometries by defining vertex coordinates and assembling them into faces. It also supports importing 3D geometry from various formats, such as .obj, .ply, and .stl, which can be created using Computer-Aided Design (CAD) software. The `PV_Configuration_3D` class is constructing the 3D PV geometry, starting with the basic component, which is a rectangular PV module. These modules can be specified with a thickness and are arranged in a grid to form a block, which is then rotated to achieve the desired tilt. The entire PV plant is generated by repeating this process and adjusting the orientation around the zenith axis for proper azimuth alignment.

PASE enables the creation of PV plants that can utilize sun-tracking and 
back-tracking algorithms based on NREL's methodologies. 
Users can easily create the PV system by completing parameter files located in 
designated folders, namely AV_CENTRAL and PV_MODULES. However, there is 
currently no user-friendly method for importing 3D geometry files for other 
structures due to varying conventions, including differences in reference 
frames, drawing scales, and file extensions, necessitating individual 
adjustments for each case. 
Consequently, in PASE, only the PV modules are created as geometric elements 
within the scene using PyVista.

### 2. Microclimate Modeling

The PASE framework’s micro-climate module calculates light and wind impacts within an agrivoltaic system.

#### Light Module

The **Light Module** calculates solar positions based on user-selected precision to minimize computations. It divides global horizontal irradiance (GHI) into direct and diffuse components using the Erbs model, then applies the HDKR model to compute irradiance on panel surfaces, considering circumsolar and horizon components, and soil albedo (defaulted to 0.25). A mesh of interest points, defined by the user, supports irradiance calculations on the ground level, while additional PV panel meshes track irradiance based on mutual shading and positioning.

#### Ray Casting

The **Ray Casting Scene** performs direct and diffuse ray casting. Direct rays determine light maps by tracing from mesh points to the sun, while diffuse rays, launched isotropically, yield sky visibility maps based on interception rates. These maps are then combined with irradiance data to compute daily light exposure reaching the crops.

#### Wind Module

The **Wind Module** calculates wind speed at different heights based on a logarithmic profile and roughness length of the terrain. This feature adjusts the wind data from PvGis (typically measured at 10 m) to the 2 m height needed for crop models, especially for evapotranspiration calculations. For vertical agrivoltaic (AV) systems, an empirical windbreak model (from `Windbreak2D.py`) further refines wind speed estimates by simulating the sheltering effects of panels.

### 3. Photovoltaic and Crop Production Calculation

#### Photovoltaic Module Description

The `PV_Production` class calculates the plane of array (POA) irradiance on 
photovoltaic (PV) module faces, including bifacial modules, to determine their 
productivity. Key loss factors considered during this process are mutual shading
and thermal losses. A PV module's temperature exceeding the standard test 
conditions (STC) of 25°C reduces conversion efficiency, and PASE implements the
PVsyst cell temperature model to account for this.

Heat loss calculations are based on typical conditions for free-standing 
modules, with a constant heat transfer component of 25 W/m²·K and a 
convective heat transfer component of 1.2 W·s/m³·K. 
The default wind speed for calculations is set at 10 m but can be adjusted.

The power generated by a PV module is computed using the formula: 

$$
P_{pv} = \eta A_{pv} \left( POA_{front} + POA_{rear} \beta \right) \left( 1 + \frac{\alpha}{100} (T_{pv} - T_{stc}) \right)
$$

Where:

- Ppv​ = Power output (W)
- η = Conversion efficiency at STC
- Apv​ = Surface area of the module
- POAfront​ and POArear​ = Irradiance values for the front and rear faces
- β = Bifaciality factor
- α = Temperature coefficient (negative value)
- Tpv​ = Module temperature
- Tstc​ = Standard test conditions temperature (25°C)

This formula illustrates how various factors influence the overall power output of the PV module.

#### Agronomic Module Description

The agronomic module in PASE consists of three sub-modules for integrated 
crop models: SIMPLE, Gras-Sim, and STICS. SIMPLE and Gras-Sim are implemented 
in Python, while STICS uses data management functions for compatibility with 
the JavaStics executable, allowing co-simulation.

1. **SIMPLE Module:**
   
   - The `run_independant_years_of_crop` function reads soil and crop parameters to run simulations over multiple years.
   - It utilizes the Crop and Soil classes and the `get_ET0` function to calculate water balance and water stress.
   - The FAO 56 Penman-Monteith model is implemented separately for calculating Reference Evapotranspiration (ET0).

2. **Gras-Sim Module:**
   
   - The `run_independant_years_of_grassland` function follows a similar structure, reading input files for soil and grassland parameters.
   - It calls the Grassland classes and the `get_ET0` function to perform simulations and manage water balance, using equations based on the work of Kokah et al. (2023).

3. **STICS Module:**
   
   - The `run_independent_usms` function reads a YAML input file for simulation parameters and specifies JavaStics .xml files for crops and soil.
   - It generates weather data files for each simulated year and creates an `usms.xml` file containing simulation unit information for JavaStics.
   - STICS can run independently over several years, with all formalisms detailed in Beaudoin et al. (2023).

The output of the simulations is stored in Python dictionaries, with each entry representing a year of agronomic results, managed by the `Crop_outputs` class in STICS and the Crop and Grassland classes in SIMPLE and Gras-Sim.

## PASE specific class

### Mesh Class

The class `Mesh` generates and manages point sources for computing microclimate variables in different parts of the 3D scene. It includes methods for adding regular meshes or specific points, as well as retrieving and organizing these points for light calculations.

Once the `Mesh` class is initialized, each time an `add_plane_ground_regular_meshes` or `add_sensor` method **is** used, new locations will be added to the set of locations of interest**s**. These locations can be added using a regularly sampled area (`add_plane_ground_regular_meshes`) or by adding a specific point (`add_sensor`). The points are stored in the attribute `sourcepoints` of the `Mesh` instance. Each time a collection of points is added, a specific string flag can be given to allow for later sub-sampling of the `Mesh` instance if, for example, the user wants to compute micrometeorological data but not use it in the crop model.

```python
# Initialization: 
M = Mesh() 

# Addition of a regular mesh at the ground level: 
M.add_plane_ground_regular_meshes(0, 1, 0, 3, 0.1, 1, flag='Points_Name')

# Addition of a sensor: 
M.add_sensor(0, 1, 1, flag='Points_Name')
```
