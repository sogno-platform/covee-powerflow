import json
import sys
from importlib import import_module
import coloredlogs, logging, threading


class select():

    def __init__(self, conf_dict):
        self.conf_dict = conf_dict
        self.control_module = None
        self.case_module = None

    def select_online_control(self):
                      
        self.control_module = 'covee.control_strategies.'+self.conf_dict["CONTROL_MODULE"]
        try: 
            module = import_module(self.control_module)
        except:
            module = None
            logging.error("Uncorrect definition of the control in conf.json. Please look at the folder control_strategies")

        return module

    def select_MPC_control(self):
                      
        self.control_module = 'covee.control_strategies.'+self.conf_dict["MPC_MODULE"]
        try: 
            module = import_module(self.control_module)
        except:
            module = None
            logging.error("Uncorrect definition of the control in conf.json. Please look at the folder control_strategies")

        return module


    def select_case(self):

        self.case_module = 'cases.'+self.conf_dict["CASE_MODULE"]
        try: 
            module = import_module(self.case_module)
        except:
            module = None
            logging.error("Uncorrect definition of the case in conf.json. Please look at the folder cases")
        
        return module

