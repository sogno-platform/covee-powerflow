from powerflow_class.runPF_class import runPF_class
import powerflow_class.utils as utils
import numpy as np
from pypower.api import *
from pypower.ext2int import ext2int
import csv
import os
import coloredlogs, logging, threading
from threading import Thread, Event
from dmu.dmu import dmu
from dmu.httpSrv import httpSrv
from dmu.mqttClient import mqttClient
import time
import json
import argparse
import paho.mqtt.client as mqtt
import utils as utils


parser = argparse.ArgumentParser()
parser.add_argument('--ext_port', nargs='*', required=True)
args = vars(parser.parse_args())
ext_port = args['ext_port'][0]

# Read json file and set Control Strategy and Case 
# =====================================================================================================
with open("./examples/conf.json", "r") as f:
    conf_dict = json.load(f)

module_obj = utils.select(conf_dict)
case = module_obj.select_case()
# =====================================================================================================

# Get the grid data infos
# =====================================================================================================
additional = utils.additional() 

conf_dict = additional.convert_index(conf_dict)
active_nodes = conf_dict["CONTROL_DATA"]["active_nodes"]   # number of active DGs
active_ESS = conf_dict["CONTROL_DATA"]["active_ESS"]       # number of active ESSs
active_nodes_old = active_nodes
active_ESS_old = active_ESS

logging.info("active_nodes"+str(active_nodes))

ppc_obj = case.case_()
ppc = ppc_obj.case()
ppc = ext2int(ppc)      # convert to continuous indexing starting from 0
BUS_TYPE = 1
[grid_data,reactive_power,active_power,active_power_ESS] = additional.system_info(ppc,BUS_TYPE, active_nodes, active_ESS)

# Initialize the powerflow
# =====================================================================================================
run_PF = runPF_class(active_nodes, active_ESS, grid_data["full_nodes"], grid_data["total_control_nodes"], conf_dict["POWERFLOW_DATA"]["uncontrolled_nodes"] )
profiles = run_PF.read_profiles(conf_dict, grid_data)
full_active_power_dict = {}
full_reactive_power_dict = {}
full_active_power_ESS_dict = {}
v_old =  [0.0]*len(grid_data["full_nodes"])
for i in grid_data["full_nodes"]:
    full_active_power_dict["node_"+str(int(i))] = 0.0
    full_reactive_power_dict["node_"+str(int(i))] = 0.0
    full_active_power_ESS_dict["node_"+str(int(i))] = 0.0
iter_k = 0

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
    # logging.debug("RECEIVED EXTERNAL CONTROL")
    # logging.debug(data)       
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

# Receive from PMU
dmuObj.addElm("edgePMU3", {})
mqttObj.attachSubscriber("/location_10003/30025/edgePMU3 ch1 amplitude","json","edgePMU3")
dmuObj.addElm("edgePMU4", {})
mqttObj.attachSubscriber("/location_10001/30001/edgePMU4 ch1 amplitude","json","edgePMU4")
dmuObj.addElm("edgePMU9", {})
mqttObj.attachSubscriber("/location_10002/30013/edgePMU9 ch1 amplitude","json","edgePMU9")

# Receive from Kibertnet
dmuObj.addElm("location4", {})
mqttObj.attachSubscriber("/location_4/4/operationPower","json","location4")
dmuObj.addElm("location7", {})
mqttObj.attachSubscriber("/location_7/7/operationPower","json","location7")
dmuObj.addElm("location34", {})
mqttObj.attachSubscriber("/location_34/34/operationPower","json","location34")
dmuObj.addElm("location35", {})
mqttObj.attachSubscriber("/location_35/35/operationPower","json","location35")
dmuObj.addElm("location36", {})
mqttObj.attachSubscriber("/location_36/36/operationPower","json","location36")

########################################################################################################
#########################  Section for Sending Signal  #################################################
########################################################################################################

mqttObj.attachPublisher("/voltage_control/measuremnts/voltage","json","voltage_dict")
mqttObj.attachPublisher("/voltage_control/measuremnts/pv","json","pv_input_dict")
mqttObj.attachPublisher("measurements","json","measurements")

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
        # print("RECEIVED: ",active_power )

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

        # p_value = list(np.array(p_value, dtype=np.float32))
        # logging.debug("received active power " +str(p_value))

        for k in range(len(active_nodes)):
            pv_input_dict["node_"+str(int(active_nodes[k])+1)] = profiles["gen_profile"][iter_k][int(k)]
    
        '''
        Integrate the Kibernet measurements
        '''
        if dmuObj.getDataSubset("location4"):
            pv_input_dict["node_27"] = dmuObj.getDataSubset("location4","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
            profiles["gen_profile"][iter_k][27] = dmuObj.getDataSubset("location4","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
        if dmuObj.getDataSubset("location7"):
            pv_input_dict["node_10"] = dmuObj.getDataSubset("location7","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
            profiles["gen_profile"][iter_k][10] = dmuObj.getDataSubset("location7","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
        if dmuObj.getDataSubset("location34"):
            pv_input_dict["node_11"] = dmuObj.getDataSubset("location34","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
            profiles["gen_profile"][iter_k][11] = dmuObj.getDataSubset("location34","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
        if dmuObj.getDataSubset("location35"):
            pv_input_dict["node_12"] = dmuObj.getDataSubset("location35","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
            profiles["gen_profile"][iter_k][12] = dmuObj.getDataSubset("location35","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
        if dmuObj.getDataSubset("location36"):
            pv_input_dict["node_13"] = dmuObj.getDataSubset("location36","value")/conf_dict["POWERFLOW_DATA"]["P_base"]
            profiles["gen_profile"][iter_k][13] = dmuObj.getDataSubset("location36","value")/conf_dict["POWERFLOW_DATA"]["P_base"]


        print("active nodes ",active_nodes)
        ################################# Run the PowerFlow #####################################
        ##############################################################################################################
        [v_tot, v_gen, p, c, p_load, v_pv, v_ess] = run_PF.run_Power_Flow(ppc,p_value,q_value,p_ESS_value,profiles["gen_profile"][iter_k],profiles["load_profile"][iter_k])

        for i in range(len(grid_data["full_nodes"])):
            voltage_dict["node_"+str(int(grid_data["full_nodes"][i]))] = v_tot[int(grid_data["full_nodes"][i])]

        '''
        Integrate the PMU measurements
        '''
        if dmuObj.getDataSubset("edgePMU3"):
            voltage_dict["node_7"] = dmuObj.getDataSubset("edgePMU3","value")/conf_dict["POWERFLOW_DATA"]["V_base"]
        if dmuObj.getDataSubset("edgePMU4"):
            voltage_dict["node_11"] = dmuObj.getDataSubset("edgePMU4","value")/conf_dict["POWERFLOW_DATA"]["V_base"]
        if dmuObj.getDataSubset("edgePMU9"):
            pv_input_dict["node_23"] = dmuObj.getDataSubset("edgePMU9","value")/conf_dict["POWERFLOW_DATA"]["V_base"]

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
        measurements.update({"voltage_measurements": [v_tot[int(grid_data["full_nodes"][i])-1]*230 for i in range(len(grid_data["full_nodes"]))]})
        measurements.update({"pv_input_measurements": [ p[i]*6e3 for i in range(len(p))]})
        measurements.update({"active_power_control_dict": [p_value[i]*6e3 for i in range(len(p_value))]})
        measurements.update({"reactive_power_control_dict": [q_value[i]*6e3 for i in range(len(q_value))]})
        measurements.update({"active_power_ESS_control_dict": [p_ESS_value[i]*6e3 for i in range(len(p_ESS_value))]})      
        measurements.update({"reactive_percentage": [(-q_value[i]-0.31512)*6e3 for i in range(len(q_value))]})      
        dmuObj.setDataSubset(measurements,"measurements")


        # logging.debug(active_power_value)        
        # logging.debug(reactive_power_value)

        time.sleep(0.5)
        iter_k += 1
        if iter_k == 2159:
            iter_k = 0

except (KeyboardInterrupt, SystemExit):
    logging.info('simulation finished')
