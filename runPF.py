from pypower.api import *
from pypower.ext2int import ext2int
from pypower.idx_brch import F_BUS, T_BUS, TAP, BR_R, BR_X, BR_B, RATE_A, PF, QF, PT, QT
from pypower.idx_bus import BUS_TYPE, REF, PD, QD, VM, VA, VMAX, VMIN
from pypower.idx_gen import GEN_BUS, PG, QG, PMAX, PMIN, QMAX, QMIN, VG
from pypower.int2ext import int2ext

from cases.LV_SOGNO import LV_SOGNO as case
from csv_files.read_profiles import read_profiles

import numpy as np
from pypower.ppoption import ppoption
import csv
import os
import coloredlogs, logging, threading
from threading import Thread
from submodules.dmu.dmu import dmu
from submodules.dmu.httpSrv import httpSrv
import time
import sys
import requests
import json
import csv
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--ext_port', nargs='*', required=True)
args = vars(parser.parse_args())
ext_port = args['ext_port'][0]


coloredlogs.install(level='DEBUG',
fmt='%(asctime)s %(levelname)-8s %(name)s[%(process)d] %(message)s',
field_styles=dict(
    asctime=dict(color='green'),
    hostname=dict(color='magenta'),
    levelname=dict(color='white', bold=True),
    programname=dict(color='cyan'),
    name=dict(color='blue')))
logging.info("Program Start")


def initialize( name, profiles):
    # Input Data
    # =============================================================
    ppc = name
    pvproduction = profiles[0]
    demandprofile_P = profiles[1]

    ppc = ext2int(ppc)      # convert to continuous indexing starting from 0
    BUS_TYPE = 1

    # Gather information about the system
    # =============================================================
    baseMVA, bus, gen, branch, cost, VMAX, VMIN = \
        ppc["baseMVA"], ppc["bus"], ppc["gen"], ppc["branch"], ppc["gencost"], ppc["VMAX"], ppc["VMIN"]

    nb = bus.shape[0]                        # number of buses
    ng = gen.shape[0]                        # number of generators
    nbr = branch.shape[0]                    # number of branches

    for i in range(int(nb)):
        if bus[i][BUS_TYPE] == 3.0:
            pcc = i
        else:
            pass     
    
    grid_data = {"baseMVA":baseMVA,"branch":branch,"pcc":pcc,"bus":bus,"gen":gen,"nb":nb,"ng":ng,"nbr":nbr}

    return grid_data

def run_Power_Flow(ppc, active_nodes, active_power,reactive_power,pv_profile,load_profile):
    ppc = ext2int(ppc)      # convert to continuous indexing starting from 0
    BUS_TYPE = 1

    # Gather information about the system
    # =============================================================
    baseMVA, bus, gen, branch, cost, VMAX, VMIN = \
        ppc["baseMVA"], ppc["bus"], ppc["gen"], ppc["branch"], ppc["gencost"], ppc["VMAX"], ppc["VMIN"]

    nb = bus.shape[0]                        # number of buses
    ng = gen.shape[0]                        # number of generators
    nbr = branch.shape[0]                    # number of branches

    for i in range(int(nb)):
        if bus[i][BUS_TYPE] == 3.0:
            pcc = i
        else:
            pass

    c = active_nodes
    for i in range(1,ng):
        if gen[i][0] in c:
            pass
        else:
            np.delete(ppc["gen"],(i),axis=0)       

    print("Number of Reactive Power Compensator = ",int(len(c)))
            
    # initialize vectors
    # =====================================================================
    q = [0.0] * int(len(c))
    p = []
    v_gen = []
    v_tot = []

    ############## SET THE ACTUAL LOAD AND GEN VALUES ###############-+
    for i in range(int(nb)-1):
        bus[i][PD] = load_profile[i]#0.3 
        bus[i][QD] = 0.0
    for i in range(ng-1):
        gen[i][PG] = pv_profile[i]
        if i in c:
            gen[i][QG] = reactive_power[i]
            gen[i][PG] = pv_profile[i] + active_power[i]
    # for i in range(int(len(c))):
    #     gen[i+1][QG] = reactive_power[i]
    #     gen[i+1][PG] = pv_profile[i] + active_power[i]

    ppc['bus'] = bus
    ppc['gen'] = gen
    ppc = int2ext(ppc)


    ############# RUN PF ########################
    opt = ppoption(VERBOSE=0, OUT_ALL=0, UT_SYS_SUM=0)
    results = runpf(ppc, opt)
    bus_results = results[0]['bus']

    for i in range(grid_data["nb"]):
        v_tot.append(bus_results[int(i-1)][VM])

    for i in range(int(len(c))):
        v_gen.append(bus_results[int(c[i]-1)][VM])
        p.append(gen[i+1][PG])
    
    return v_tot,v_gen,p,c


############################ Start the Server #######################################################

''' Initialize objects '''
dmuObj = dmu()

''' Start http server '''
httpSrvThread1 = threading.Thread(name='httpSrv',target=httpSrv, args=("0.0.0.0", 8000 ,dmuObj,))
httpSrvThread1.start()

httpSrvThread2 = threading.Thread(name='httpSrv',target=httpSrv, args=("0.0.0.0", int(ext_port) ,dmuObj,))
httpSrvThread2.start()
time.sleep(2.0)
#######################################################################################################


########################################################################################################
#########################  Section for Defining the Dictionaries  ######################################
########################################################################################################

dict_ext_cntr = {
    "data_cntr" : [],
    "data_nodes" : []
}

simDict = {
    "active_nodes" : [],
    "output_voltage": [],
    "active_power_control": [],
    "reactive_power_control": []
}

voltage_dict = {}
active_power_control_dict = {}
reactive_power_control_dict = {}
pv_input_dict = {}

# add the simulation dictionary to mmu object
dmuObj.addElm("simDict", simDict)
dmuObj.addElm("voltage_dict", voltage_dict)
dmuObj.addElm("active_power_control_dict", active_power_control_dict)
dmuObj.addElm("reactive_power_control_dict", reactive_power_control_dict)
dmuObj.addElm("pv_input_dict", pv_input_dict)

########################################################################################################
#########################  Section for Receiving Signal  ###############################################
########################################################################################################

def active_power_control_input(data,  *args):
    active_power_control_dict = {}  
    dmuObj.setDataSubset(data,"active_power_control_dict")
def reactive_power_control_input(data,  *args):
    reactive_power_control_dict = {}  
    dmuObj.setDataSubset(data,"reactive_power_control_dict")

def api_cntr_input(data,  *args):   
    tmpData = []
    logging.debug("RECEIVED EXTERNAL CONTROL")
    logging.debug(data)       
    dmuObj.setDataSubset(data,"simDict", "active_nodes")

# Receive from external Control
dmuObj.addElm("nodes", dict_ext_cntr)
dmuObj.addRx(api_cntr_input, "nodes", "data_nodes")

# Receive active power control
dmuObj.addElm("active_power", simDict)
dmuObj.addRx(active_power_control_input, "active_power", "active_power_control")
# Receive reactive power control
dmuObj.addElm("reactive_power", simDict)
dmuObj.addRx(reactive_power_control_input, "reactive_power", "reactive_power_control")

########################################################################################################
#########################  Section for Sending Signal  #################################################
########################################################################################################

def measurement_output(data, *args):

    reqData = {}
    reqData["data"] =  data
    # logging.debug("voltage sent")
    # logging.debug(data)

    headers = {'content-type': 'application/json'}
    try:
        jsonData = (json.dumps(reqData)).encode("utf-8")
    except:
        logging.warn("Malformed json")
    try:
        for key in data.keys():
            if key == "voltage_measurements":
                result = requests.post("http://pv_centralized:8000/set/voltage/voltage_node/", data=jsonData, headers=headers)
            if key == "pv_input_measurements":
                result = requests.post("http://pv_centralized:8000/set/pv_input/pv_input_node/", data=jsonData, headers=headers)
    except:
        logging.warn("No connection to control")

dmuObj.addRx(measurement_output,"voltage_dict")
dmuObj.addRx(measurement_output,"pv_input_dict")

# read profiles from CSV files
# =======================================================================
profiles = read_profiles()
[PV_list, P_load_list] = profiles.read_csv()

ppc = case()
grid_data = initialize(ppc, [PV_list, P_load_list])


########################################################################################################
#########################  Section for Posting Signal (for Grafana) ####################################
########################################################################################################
grafanaArrayPos = 0
dataDict = []
for i in range(1000):
    dataDict.extend([[0,0]])

for i in range(grid_data["nb"]+1):
    dmuObj.addElm("grafana voltage node_"+str(i), dataDict)
    dmuObj.addElm("grafana reactive power node_"+str(i), dataDict)
    dmuObj.addElm("grafana active power node_"+str(i), dataDict)
    dmuObj.addElm("grafana pv production node_"+str(i), dataDict)

k=800

########################## Initialization vectors  ######################################################
active_nodes = list(np.array(np.matrix(ppc["gen"])[:,0]).flatten())
full_nodes = active_nodes[1:len(active_nodes)]
active_nodes = active_nodes[1:len(active_nodes)]
active_nodes = [float(i)-1 for i in active_nodes]
full_active_power_dict = {}
full_reactive_power_dict = {}
for i in full_nodes:
    full_active_power_dict["node_"+str(int(i))] = 0.0
    full_reactive_power_dict["node_"+str(int(i))] = 0.0


########################################### Main #########################################################
try:
    while True:
        # intialize the dictionaries
        voltage_dict = {}
        pv_input_dict = {}
        
        active_power_value = dmuObj.getDataSubset("active_power_control_dict")
        active_power = active_power_value.get("active_power", None)
        reactive_power_value = dmuObj.getDataSubset("reactive_power_control_dict")
        reactive_power = reactive_power_value.get("reactive_power", None)
        if not active_power:
            p_value = list(full_active_power_dict.values())
        else:
            active_nodes = list(map(lambda x: x.replace('node_',''),list(active_power.keys())))
            active_nodes = [float(i)-1 for i in active_nodes]
            for key in active_power:
                full_active_power_dict[key] = active_power[key]
            p_value = list(full_active_power_dict.values())

        if not reactive_power:
            q_value = list(full_reactive_power_dict.values())
        else:
            active_nodes = list(map(lambda x: x.replace('node_',''),list(reactive_power.keys())))
            active_nodes = [float(i)-1 for i in active_nodes]
            for key in reactive_power:
                full_reactive_power_dict[key] = reactive_power[key]
            q_value = list(full_reactive_power_dict.values())

        pv_profile_k = PV_list[k][:]#[1.4]*len(active_nodes)#
        p_load_k = P_load_list[k][:]#[0.5]*grid_data["nb"]#

        print("active nodes ",active_nodes)
        [v_tot,v_gen,p,c] = run_Power_Flow(ppc,active_nodes,p_value,q_value,pv_profile_k,p_load_k)
      
        for i in range(len(full_nodes)):
            voltage_dict["node_"+str(int(full_nodes[i]))] = v_tot[i]
            pv_input_dict["node_"+str(int(full_nodes[i]))] = pv_profile_k[i]
        dmuObj.setDataSubset({"voltage_measurements": voltage_dict},"voltage_dict")
        dmuObj.setDataSubset({"pv_input_measurements": pv_input_dict},"pv_input_dict")

        for i in range(grid_data["nb"]):
            if i in active_nodes and active_power is not None and  reactive_power is not None:
                sim_list2= [reactive_power["node_"+str(i+1)], time.time()*1000]
                dmuObj.setDataSubset(sim_list2,"grafana reactive power node_"+str(i+1),grafanaArrayPos)
                sim_list3= [active_power["node_"+str(i+1)], time.time()*1000]
                dmuObj.setDataSubset(sim_list3,"grafana active power node_"+str(i+1),grafanaArrayPos)
                if i == 22:
                    sim_list4 = [0.0, time.time()*1000]
                    dmuObj.setDataSubset(sim_list4,"grafana pv production node_"+str(i+1),grafanaArrayPos)
                else:
                    sim_list4 = [pv_profile_k[i], time.time()*1000]
                    dmuObj.setDataSubset(sim_list4,"grafana pv production node_"+str(i+1),grafanaArrayPos)           
            else:
                sim_list2= [0.0, time.time()*1000]
                dmuObj.setDataSubset(sim_list2,"grafana reactive power node_"+str(i+1),grafanaArrayPos)
                sim_list3= [0.0, time.time()*1000]
                dmuObj.setDataSubset(sim_list3,"grafana active power node_"+str(i+1),grafanaArrayPos)
                sim_list4 = [0.0, time.time()*1000]
                dmuObj.setDataSubset(sim_list4,"grafana pv production node_"+str(i+1),grafanaArrayPos)
            sim_list = [v_tot[i], time.time()*1000]
            dmuObj.setDataSubset(sim_list,"grafana voltage node_"+str(i+1),grafanaArrayPos)

        
        grafanaArrayPos = grafanaArrayPos+1
        if grafanaArrayPos>1000:
            grafanaArrayPos = 0

        logging.debug(active_power_value)        
        logging.debug(reactive_power_value)

        time.sleep(0.3)
        k = min(k+1,3000)
        print(k)

except (KeyboardInterrupt, SystemExit):
    print('simulation finished')