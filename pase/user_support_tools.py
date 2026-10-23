#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

import logging
from typing import Tuple


class PASE_Logger:
    
    def __init__(self, msg=None, level=None, error_type=None):
        
        log_file = 'logging_file.log'
        logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG,
                            format='%(asctime)s  (%(levelname)s)  -  %(message)s',
                            datefmt='%I:%M:%S %p')
        
        if level is None and msg is None:
            self.initialization()
        
        if level == 'DEBUG':
            self.write_debug(msg)
        elif level == 'INFO':
            self.write_info(msg)
        elif level == 'WARNING':
            self.write_warning(msg)
        elif level == 'ERROR':
            self.write_error(msg, error_type)
        elif level == 'CRITICAL':
            self.write_critical(msg)
            
            
    def initialization(self, msg='START OF THE SIMULATION'):
        
        with open('logging_file.log', 'w'):
            pass
        log_file = 'logging_file.log'
        logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG,
                            format='%(asctime)s  (%(levelname)s)  -  %(message)s',
                            datefmt='%I:%M:%S %p') 
        self.write_info(msg)
        
            
    def write_debug(self, msg):      
        logging.debug(msg)
        print(msg)
        
        
    def write_info(self, msg):
        logging.info(msg)
        print(msg)
        
        
    def write_warning(self, msg):
        logging.warning(msg)
        print(msg)
        
        
    def write_error(self, msg, error_type):
        logging.error(msg)
        
        if error_type == 'value':
            raise ValueError(msg)
        
        
    def write_critical(self, msg):
        logging.critical(msg)
        print(msg)
        

def prompt(prompt: str, valid: Tuple[str, ...], default: str = None) -> str:
    while True:
        resp = input(prompt).strip()
        if resp == "" and default is not None:
            return default
        if resp.lower() in valid:
            return resp.lower()
        print(f"Invalid input. Expected one of: {', '.join(valid)}")
