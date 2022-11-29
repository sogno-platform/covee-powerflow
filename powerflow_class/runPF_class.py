from pypower.api import *
from pypower.ext2int import ext2int
from pypower.idx_brch import F_BUS, T_BUS, TAP, BR_R, BR_X, BR_B, RATE_A, PF, QF, PT, QT
from pypower.idx_bus import BUS_I,BUS_TYPE, REF, PD, QD, VM, VA, VMAX, VMIN, NONE
from pypower.idx_gen import GEN_BUS, PG, QG, PMAX, PMIN, QMAX, QMIN, VG, GEN_STATUS
from pypower.int2ext import int2ext

from powerflow_class.csv_files.read_profiles import read_profiles

from scipy.sparse import issparse, vstack, hstack, csr_matrix as sparse
from numpy import flatnonzero as find

import numpy as np
from pypower.ppoption import ppoption

from powerflow_class.csv_files.read_profiles import read_profiles



class runPF_class():

    def __init__(self, active_nodes, active_ESS, full_nodes, total_nodes,uncontrolled_nodes):
        self.active_nodes = active_nodes
        self.active_ESS = active_ESS
        self.full_nodes = full_nodes
        self.total_nodes = total_nodes
        self.uncontrolled_nodes = uncontrolled_nodes

    def read_profiles(self, conf_dict, grid_data):
        profile_out = {}
        # read profiles from CSV files
        # =======================================================================
        profiles = read_profiles(conf_dict, grid_data)
        [PV_list, P_load_list] = profiles.read_csv()

        profile_out = {"gen_profile" : PV_list,"load_profile": P_load_list}

        return profile_out

    def initialize(self, name, profiles):
        # Input Data
        # =============================================================
        ppc = name
        pvproduction = profiles[0]
        demandprofile_P = profiles[1]

        bt = ppc["bus"][:, 1]

        ## determine which buses, branches, gens are connected and
        ## in-service
        nb = ppc["bus"].shape[0]
        n2i = sparse((range(nb), (ppc["bus"][:, BUS_I], np.zeros(nb))),
                        shape=(max(ppc["bus"][:, BUS_I].astype(int)) + 1, 1))
        n2i = np.array( n2i.todense().flatten() )[0, :] # as 1D array
        bs = (bt != NONE)                               ## bus status
        gs = ( (ppc["gen"][:, GEN_STATUS] > 0) &          ## gen status
                bs[ n2i[ppc["gen"][:, GEN_BUS].astype(int)] ] )
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

    def run_Power_Flow(self, ppc, active_power,reactive_power,active_power_ess,pv_profile,load_profile):
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

        c = self.active_nodes
        for i in range(1,ng):
            if gen[i][0] in c:
                pass
            else:
                np.delete(ppc["gen"],(i),axis=0)       

        #print("Number of Reactive Power Compensator = ",int(len(c)))
                
        # initialize vectors
        # =====================================================================
        q = [0.0] * int(len(c))
        p = []
        v_gen = []
        v_tot = []
        p_load = []
        v_tot = []
        v_gen = []
        v_pv = []
        v_ess = []

        ############## SET THE ACTUAL LOAD AND GEN VALUES ###############
        s = 0
        for i in range(int(nb)):
            bus[i][PD] = load_profile[i] 
            bus[i][QD] = 0.0
            if self.active_ESS != None and any(bus[i][BUS_I] == float(self.active_ESS[k]) for k in range(len(self.active_ESS))):
                if active_power_ess[s]:
                    bus[i][PD] = load_profile[i]-active_power_ess[s]
                    s +=1
        r = 0
        for j in range(int(ng)):
            gen[j][PG] = 0.0
            gen[j][QG] = 0.0
            if any(gen[j][GEN_BUS] == float(self.active_nodes[k]) for k in range(len(self.active_nodes))):                
                gen[j][QG] = reactive_power[j]
                gen[j][PG] = pv_profile[r]+active_power[j]
                r +=1
            if any(gen[j][GEN_BUS] == float(self.uncontrolled_nodes[k]) for k in range(len(self.uncontrolled_nodes))):  
                gen[j][PG] = pv_profile[r]
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

        for i in self.total_nodes:
            v_gen.append(bus_results[int(i)][VM])
        for i in self.full_nodes:
            v_tot.append(bus_results[int(i)][VM])
        for i in self.active_nodes:
            v_pv.append(bus_results[int(i)][VM])
        if self.active_ESS != None:
            for i in self.active_ESS:
                v_ess.append(bus_results[int(i)][VM])

        for i in range(int(len(c))):
            p.append(gen[i+1][PG])
            p_load.append(bus[int(c[i])][PD])
        
        return v_tot,v_gen,p,c,p_load, v_pv, v_ess