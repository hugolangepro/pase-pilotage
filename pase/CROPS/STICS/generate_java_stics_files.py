#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

def generate_weather_data_file(WD, irrad, loc_name, path):
    
    WD_files_dict = {}
    
    for year in WD.keys():
        
        WD_files_list = []
        clim = 'clim'+year
        
        for position in range(len(irrad[year][:,1])):
            
            WD_file_name = (str(loc_name)+'_'+year+'_position'+str(position))
            WD_files_list.append(WD_file_name)
            WD_file = open(path+WD_file_name+'.'+year,'w')
            
            for day in WD[year].index:
                
                if day.day_of_year==366:
                    break
                
                month = day.month
                day_of_month = day.day
                julian_day = day.day_of_year
                
                min_T = str(round(WD[year]["Min_temp"][day],1))
                max_T = str(round(WD[year]['Max_temp'][day],1))
                daily_rad = str(round(irrad[year][position, julian_day-1],1))
                ETP = str(-999)
                Daily_rain = str(round(WD[year]['Rain'][day],1))
                ws_10m = str(round(WD[year]['Avg_WS_2m'][day],1))
                vapor_press = str(round(WD[year]['Vap_press'][day],1))
                CO2 = str(round(WD[year]['CO2'][day],1))
                
    
                txt_line2 = (f'{clim:<9}{year:>5}{month:>4}{day_of_month:>4}{julian_day:>5}{min_T:>6}{max_T:>6}{daily_rad:>6}{ETP:>6}{Daily_rain:>6}{ws_10m:>6}{vapor_press:>6}{CO2:>7}'
                             +'\n')
        
                WD_file.write(txt_line2)
                
            WD_file.close()
            
        WD_files_dict[year] = WD_files_list
            
    return WD_files_dict


def generate_USMS_file(FN, FN_PY, simu_P, year, path):

    output_file = open(path+'usms.xml','w')

    output_file.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
    output_file.write('<usms>\n')
    output_file.write('  <usm nom="' + FN + '">\n')
    output_file.write('    <datedebut>' + str(simu_P['BeginDate']) + '</datedebut>\n')
    output_file.write('    <datefin>' + str(simu_P['EndDate']) + '</datefin>\n')
    output_file.write('    <finit>' + simu_P['InitFile'] + '.xml</finit>\n')
    output_file.write('    <nomsol>' + simu_P['SoilName'] + '</nomsol>\n')
    output_file.write('    <fstation>' + simu_P['StationFile'] + '.xml</fstation>\n')
    if simu_P['AnnualCropOption'] == 0:
        output_file.write('    <fclim1>' + FN_PY+'.' + str(int(year)-1) + '</fclim1>\n')
        output_file.write('    <fclim2>' + FN+'.' + year + '</fclim2>\n')
    elif simu_P['AnnualCropOption'] == 1:
        output_file.write('    <fclim1>' + FN+'.' + year + '</fclim1>\n')
        output_file.write('    <fclim2>' + FN+'.' + year + '</fclim2>\n')
    output_file.write('    <culturean>' + str(simu_P['AnnualCropOption']) + '</culturean>\n')
    output_file.write('    <nbplantes>' + str(simu_P['PlantsNumber']) + '</nbplantes>\n')
    output_file.write('    <codesimul>0</codesimul>\n')
    output_file.write('    <plante dominance="1">\n')
    output_file.write('      <fplt>' + simu_P['PlantFile'] + '.xml</fplt>\n')
    output_file.write('      <ftec>' + simu_P['TechnicFile'] + '.xml</ftec>\n')
    output_file.write('      <flai>null</flai>\n')
    output_file.write('    </plante>\n')
    output_file.write('    <plante dominance="2">\n')
    
    if simu_P['PlantFile2ndCrop'] == 'N/A':
        plantfile2ndcrop = 'null'
        technicfile2ndcrop = 'null'
    else:
        plantfile2ndcrop = simu_P['PlantFile2ndCrop']
        technicfile2ndcrop = simu_P['TechnicFile2ndCrop']
        
    output_file.write('      <fplt>' + plantfile2ndcrop + '</fplt>\n')
    output_file.write('      <ftec>' + technicfile2ndcrop + '</ftec>\n')
    output_file.write('      <flai>null</flai>\n')
    output_file.write('    </plante>\n')
    output_file.write('  </usm>\n')
    output_file.write('  <usm nom="Bidon">\n')   # Add to work with pystics' way of importing usm parameters (line 715-721 de params.py)
    output_file.write('  </usm>\n')
    output_file.write('</usms>')

    output_file.close()
