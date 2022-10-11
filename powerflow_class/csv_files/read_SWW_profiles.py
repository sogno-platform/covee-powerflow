import csv
import os
import numpy as np

class read_SWW_profiles:

    def __init__(self,conf_dict, grid_data):

        self.pvproduction = []
        self.demandprofile_P = []
        self.pvmeasurements = []
        self.demandmeasurements = []
        self.conf_dict = conf_dict
        self.grid_data = grid_data
    
    def read_csv(self):

        

        # Read CSV FILES
        # =============================================================

        cwd = os.getcwd()
        wd = os.path.join(cwd, 'powerflow_class/data/profiles/SWW')
        wd.replace("\\", "/")

        # TO BE DONE