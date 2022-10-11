import csv
import os
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "serif"
plt.rcParams["figure.figsize"] = (15,7.5)
plt.rcParams.update({'font.size': 26})
plt.rc('legend', fontsize=20, loc='upper right')    # legend fontsize

class read_profiles:

    def __init__(self,conf_dict, grid_data):

        self.pvproduction = []
        self.demandprofile_P = []
        self.pvmeasurements = []
        self.demandmeasurements = []
        self.conf_dict = conf_dict
        self.grid_data = grid_data


    def read_csv(self):

        if self.conf_dict["POWERFLOW_DATA"]["TYPE_PROFILE"] == "fix":
            
            gen_profile = np.tile([self.conf_dict["POWERFLOW_DATA"]["PROFILE"]["fix"]["GEN_PROFILE"]]*self.grid_data["ng"],(self.conf_dict["POWERFLOW_DATA"]["PROFILE"]["fix"]["ITERATIONS"],1))
            load_profile = np.tile([self.conf_dict["POWERFLOW_DATA"]["PROFILE"]["fix"]["LOAD_PROFILE"]]*self.grid_data["nb"], (self.conf_dict["POWERFLOW_DATA"]["PROFILE"]["fix"]["ITERATIONS"],1))

            return gen_profile, load_profile


        if self.conf_dict["POWERFLOW_DATA"]["TYPE_PROFILE"] == "variable":

            profiles = {
                'PV_measurements' : [self.conf_dict["POWERFLOW_DATA"]["PROFILE"]["variable"]["GEN_PROFILE"],self.pvmeasurements],
                'Load_measurements' : [self.conf_dict["POWERFLOW_DATA"]["PROFILE"]["variable"]["LOAD_PROFILE"],self.demandmeasurements],
            }

            # Read CSV FILES
            # =============================================================

            cwd = os.getcwd()
            wd = os.path.join(cwd, 'powerflow_class/data/profiles/Test')
            wd.replace("\\", "/")
            wd1 = os.path.join(cwd, 'powerflow_class//csv_files/profiles')
            wd1.replace("\\", "/")        
            k = 1
            for key in profiles:

                with open(os.path.join(wd, profiles[key][0])) as csv_file: 
                    pvproduction = csv.reader(csv_file, delimiter=',')
                    x = list(pvproduction)
                    profiles[key][1] = np.array(x).astype("float")
                
                name = profiles[key][0].replace('.csv','')
                list_plot = profiles[key][1] 
                for j in range(profiles[key][1].shape[1]):
                    globals()[name+'_' + str(j)] = []
                    for i in range(int(list_plot.shape[0]) - 1):
                        globals()[name+'_' + str(j)].append(list_plot[i][j])

                # plt.figure(k)
                # for j in range(list_plot.shape[1]):
                #     plt.plot(globals()[name+'_' + str(j)],'grey')
                # plt.plot(globals()[name+'_' + str(j)],'deepskyblue', label='bus'+str(j))
                # plt.plot(globals()[name+'_' + str(j-1)],'chartreuse', label='bus'+str(j-1))

                # axes = plt.gca()
                # plt.xlabel("Time [h]")
                # plt.ylabel(name+'[p.u.]')
                # plt.legend()
                # plt.savefig(wd1+'/plots/'+name+'.eps')
                # plt.savefig(wd1+'/plots/'+name+'.png')
                # k+=1
            
                


            return np.array(profiles['PV_measurements'][1]), np.array(profiles['Load_measurements'][1])