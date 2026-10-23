#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
#Author : Roxane Bruhwyler (roxane.bruhwyler@uliege.be or roxane.bruhwyler@hotmail.com)
#This file is part of the PASE software, and is distributed under the MIT license.

"""

import matplotlib.pyplot as plt
import numpy as np
import os

def graph_1Y_axis(data_x=None, data1=None, data2=None, data3=None, data4=None, 
                  data_x_name=None, data1_name=None, data2_name=None, data3_name=None, 
                  data4_name=None, c1=None, c2=None, c3=None, c4=None, ax1_name=None, graph_name=None, gd_color=None, 
                  x_inf=None, x_sup=None):
    
    plt.style.use('classic')
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    lgd1 = ax1.plot(data_x, data1, c1, label=data1_name, linestyle='solid', linewidth=2.5)
    lgd = lgd1
    if data2 is not None:
        lgd2 = ax1.plot(data_x, data2, c2, label=data2_name, linestyle='dotted', linewidth=4)
        lgd = lgd + lgd2
    if data3 is not None:
        lgd3 = ax1.plot(data_x, data3, c3, label=data3_name, linestyle='dashdot', linewidth=3.5)
        lgd = lgd + lgd3
    if data4 is not None:    
        lgd4 = ax1.plot(data_x, data4, c4, label=data4_name, linestyle='dashed', linewidth=3.5)  
        lgd = lgd + lgd4            
    ax1.set_ylabel(ax1_name)
    ax1.set_xlabel(data_x_name)
    ax1.set_xlim(x_inf, x_sup)
    #fig.title(graph_name)

    lgds = [l.get_label() for l in lgd]
    ax1.legend(lgd, lgds, loc=0)
    ax1.grid(color=gd_color, linestyle='-')
    plt.show()

    path = os.path.join('OUTPUTS', 'GRAPHS', graph_name+'.svg')

    fig.savefig(path, format='svg')
    
    
def graph_2Y_axis(data_x=None, data1=None, data2=None, data3=None, data4=None, 
                        data5=None, data6=None, data_x_name=None, data1_name=None, data2_name=None,
                        data3_name=None, data4_name=None, data5_name=None, data6_name=None,
                        ax1_name=None, ax2_name=None, graph_name=None):
    
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    lgd1 = ax1.plot(data_x, data1, '#FF6103', label=data1_name, linestyle='solid', linewidth=2.5)
    lgd = lgd1
    if data2 is not None:
        lgd2 = ax1.plot(data_x, data2, '#98F5FF', label=data2_name)
        lgd = lgd + lgd2
    if data3 is not None:
        lgd3 = ax1.plot(data_x, data3, '#CDAA7D', label=data3_name)
        lgd = lgd + lgd3
    if data4 is not None:
        ax2 = ax1.twinx()
        lgd4 = ax2.plot(data_x, data4, '#FF7256', label=data4_name, linestyle='dashdot', linewidth=3.5)
        lgd = lgd + lgd4
        ax2.set_ylabel(ax2_name)
    if data5 is not None:    
        lgd5 = ax2.plot(data_x, data5, '#FF4040', label=data5_name)  
        lgd = lgd + lgd5
    if data6 is not None:
        lgd6 = ax2.plot(data_x, data6, '#A52A2A', label=data6_name)     
        lgd = lgd + lgd6
    ax1.set_ylabel(ax1_name)
    ax1.set_xlabel(data_x_name)
    #fig.title(graph_name)

    lgds = [l.get_label() for l in lgd]
    ax1.legend(lgd, lgds, loc=0)
    ax1.grid(color='#CBCBCB')
    plt.show()

    path = os.path.join('OUTPUTS', 'GRAPHS', graph_name + '.png')

    fig.savefig(path, format='png')

    
def histogram_several_series(x_label, data_s1, data_s2, data_s3, label_s1,
                          label_s2, label_s3, y_label, graph_title,
                          data_s4=None, label_s4=None):
    
    X_axis = np.arange(len(data_s1))
    d = 0.275 
    
    plt.style.use('classic')
    plt.bar(X_axis-d, data_s1, d, label = label_s1, color='#ffcc00')
    plt.bar(X_axis, data_s2, d, label = label_s2, color='#4d94ff')
    plt.bar(X_axis+d, data_s3, d, label = label_s3, color='#d9d9d9')
    if data_s4 is not None:
        plt.bar(X_axis+1.5*d, data_s4, d, label = label_s4, color='#8C60B6')
    plt.xticks(X_axis, x_label)
    plt.xlim(-1, 12)
    plt.ylabel(y_label, fontweight='bold')
    plt.legend(loc='best')
    plt.grid()
    plt.savefig(os.path.join('OUTPUTS', 'GRAPHS', graph_title + '.svg'))
    plt.show()
