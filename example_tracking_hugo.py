#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.



#---------------------------------------------- IMPORTS ----------------------------------------------

import os

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import (YAML_Inputs_provider,
                                                       Inputs_aggregator)
from pase.DATA_MANAGEMENT.input_checker import InputsEvaluator
from pase.DATA_MANAGEMENT.OUTPUT.outputs_manager import OutputsManager
from pase.DATA_MANAGEMENT.weather_data_provider import (fetch_weather_from_pvgis,
                                                        get_cache_key,
                                                        Weather_data)
from pase.PHOTOVOLTAICS.configuration import (PV_Configuration_3D,
                                              PVConfiguration3D)  
from pase.ENVIRONMENT.light import Sun_positions_sampled, Sun_positions, Light
from pase.ENVIRONMENT.light import Ray_casting_scene
from pase.ENVIRONMENT.mesh import Mesh
from pase.ENVIRONMENT.sky_model import ReinhartSky
from pase.PHOTOVOLTAICS.production import PV_Production
from pase.CROPS.run_crop_simulations import (run_crop_simu,
                                             visualize_map_of_a_variable)

# ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
from pase.PHOTOVOLTAICS.pilotage import PilotageStrategy, TrackingController
from pase.DATA_MANAGEMENT.plots.tracking_trace import export_tracking_trace

# ------- PARAMETRES DU PILOTAGE (a modifier ici) -------
# Fichier de strategie de pilotage (voir INPUTS/PILOTAGE/ pour les exemples) :
#   - strategie_tracking_pur.yaml       : tracking classique (reference)
#   - strategie_antitrack_pur.yaml      : anti-tracking toute l'annee
#   - strategie_antitrack_printemps.yaml: strategie mixte dates + heures
STRATEGIE_PILOTAGE = os.path.join('INPUTS', 'PILOTAGE', 'strategie_tracking_pur.yaml')
# Jour(s) a tracer sur les graphiques de verification du pilotage.
# Format : (date 'YYYY-MM-DD', mot-cle). Le mot-cle (ex. saison) apparait dans le
# titre ET le nom du fichier PNG. Une figure est generee par jour (le CSV, lui,
# contient toujours TOUTE l'annee). Laisser [] pour n'exporter que le CSV.
JOURS_TRACE = [
    ('02-15', 'hiver'),
    ('05-01', 'printemps'),
    ('07-15', 'ete'),
    ('10-15', 'automne'),
]
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============

#initialise le système de logs de PASE (permet d'ecrire les messages d'erreur et d'information dans un fichier de logging_file)
PASE_Logger()



#---------------------------------------------- LOAD DES INPUTS ----------------------------------------------


# localisation / période de simulation / position solaire moyenne (mois, semaine, jour) / ciel diffus / ZONE D'INTERET AU SOL
Loc_1 = YAML_Inputs_provider(file='Example1_loc_hugo.yaml', subpath='SCENARIOS').inputs

# Structure d'un block PV (nb panneaux, espacement, axe rotation, hauteur) / TRACKING (0,1) / structure PV globale (nb block, espacement blocs, axe de roation)
AV_1 = YAML_Inputs_provider(file='Example2_tracking_AV_hugo.yaml', subpath='AV_CENTRAL').inputs

# Données tech d'un module PV (dimensions, puissance, bifacialité, epaisseur)
PV_module_1 = YAML_Inputs_provider(file='Example1_PV_Module_hugo.yaml', subpath=os.path.join('HARDWARE','PV_MODULES')).inputs

# configuration du modèle de culture (date de semis, paramètre du sol, coeficient du modèle)
crop_config = YAML_Inputs_provider(file='simple_example.yml', subpath=os.path.join('CROPS', 'config')).inputs



# Using Sky Types characterization while simulating an AV central with solar
# tracking is very computer intensive ; InputChecker asks the user to reconsider
#tcheck si le tracking est actif et si les seuils de points sources et de MF sont respectés pour éviter des temps de calcul trop longs
input_checker = InputsEvaluator(Loc_1, AV_1)

#fusion des deux dictionnaires d'inputs (Loc_1 et AV_1) pour créer un dictionnaire d'inputs global pour la simulation
PV_params_dict = Inputs_aggregator([AV_1, PV_module_1]).aggregated_inputs


# ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
# Chargement de la stratégie de pilotage (planning tracking / anti-tracking / fixe)
# et création du contrôleur : c'est LUI qui calcule désormais les angles des
# panneaux, à la fois pour la géométrie 3D (ray casting -> lumière au sol)
# et pour la production électrique -> angles strictement identiques des 2 côtés.
strategie_pilotage = PilotageStrategy.from_yaml(STRATEGIE_PILOTAGE)
pilotage_controller = TrackingController.from_inputs(strategie_pilotage,
                                                     PV_params_dict)
print(f"[PILOTAGE] Stratégie chargée : '{strategie_pilotage.name}' "
      f"(default_mode={strategie_pilotage.default_mode}, "
      f"{len(strategie_pilotage.rules)} règle(s), "
      f"MaxTiltAngle={pilotage_controller.max_tilt_deg}°)")
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============


#gestion de l'arborescence du fichier output
om = OutputsManager(Loc_1['LocationName'],
                    Loc_1['SimulationStartingYear'],
                    Loc_1['SimulationEndingYear'])

#calcul des hashs des fichiers input et recherhce si hash existe déjà pour éviter de refaire les calculs si les mêmes inputs
variant_dir = om.setup_variant(loc=Loc_1,
                               av=AV_1,
                               pv_module=PV_module_1,
                               structure=dict(),  # No structure -> empty dict.
                               crop_config=crop_config,
                               source=__file__)

#création d'une clé de cache pour les données météo en fonction de la localisation et de la période de simulation
cache_key = get_cache_key(Loc_1['Latitude'],
                          Loc_1['Longitude'],
                          Loc_1['SimulationStartingYear'],
                          Loc_1['SimulationEndingYear'])



#------------------------------------------------ PRE PROCESSING ----------------------------------------------

#--------------------- WHEATHER DATA ---------------------
# Import weather data and compute daily weather data
lat = Loc_1['Latitude']
lon = Loc_1['Longitude']
start_year = Loc_1['SimulationStartingYear']
end_year = Loc_1['SimulationEndingYear']

#si données météo de PVGIS, on les importe ou les télécharge et les stocke dans le cache
if Loc_1['WeatherDataOption'] == 1:
    raw_weather = om.load_or_fetch_weather(
        key=cache_key,
        fetch_fn=lambda: fetch_weather_from_pvgis(lat, lon, start_year, end_year)
    )

else:  #sinon, on les laisse à None pour les importer depuis un fichier csv
    raw_weather=None

#prend les données brutes et les organise en objets exploitables par la suite
WD = Weather_data(Loc_1['Latitude'],
                  Loc_1['Longitude'],
                  Loc_1['SimulationStartingYear'],
                  Loc_1['SimulationEndingYear'],
                  Loc_1['WeatherDataOption'],
                  raw_weather,
                  Loc_1['WeatherFileName'],
                  Loc_1['DailyWeatherFileName']
                  )


#--------------------- SUN POSITIONS ---------------------


#----POSITION SOLEIL SAMPLÉE----
# calcule les positions du soleil (azimut + élévation) mais en sous-échantillonnant selon PrecisionLevelOnSunPosition (mois, semaine, jour)
Sun_positions_samp = Sun_positions_sampled(Loc_1['Latitude'],
                                      Loc_1['Longitude'],
                                      Loc_1['PrecisionLevelOnSunPosition'],
                                      Loc_1['LocationName'],
                                      len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                      Loc_1['TimeZone'])

#----POSITION SOLEIL COMPLÈTE----
# Calcule les positions solaires pour chaque heure de l'année. Nécessaires pour le modèle HDKR qui calcule l'irradiance reçue sur les panneaux inclinés
Sun_positions_complete = Sun_positions(Loc_1['Latitude'],
                                       Loc_1['Longitude'],
                                       len(WD.nyears_data[str(Loc_1['SimulationStartingYear'])]),
                                       Loc_1['TimeZone'])



#----GEOMETRIE 3D DU SYST PV------
# Construit le maillage 3D des panneaux
# ============== [HUGO - PILOTAGE] DEBUT MODIF ==============
# Ajout de pilotage_controller + sun_datetimes : les angles des panneaux sont
# calculés par le contrôleur de pilotage (tracking/anti-tracking selon la
# stratégie) au lieu du tracking pur historique.
PV_1_3Dconfig = PV_Configuration_3D(PV_params_dict,
                                    Sun_positions_samp.solar_vector,
                                    visualization=True,
                                    pilotage_controller=pilotage_controller,
                                    sun_datetimes=Sun_positions_samp.SP.index)
# ============== [HUGO - PILOTAGE] FIN MODIF ==============



#------------------- CREATION ZONE D'INTERET------------------

# Initialise un objet vide qui va contenir les points d'intérêt.
M = Mesh()

# Oriente la grille selon le mode défini dans Loc_1['InterestZoneOrientationMode']
M.set_interest_zone_orientation(Loc_1, AV_1)

# Crée la grille de points au sol avec les paramètres de Loc_1
M.add_oriented_plane_ground_mesh(
    Loc_1['Xmin_InterestZone'],
    Loc_1['Xmax_InterestZone'],
    Loc_1['Ymin_InterestZone'],
    Loc_1['Ymax_InterestZone'],
    Loc_1['dX_InterestZone'],
    Loc_1['dY_InterestZone'],
    flag="crop"
)


#------------------- CALCUL LUMINEUX ------------------
# Discrétisation du ciel - Génère les patches du dôme céleste (en fonction de MF). Chaque patch a une direction, une surface solide et un poids pour le calcul du diffus
discrete_sky = ReinhartSky(MF=Loc_1['MF']).reinhart_patches

# Données d'irradiance - Combine les données météo horaires et les positions solaires complètes pour calculer l'irradiance directe et diffuse disponible = en gros combien d'énergie est disponible dans le ciel
Light_instance = Light(WD.nyears_data, Sun_positions_complete)

# assemblage des 3 elements : grille de points au sol, géométrie 3D des panneaux, ciel discret
L = Ray_casting_scene(mesh=M,
                      geometry=PV_1_3Dconfig.PV_central_PD,
                      discrete_sky=discrete_sky)

# Ray casting - pour chaque position solaire calcul des ombre DIRECTES et DIFFUSES
L.get_light_maps(Sun_positions_samp.solar_vector,
                 visualization=False,
                 Sun_P_map_to_visualize=3)

# Intégration sur la journée 
L.get_daily_irradiation_map(Sun_positions_samp.SP, Light_instance.data,
                            visualization=False)



# ------------------------------------------- PROCESSING ---------------------------------------------------

# ----------------- PRODUCTION ELECTRIQUE -----------------
# Initialise le modèle de production électrique avec les paramètres du module
# ============== [HUGO - PILOTAGE] DEBUT MODIF ==============
# (ancienne ligne : PV_central = PV_Production(PV_params_dict))
PV_central = PV_Production(PV_params_dict,
                           pilotage_controller=pilotage_controller)
# ============== [HUGO - PILOTAGE] FIN MODIF ==============

# Calcule la production électrique pour chaque année simulée - utilise le modèle HDKR pour convertir l'irradiance horizontale en irradiance sur les panneaux inclinés/trackés, puis applique le rendement électrique du module pour obtenir une puissance en watts à chaque heure
PV_central.get_several_years_of_electricity_production(Sun_positions_complete, Light_instance.data, WD.nyears_data)

# affiche dans le terminal la production annuelle totale de la centrale pour chaque année simulée
for _ in range(Loc_1['SimulationStartingYear'], Loc_1['SimulationEndingYear']+1):
    PV_prod = PV_central.production[str(_)]
    print(f'PV production for year {_}: {PV_prod["P_central"].sum():.2f} MW·h')


# ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
# ----------------- TRACE DE VERIFICATION DU PILOTAGE -----------------
# Pour chaque année simulée : export d'un CSV horodaté (soleil + tilt + mode)
# et un graphique par jour de JOURS_TRACE appartenant à cette année, montrant
# l'inclinaison des panneaux par rapport à la position du soleil, avec le mode
# actif (tracking / anti-tracking / fixe) en bandes colorées.
for _year in PV_central.tiltY_per_year:
    _sp = (Sun_positions_complete.sp_leapY if int(_year) % 4 == 0
           else Sun_positions_complete.sp_nonleapY)
    # JOURS_TRACE est en 'MM-DD' -> on prefixe l'annee courante (year-agnostic)
    _jours_annee = [(f'{_year}-{mmdd}', lab) for (mmdd, lab) in JOURS_TRACE]
    export_tracking_trace(
        tilt_series=PV_central.tiltY_per_year[_year],
        mode_series=PV_central.mode_per_year.get(_year),
        true_angle_series=PV_central.true_angle_per_year.get(_year),
        sun_positions_df=_sp,
        label=f'{strategie_pilotage.name}_{_year}',
        day=_jours_annee,   # liste de dates -> une figure par jour
        max_tilt_deg=pilotage_controller.max_tilt_deg)
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============




# ----------------- MODELE DE CULTURE ----------------
#Temporary line, this parameter (option_2D) should be in SCENARIOS input files (general parameters)
option_2D = 1 # 0: no 2D-spatialization ; 1 : 2D spatialization


#lancement du modèle de culture avec la météo journalière, la carte d'irradiation journalière calculée par le Ray casting
#agro_results contient les variables agronomiques (rendement, biomasse...) pour chaque point au sol et chaque jour de l'année.
agro_results = run_crop_simu(crop_config, option_2D, WD.nyears_daily_data,
                                     L.daily_irr_spat,
                                     Loc_1)





#---------------------------------------------- AFFICHAGE 3D ----------------------------------------------


# --------------- AFFICHAGE 3D LUMIERE ---------------

# affciage map lumière directe
L.visualize_direct_light_map(8)

# affciage map lumière diffuse
L.visualize_diffuse_light_map(1)

# irradiation journalière pour l'année et le jour julian choisi
L.visualize_daily_irrad_map(Loc_1['SimulationStartingYear'], 5)




# --------------- AFFICHAGE 3D CULTURE---------------

# Affiche une carte 2D du rendement au sol à une date donnée.
if crop_config['CropModel'] == ('simple' or 'stics'):
    visualize_map_of_a_variable(crop_config, agro_results,
                                'Fresh_yield',
                                PV_1_3Dconfig.PV_central_PD, M,
                                Loc_1['SimulationStartingYear'],
                                MM_DD='10-10', unit='g/m²')
else:
    visualize_map_of_a_variable(crop_config, agro_results,
                                'BM',
                                PV_1_3Dconfig.PV_central_PD, M,
                                Loc_1['SimulationStartingYear'],
                                MM_DD='10-10', unit='t/ha')


#---------------------------------------------- GRAPHS PLOTTING ----------------------------------------------



# --------------- GRAPHS PROD ENERGY ---------------
from pase.DATA_MANAGEMENT.plots.pv_energy_integral import plot_pv_energy_integral

# ============== [HUGO - PILOTAGE] DEBUT AJOUT ==============
# Serie des modes de pilotage concatenee sur toutes les annees, pour colorer le
# fond des graphes d'integrale selon le mode actif (tracking / anti-tracking).
import pandas as _pd
_annees = sorted(PV_central.production.keys())
_mode_all = (_pd.concat([PV_central.mode_per_year[_y] for _y in _annees])
             if PV_central.mode_per_year else None)
# ============== [HUGO - PILOTAGE] FIN AJOUT ==============

plot_pv_energy_integral(PV_central.production, mode_series=_mode_all)
# ou avec sauvegarde :
plot_pv_energy_integral(PV_central.production, save_path='OUTPUTS/GRAPHS/pv_energy_integral.png',
                        mode_series=_mode_all)




# --------------- GRAPHS CROP ---------------
from pase.DATA_MANAGEMENT.plots.biomass_integral import plot_biomass_integral

plot_biomass_integral(agro_results, save_path='OUTPUTS/GRAPHS/bio_mass_integral.png',
                      mode_series=_mode_all)                                    # Biomasse par défaut
plot_biomass_integral(agro_results, variable='Fresh_yield', unit='g/m²', mode_series=_mode_all)  # Rendement frais
plot_biomass_integral(agro_results, variable='Dry_yield', unit='g/m²', mode_series=_mode_all)    # Rendement sec




# --------------- SAUVEGARDE DES RESULTATS ---------------
# Enregistre les résultats de cette simulation sur disque.
# une fois tous les scénarios souhaités sauvegardés.
# il faut ensuite lancer compare_simulations.py pour tracer les graphiques de comparaison

from pase.DATA_MANAGEMENT.simulation_results import save_simulation

# ============== [HUGO - PILOTAGE] DEBUT MODIF ==============
# (ancienne ligne : save_simulation('sans_track_Tilt_90deg', PV_central.production, agro_results))
# Le label inclut le nom de la stratégie de pilotage, et les séries de tilt/mode
# sont sauvegardées dans le pickle pour pouvoir comparer les stratégies.
save_simulation(f'pilotage_{strategie_pilotage.name}',
                PV_central.production,
                agro_results,
                pilotage={'strategy_name': strategie_pilotage.name,
                          'strategy_file': STRATEGIE_PILOTAGE,
                          'tilt_per_year': PV_central.tiltY_per_year,
                          'mode_per_year': PV_central.mode_per_year,
                          'true_angle_per_year': PV_central.true_angle_per_year})
# ============== [HUGO - PILOTAGE] FIN MODIF ==============
