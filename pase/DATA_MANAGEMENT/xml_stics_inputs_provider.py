#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import xmltodict
            
class XML_STICS_inputs_provider(dict):
    
    def __init__(self, file=None, soil_name=None):
        
        dict.__init__(self)
        
        if 'plt.xml' in file:
            rfile = open('INPUTS/CROPS/STICS/plant/'+file,"r")
            xml_dict = xmltodict.parse(rfile.read())
        else:
            rfile = open('INPUTS/CROPS/STICS/param_files/'+file,"r")
            xml_dict = xmltodict.parse(rfile.read())
        
        if ('plt.xml' in file or 'tec.xml' in file 
            or 'sta.xml' in file or 'param' in file) and soil_name is None:
            file_type = next(iter(xml_dict))
            for formalism in xml_dict[file_type]['formalisme']:
                self.retrieve_parameters(formalism)
                
        elif 'sols.xml' in file and soil_name is not None:          
            for soil in xml_dict['sols']['sol']:
                if soil['@nom'] == soil_name:
                    self.retrieve_parameters(soil)
                    
        elif 'ini.xml' in file and soil_name is None:
            self.retrieve_init_parameters(xml_dict)
            
                    
    def retrieve_parameters(self, dictionnary=None):
        
        for key, data in dictionnary.items():
                       
            if key == 'param' and type(data) is list:
                for parameter in data:
                    dict.__setitem__(self, parameter['@nom'],
                                     num(parameter['#text']))
                    
                    
            elif key == 'param' and type(data) is dict:
                dict.__setitem__(self, data['@nom'], num(data['#text']))
                
                
            elif key == 'option' and type(data) is list:
                for model in data:
                    dict.__setitem__(self, model['@nomParam'], 
                                     num(model['@choix']))
                    for choice in model['choix']:
                        if num(choice['@code']) == num(model['@choix']):
                            for key2, data2 in choice.items():
                                if key2 == 'param' and type(data2) is dict:
                                    dict.__setitem__(self, data2['@nom'], 
                                                  num(data2['#text']))
                                elif key2 == 'param' and type(data2) is list:
                                    for param in choice['param']:
                                        dict.__setitem__(self, param['@nom'], 
                                                     num(param['#text']))
                    
                    
            elif key == 'option' and type(data) is dict:
                dict.__setitem__(self, data['@nomParam'], num(data['@choix']))
                for model in data['choix']:
                    if num(model['@code']) == num(data['@choix']):
                        for key2, data2 in model.items():
                            if key2 == 'param' and type(data2) is dict:
                                dict.__setitem__(self, data2['@nom'], 
                                              num(data2['#text']))
                            elif key2 == 'param' and type(data2) is list:
                                for param in model['param']:
                                    dict.__setitem__(self, param['@nom'], 
                                                 num(param['#text']))
             
                
            elif key == 'ta':
                interventions_dict = {}
                if type(data['intervention']) is list:
                    for inter in data['intervention']:
                        params = {}
                        for par in inter['colonne']:
                            params[par['@nom']] = num(par['#text'])
                        interventions_dict[inter['colonne'][0]['#text']] = params
                elif type(data['intervention']) is dict:
                    params = {}
                    for par in data['intervention']['colonne']:
                        params[par['@nom']] = num(par['#text'])
                    interventions_dict[data['intervention']['colonne'][0]['#text']] = params
                dict.__setitem__(self, dictionnary['@nom'], interventions_dict)
                
                
            elif key == 'tableau':  
                list_epc = []
                list_HCCF = []
                list_HMINF = []
                list_DAF = []
                list_cailloux = []
                list_typecailloux = []
                list_infil = []
                list_epd = []
                for layer in data:
                    for param in layer['colonne']:
                        if param['@nom'] == 'epc':
                            list_epc.append(param['#text'])
                        if param['@nom'] == 'HCCF':
                            list_HCCF.append(param['#text'])
                        if param['@nom'] == 'HMINF':
                            list_HMINF.append(param['#text'])
                        if param['@nom'] == 'DAF':
                            list_DAF.append(param['#text'])
                        if param['@nom'] == 'cailloux':
                            list_cailloux.append(param['#text'])
                        if param['@nom'] == 'typecailloux':
                            list_typecailloux.append(param['#text'])
                        if param['@nom'] == 'infil':
                            list_infil.append(param['#text'])
                        if param['@nom'] == 'epd':
                            list_epd.append(param['#text'])
                dict.__setitem__(self, 'epc', list_epc)
                dict.__setitem__(self, 'HCCF', list_HCCF)
                dict.__setitem__(self, 'HMINF', list_HMINF)
                dict.__setitem__(self, 'DAF', list_DAF)
                dict.__setitem__(self, 'cailloux', list_cailloux)
                dict.__setitem__(self, 'typecailloux', list_typecailloux)
                dict.__setitem__(self, 'infil', list_infil)
                dict.__setitem__(self, 'epd', list_epd)
                
    
    def retrieve_init_parameters(self, dictionnary):
        
        dict.__setitem__(self, 'nbplantes', num(dictionnary['initialisations']
                                                ['nbplantes']))
        for key, data in dictionnary['initialisations']['plante'][0].items():
            if type(data) is str:
                dict.__setitem__(self, key, num(data))
            else:
                layer_dic = {}
                for layer in data['horizon']:
                    layer_dic[layer['@nh']] = num(layer['#text'])
                dict.__setitem__(self, key, layer_dic)
                
        for key, data in dictionnary['initialisations']['sol'].items():
            layer_list = []
            for layer in data['horizon']:
                layer_list.append(num(layer['#text']))
            dict.__setitem__(self, key, layer_list)

        if num(dictionnary['initialisations']['nbplantes']) == 2:
            dic_2nd_plant = {}
            for key, data in dictionnary['initialisations']['plante'][1].items():
                if type(data) is str:
                    dic_2nd_plant[key] = num(data)
                elif type(data) is type(None):
                    dic_2nd_plant[key] = data
                else:
                    layer_list = []
                    for layer in data['horizon']:
                        layer_list.append(num(layer['#text']))
                    dic_2nd_plant[key] = layer_list
            dict.__setitem__(self, '2nd_plant', dic_2nd_plant)
        
        
def num(x):
    try:
        return int(x)
    except ValueError:
        try: 
            return float(x)
        except ValueError:
            return str(x)
            
