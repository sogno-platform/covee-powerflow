import numpy as np
import logging

class additional():

    def __init__(self):
        pass

    def convert_index(self,conf_dict):

        self.conf_dict = conf_dict

        self.conf_dict["CONTROL_DATA"]["active_nodes"] = list(np.array(self.conf_dict["CONTROL_DATA"]["active_nodes"])-1)
        self.conf_dict["CONTROL_DATA"]["active_ESS"] = list(np.array(self.conf_dict["CONTROL_DATA"]["active_ESS"])-1)

        return self.conf_dict

    def set_simulation_dictionary(self, dmuObj, simDict,voltage_dict,active_power_dict,reactive_power_dict,pv_input_dict,active_power_ESS_dict,pmu_input,dict_ext_cntr):
        # add the simulation dictionary to mmu object
        dmuObj.addElm("simDict", simDict)
        dmuObj.addElm("voltage_dict", voltage_dict)
        dmuObj.addElm("active_power_dict", active_power_dict)
        dmuObj.addElm("reactive_power_dict", reactive_power_dict)
        dmuObj.addElm("pv_input_dict", pv_input_dict)
        dmuObj.addElm("active_power_ESS_dict", active_power_ESS_dict)
        dmuObj.addElm("pmu_input", pmu_input)
        dmuObj.addElm("flex_request_dict", {})
        def api_cntr_input(data, uuid, name,  *args):
            tmpData = []
            logging.debug("RECEIVED EXTERNAL CONTROL")
            logging.debug(data)
            dmuObj.setDataSubset(data["nodes"],"simDict", "active_nodes")
            dmuObj.setDataSubset(data["ESS"],"simDict", "ESS_nodes")
        # Receive from external Control
        dmuObj.addElm("nodes", dict_ext_cntr)
        dmuObj.addElm("test", {})
        dmuObj.addElmMonitor(api_cntr_input, "nodes", "data_nodes")
        dmuObj.addElmMonitor(api_cntr_input, "test", "data_test")
        # Receive voltage
        dmuObj.addElm("voltage", simDict)
        # Receive pv_input
        dmuObj.addElm("pv_input", simDict)
        # Receive pmu_meas
        dmuObj.addElm("pmu_meas", {})
        # Receive flexibility_input
        dmuObj.addElm("flex_input", {})

        return dmuObj
    
    def system_info(self, ppc, BUS_TYPE, active_nodes, active_ESS):
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

        grid_data = {
                        "baseMVA":baseMVA,
                        "branch":branch,
                        "pcc":pcc,
                        "bus":bus,
                        "gen":gen,
                        "nb":nb,
                        "ng":ng,
                        "nbr":nbr, 
                        "full_nodes": list(np.array(np.matrix(ppc["gen"])[:,0]).flatten()),
                        "total_control_nodes" : list(set(active_nodes+active_ESS))
                        }
        
        reactive_power = [0.0]*len(active_nodes)
        active_power = [0.0]*len(active_nodes)
        active_power_ESS = [0.0]*len(active_ESS)

        self.active_nodes = active_nodes
        self.active_ESS = active_ESS

        return grid_data, reactive_power, active_power, active_power_ESS

    def update_dict(self, output, reactive_power_dict, active_power_dict, active_power_ESS_dict):
        k = 0
        if any(x =="reactive_power" for x in self.conf_dict["CONTROL_DATA"]["control_variables"]["DG"]):
            for pv in self.active_nodes:
                reactive_power_dict['node_'+str(int(pv)+1)]  = output["DG"]["reactive_power"][k]
                k +=1
        k = 0
        if any(x =="active_power" for x in self.conf_dict["CONTROL_DATA"]["control_variables"]["DG"]):
            for pv in self.active_nodes:
                active_power_dict['node_'+str(int(pv)+1)]  = output["DG"]["active_power"][k]
                k +=1
        k = 0
        if any(x =="active_power" for x in self.conf_dict["CONTROL_DATA"]["control_variables"]["ESS"]):
            for ess in self.active_ESS:
                active_power_ESS_dict['node_'+str(int(ess)+1)] = output["ESS"]["active_power"][k]
                k+=1

        return reactive_power_dict, active_power_dict, active_power_ESS_dict
            

    

