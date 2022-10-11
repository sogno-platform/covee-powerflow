import numpy as np

class additional():

    def __init__(self):
        pass

    def convert_index(self,conf_dict):

        self.conf_dict = conf_dict

        self.conf_dict["CONTROL_DATA"]["active_nodes"] = list(np.array(self.conf_dict["CONTROL_DATA"]["active_nodes"])-1)
        self.conf_dict["CONTROL_DATA"]["active_ESS"] = list(np.array(self.conf_dict["CONTROL_DATA"]["active_ESS"])-1)

        return self.conf_dict

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

    def update_MPC_dict(self, output_MPC, reactive_power_, active_power_, active_power_ESS_, step):
        k = 0
        if any(x =="reactive_power" for x in self.conf_dict["CONTROL_DATA"]["control_variables"]["DG"]):
            for pv in self.active_nodes:
                reactive_power_['node_'+str(int(pv)+1)] = output_MPC["DG"]["reactive_power"][k,step+1] 
                k +=1
        k = 0
        if any(x =="active_power" for x in self.conf_dict["CONTROL_DATA"]["control_variables"]["DG"]):
            for pv in self.active_nodes:
                active_power_['node_'+str(int(pv)+1)]  = output_MPC["DG"]["active_power"][k,step+1] 
                k +=1
        k = 0
        if any(x =="active_power" for x in self.conf_dict["CONTROL_DATA"]["control_variables"]["ESS"]):
            for ess in self.active_ESS:
                active_power_ESS_['node_'+str(int(ess)+1)] = output_MPC["ESS"]["active_power"][k,step+1] 
                k+=1

        return reactive_power_, active_power_, active_power_ESS_
            

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
            

    

