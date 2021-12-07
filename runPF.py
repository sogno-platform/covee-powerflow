from pypower.api import *
from pypower.ext2int import ext2int
from pypower.idx_brch import F_BUS, T_BUS, TAP, BR_R, BR_X, BR_B, RATE_A, PF, QF, PT, QT
from pypower.idx_bus import BUS_I, BUS_TYPE, REF, PD, QD, VM, VA, VMAX, VMIN
from pypower.idx_gen import GEN_BUS, PG, QG, PMAX, PMIN, QMAX, QMIN, VG
from pypower.int2ext import int2ext

from cases.case_10_nodes import case_10_nodes as case
from csv_files.read_profiles import read_profiles

import numpy as np
from pypower.ppoption import ppoption
import csv
import os
import coloredlogs, logging, threading
from threading import Thread, Event
from submodules.dmu.dmu import dmu
from submodules.dmu.httpSrv import httpSrv
from submodules.dmu.mqttClient import mqttClient
import time
import sys
import requests
import json
import csv
import argparse
import paho.mqtt.client as mqtt

from datetime import timedelta

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

if bool(os.getenv('MQTT_ENABLED')):
    mqtt_url = str(os.getenv('MQTTURL'))
    mqtt_port = int(os.getenv('MQTTPORT'))
    mqtt_user = str(os.getenv('MQTTUSER'))
    mqtt_password = str(os.getenv('MQTTPASS'))
else:
    mqtt_url = "mqtt"
    mqtt_port = 1883
    mqtt_password = ""
    mqtt_user = ""
    
    # logging.debug("MQTT COnnection Details "+ mqtt_url+" : "+mqtt_port)

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

def run_Power_Flow(ppc, active_nodes, active_ESS, active_power,reactive_power,active_power_ESS,pv_profile,load_profile):
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
    s = 0
    for i in range(int(nb)):
        bus[i][PD] = load_profile[i] 
        bus[i][QD] = 0.0
        if any(bus[i][BUS_I] == float(active_ESS[k]) for k in range(len(active_ESS))):
            bus[i][PD] = load_profile[i]-active_power_ESS[s]
            s +=1
    r = 0
    for j in range(int(ng)):
        gen[j][PG] = 0.0#+active_power[j]
        gen[j][QG] = 0.0#reactive_power[j]
        if any(gen[j][GEN_BUS] == float(active_nodes[k]) for k in range(len(active_nodes))):
            gen[j][QG] = reactive_power[r]
            gen[j][PG] = pv_profile[r]+active_power[r]
            r +=1
        else: 
            pass

    ppc['bus'] = bus
    ppc['gen'] = gen
    ppc = int2ext(ppc)


    ############# RUN PF ########################
    opt = ppoption(VERBOSE=0, OUT_ALL=0, UT_SYS_SUM=0)
    results = runpf(ppc, opt)
    bus_results = results[0]['bus']

    for i in range(grid_data["nb"]):
        v_tot.append(bus_results[int(i)][VM])

    for i in range(int(len(c))):
        v_gen.append(v_tot[int(c[i])-1])
        p.append(gen[i][PG])
        
    
    return v_tot,v_gen,p,c


############################ Start the Server #######################################################

''' Initialize objects '''
dmuObj = dmu()

''' Start mqtt client '''
mqttObj = mqttClient(mqtt_url, dmuObj, mqtt_port, mqtt_user, mqtt_password)

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
active_power_ESS_control_dict = {}
pv_input_dict = {}
measurements = {}

# add the simulation dictionary to mmu object
dmuObj.addElm("simDict", simDict)
dmuObj.addElm("voltage_dict", voltage_dict)
dmuObj.addElm("active_power_control_dict", active_power_control_dict)
dmuObj.addElm("reactive_power_control_dict", reactive_power_control_dict)
dmuObj.addElm("active_power_ESS_control_dict", active_power_ESS_control_dict)
dmuObj.addElm("pv_input_dict", pv_input_dict)
dmuObj.addElm("measurements",measurements)

########################################################################################################
#########################  Section for Receiving Signal  ###############################################
########################################################################################################

def active_power_control_input(data, uuid, name,  *args):
    active_power_control_dict = {}  
    dmuObj.setDataSubset(data,"active_power_control_dict")
def reactive_power_control_input(data, uuid, name,  *args):
    reactive_power_control_dict = {}  
    dmuObj.setDataSubset(data,"reactive_power_control_dict")

def api_cntr_input(data, uuid, name,  *args):   
    tmpData = []
    logging.debug("RECEIVED EXTERNAL CONTROL")
    logging.debug(data)       
    dmuObj.setDataSubset(data,"simDict", "active_nodes")

# Receive from external Control
dmuObj.addElm("nodes", dict_ext_cntr)
dmuObj.addElmMonitor(api_cntr_input, "nodes", "data_nodes")

# Receive active power control
dmuObj.addElm("active_power", simDict)
mqttObj.attachSubscriber("/voltage_control/control/active_power", "json","active_power_control_dict")
# Receive reactive power control
dmuObj.addElm("reactive_power", simDict)
mqttObj.attachSubscriber("/voltage_control/control/reactive_power", "json","reactive_power_control_dict")
# Receive active power ESS control
dmuObj.addElm("active_power_ESS", simDict)
mqttObj.attachSubscriber("/voltage_control/control/active_power_ESS", "json","active_power_ESS_control_dict")

########################################################################################################
#########################  Section for Sending Signal  #################################################
########################################################################################################

mqttObj.attachPublisher("/voltage_control/measuremnts/voltage","json","voltage_dict")
mqttObj.attachPublisher("/voltage_control/measuremnts/pv","json","pv_input_dict")
mqttObj.attachPublisher("measurements","json","measurements")

# Send meas to pmu
dmuObj.addElm("powerflow_output", {})
mqttObj.attachPublisher("/edgeflex/edgepmu0/ch0/voltage_rms","json","powerflow_output")

# read profiles from CSV files
# =======================================================================
profiles = read_profiles()
[PV_list, P_load_list] = profiles.read_csv()

ppc = case()
grid_data = initialize(ppc, [PV_list, P_load_list])

iter_k=0

########################## Initialization vectors  ######################################################
active_nodes = list(np.array(np.matrix(ppc["gen"])[:,0]).flatten())
full_nodes = active_nodes[1:len(active_nodes)]
active_nodes = active_nodes[1:len(active_nodes)]
active_nodes = [float(i)-1 for i in active_nodes]
active_ESS = active_nodes
full_active_power_dict = {}
full_reactive_power_dict = {}
full_active_power_ESS_dict = {}
v_old =  [0.0]*len(full_nodes)
for i in full_nodes:
    full_active_power_dict["node_"+str(int(i))] = 0.0
    full_reactive_power_dict["node_"+str(int(i))] = 0.0
    full_active_power_ESS_dict["node_"+str(int(i))] = 0.0

voltage_tot = []
active_power_pv_tot = []
reactive_power_pv_tot = []
active_power_ess_tot = []
load_tot = []
active_nodes_list = []
########################################### Main #########################################################
try:
    while True:
        # intialize the dictionaries
        voltage_dict = {}
        pv_input_dict = {}
        measurements = {}
        pv_profile_k = []
        p_load_k = []
        
        active_power_value = dmuObj.getDataSubset("active_power_control_dict")
        active_power = active_power_value.get("active_power", None)
        logging.info(active_power)
        reactive_power_value = dmuObj.getDataSubset("reactive_power_control_dict")
        reactive_power = reactive_power_value.get("reactive_power", None)

        active_power_ESS_value = dmuObj.getDataSubset("active_power_ESS_control_dict")
        active_power_ESS = active_power_ESS_value.get("active_power_ESS", None)

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
        
        if not active_power_ESS:
            p_ESS_value = list(full_active_power_ESS_dict.values())
        else:
            active_ESS = list(map(lambda x: x.replace('node_',''),list(active_power_ESS.keys())))
            active_ESS = [float(i)-1 for i in active_ESS]
            for key in active_power_ESS:
                full_active_power_ESS_dict[key] = active_power_ESS[key]
            p_ESS_value = list(full_active_power_ESS_dict.values())


        profile = "fixed"
        if profile == "fixed":
            pv_profile_k = [2.0]*len(active_nodes)
        elif profile == "variable":
            pv_profile_k = (1.0*np.array(PV_list[k][:])).tolist()
            pv_profile_k.extend((1.0*np.array(PV_list[k][:])).tolist())
        else:
            print("error")

        p_load_k = [0.05]*grid_data["nb"]#(P_load_list[k][:]).tolist()

        print("active nodes ",active_nodes)
        [v_tot,v_gen,p,c] = run_Power_Flow(ppc,active_nodes, active_ESS,p_value,q_value,p_ESS_value,pv_profile_k,p_load_k)


        for i in range(len(full_nodes)):
            voltage_dict["node_"+str(int(full_nodes[i]))] = v_tot[int(full_nodes[i])-1]
        for k in range(len(active_nodes)):
            pv_input_dict["node_"+str(int(active_nodes[k])+1)] = pv_profile_k[int(k)]
        print(pv_input_dict)

        if iter_k%1 == 0 and iter_k!=0:
            dmuObj.setDataSubset({"voltage_measurements": voltage_dict},"voltage_dict")
            dmuObj.setDataSubset({"pv_input_measurements": pv_input_dict},"pv_input_dict")
            if str(os.getenv('MQTT_ENABLED')) == "true":
                dmuObj.setDataSubset({"voltage_node": voltage_dict["node_"+str(int(active_nodes[-1]))]*115.0},"powerflow_output")
        else:
            pass
        
        print("voltage",voltage_dict)

        measurements={"VMAX":126.5}
        measurements.update({"VMIN":18e3})
        measurements.update({"voltage_measurements": [v_tot[int(full_nodes[i])-1]*230 for i in range(len(full_nodes))]})
        measurements.update({"pv_input_measurements": [ p[i]*6e3 for i in range(len(p))]})
        measurements.update({"active_power_control_dict": [p_value[i]*6e3 for i in range(len(p_value))]})
        measurements.update({"reactive_power_control_dict": [q_value[i]*6e3 for i in range(len(q_value))]})
        measurements.update({"active_power_ESS_control_dict": [p_ESS_value[i]*6e3 for i in range(len(p_ESS_value))]})      
        measurements.update({"reactive_percentage": [(-q_value[i]-0.31512)*6e3 for i in range(len(q_value))]})      
        dmuObj.setDataSubset(measurements,"measurements")


        logging.debug(active_power_value)        
        logging.debug(reactive_power_value)

        voltage_tot.append(v_tot)
        active_power_pv_tot.append(p)
        reactive_power_pv_tot.append(q_value)
        active_power_ess_tot.append(p_ESS_value)
        load_tot.append(p_load_k)
        active_nodes_list.append(active_nodes)

        time.sleep(0.5)
        iter_k += 1
        if iter_k == 2159:
            iter_k = 0
        #k = min(k+1,2159)
        # print("K = ",k)
        # if k >= 2159:
        #     rows = voltage_tot
        #     with open('powerflow/csv_files/voltage.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        #         wr = csv.writer(csv_file)
        #         for row in rows:
        #             wr.writerow(row)
        #     csv_file.close()

        #     rows = active_power_pv_tot
        #     with open('powerflow/csv_files/active_power_pv_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        #         wr = csv.writer(csv_file)
        #         for row in rows:
        #             wr.writerow(row)
        #     csv_file.close()

        #     rows = reactive_power_pv_tot
        #     with open('powerflow/csv_files/reactive_power_pv_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        #         wr = csv.writer(csv_file)
        #         for row in rows:
        #             wr.writerow(row)
        #     csv_file.close()

        #     rows = active_power_ess_tot
        #     with open('powerflow/csv_files/active_power_ess_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        #         wr = csv.writer(csv_file)
        #         for row in rows:
        #             wr.writerow(row)
        #     csv_file.close()

        #     rows = load_tot
        #     with open('powerflow/csv_files/load_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        #         wr = csv.writer(csv_file)
        #         for row in rows:
        #             wr.writerow(row)
        #     csv_file.close()

        #     rows = active_nodes_list
        #     with open('powerflow/csv_files/active_nodes_list.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        #         wr = csv.writer(csv_file)
        #         for row in rows:
        #             wr.writerow(row)
        #     csv_file.close()

        #     print('simulation finished')
        #     break

except (KeyboardInterrupt, SystemExit):

    rows = voltage_tot
    with open('powerflow/csv_files/voltage.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        wr = csv.writer(csv_file)
        for row in rows:
            wr.writerow(row)
    csv_file.close()

    rows = active_power_pv_tot
    with open('powerflow/csv_files/active_power_pv_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        wr = csv.writer(csv_file)
        for row in rows:
            wr.writerow(row)
    csv_file.close()

    rows = reactive_power_pv_tot
    with open('powerflow/csv_files/reactive_power_pv_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        wr = csv.writer(csv_file)
        for row in rows:
            wr.writerow(row)
    csv_file.close()

    rows = active_power_ess_tot
    with open('powerflow/csv_files/active_power_ess_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        wr = csv.writer(csv_file)
        for row in rows:
            wr.writerow(row)
    csv_file.close()

    rows = load_tot
    with open('powerflow/csv_files/load_tot.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        wr = csv.writer(csv_file)
        for row in rows:
            wr.writerow(row)
    csv_file.close()

    rows = active_nodes_list
    with open('powerflow/csv_files/active_nodes_list.csv', 'w+', encoding="ISO-8859-1", newline='') as csv_file:
        wr = csv.writer(csv_file)
        for row in rows:
            wr.writerow(row)
    csv_file.close()

    print('simulation finished')