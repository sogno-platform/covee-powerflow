# CoVee - Getting Started

## Run the code

To perform the example, run ***covee_main.py***

## Change Configuration

The configuration file ***conf.json*** can be used to select the control strategy, modify the control parameters, select the grid and more.

### "CONTROL_MODULE" 

With **"CONTROL_MODULE"** the control strategy can be selected:
- *"Quadratic_Control_Centralized_DualAscent"*: Based on this [**paper** ](https://www.mdpi.com/1996-1073/13/8/2007)
- *"Quadratic_Control_Centralized_CVXPY"*: Based on quadratic optimization solver [**CVXPY**](https://www.cvxpy.org/index.html)


### "CASE_MODULE" 

With **"CASE_MODULE"** the grid model can be selected:
- *"case_30"* is a 30 nodes distribution grid

Models are defined following the [**PYPOWER**](https://pypi.org/project/PYPOWER/) style.


### "CONTROL_DATA" 

With **"CONTROL_DATA"** the parameters of the control strategies are defined:

- "VMAX" : 
- "VMIN" : 
- "control_variables" : {"DG":[], "ESS":[]}, (*active_power* or *reactive_power*)
- "active_nodes": [*list of nodes where DGs are installed*],  "__comment__": "number of active DGs",
- "active_ESS": [*list of nodes where ESSs are installed*],   "__comment__": "number of active ESSs",

- "v_ref" :   "__comment__": "only for the version with CVXPY" ,
- "M" : 1e1, "__comment__": "value for the relaxation of the constraints, only for the version with CVXPY" ,
- "Weights_CVXPY" : {"DG":{"reactive_power":1.0, "active_power":1.0}, "ESS":{"active_power":1.0}}

### ""POWERFLOW_DATA" " 

With **""POWERFLOW_DATA" "** the parameters of the powerflow are defined:

- "PROFILE" : 
    - {"variable" : {"GEN_PROFILE": *select from covee/powerflow/data/profiles*, "LOAD_PROFILE": *select from covee/powerflow/data/profiles*} , "__comment__": "must be with the format "NAME.csv" 
    - "fix" : {"GEN_PROFILE": 1.0, "LOAD_PROFILE": 0.2, "ITERATIONS": 50} }
- "TYPE_PROFILE" : "variable",  "__comment__": "with fix, the powerflow considers fixed generation and load profiles" 

