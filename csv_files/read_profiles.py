import csv
import os
import numpy as np

class read_profiles:

    def __init__(self):

        self.pvproduction = []
        self.demandprofile_P = []


    def read_csv(self):

        # Read CSV FILES
        # =============================================================

        cwd = os.getcwd()
        wd = os.path.join(cwd, 'powerflow/data/profiles/simple_test_profiles')
        wd.replace("\\", "/")
        with open(os.path.join(wd, 'PV_profile_LV_SOGNO_4kw.csv')) as csv_file: #10 Nodes: 10_nodes_PV # No Cloud: PV_profile_LV_SOGNO_4kw  #With Cloud: PV_profile_LV_SOGNO-cloudlevel-2.csv
            pvproduction = csv.reader(csv_file, delimiter=',')
            x = list(pvproduction)
            self.pvproduction = np.array(x).astype("float")

        with open(os.path.join(wd, 'LOAD_profile_LV_SOGNO.csv')) as csv_file:  # 10 Nodes: 10_nodes_Load    # LOAD_profile_LV_SOGNO
            demandprofile_P = csv.reader(csv_file, delimiter=',')
            x = list(demandprofile_P)
            self.demandprofile_P = np.array(x).astype("float")

        return self.pvproduction, self.demandprofile_P