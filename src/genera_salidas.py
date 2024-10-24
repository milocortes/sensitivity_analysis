import copy
import datetime as dt
import importlib # needed so that we can reload packages
import ipywidgets as wdg
import matplotlib.pyplot as plt
import os, os.path
import numpy as np
import pandas as pd
import pathlib
import sys
import time
from typing import Union
import warnings

from info_grupos import prefijos,grupos_normaliza

warnings.filterwarnings("ignore")

# add SISEPUEDE to path
dir_py = pathlib.Path(os.path.realpath(".")).parents[1]
if str(dir_py) not in sys.path:
    sys.path.append(str(dir_py))

## Define paths

FILE_PATH = os.getcwd()
build_path = lambda PATH : os.path.abspath(os.path.join(*PATH))

DATA_PATH = build_path([FILE_PATH, "..", "datos"])
OUTPUT_PATH = build_path([FILE_PATH, "..", "output"])

SSP_OUTPUT_PATH = build_path([OUTPUT_PATH, "ssp"])

REAL_DATA_FILE_PATH = build_path([DATA_PATH, "real_data.csv"]) 

SALIDAS_EXPERIMENTOS_PATH = build_path([OUTPUT_PATH, "experimentos"]) 

INPUTS_ESTRESADOS_PATH = build_path([SALIDAS_EXPERIMENTOS_PATH, "input_estresados"])
OUTPUTS_ESTRESADOS_PATH = build_path([SALIDAS_EXPERIMENTOS_PATH, "output_estresados"])

##  IMPORT SISEPUEDE EXAMPLES AND TRANSFORMERS
import sys 
from sisepuede.manager.sisepuede_examples import SISEPUEDEExamples
import sisepuede.core.support_classes as sc
import sisepuede.transformers as trf
import sisepuede.utilities._toolbox as sf


import sisepuede.transformers.transformers as trfs
importlib.reload(trfs)

import sisepuede as si

import pickle

### Cargamos datos de ejemplo de costa rica

examples = SISEPUEDEExamples()
cr = examples("input_data_frame")

df_input = pd.read_csv(REAL_DATA_FILE_PATH)
df_input["region"] = "iran"
df_input[list(set(cr.columns) - set(df_input.columns))] = cr[list(set(cr.columns) - set(df_input.columns))]

campos_estresar = []
for p in prefijos:
    campos_estresar.extend(
        [i for i in df_input.columns if p in i ]
    )

with open('sample_scaled.pickle', 'rb') as handle:
    sample_scaled = pickle.load(handle)

#with open("contador.txt", "r") as file:
#    id_experimento = int(file.readlines()[0].replace("\n",""))

id_experimento = int(sys.argv[1])

print(id_experimento)
    
df_estresado = df_input.copy()
df_estresado[campos_estresar]  = (df_input[campos_estresar]*sample_scaled[id_experimento]).to_numpy()

### Normaliza grupo de variables para que sumen 1 en conjunto

for grupo in grupos_normaliza:
    vars_grupo = [i for i in df_estresado.columns if grupo in i]

    df_estresado[vars_grupo] = df_estresado[vars_grupo]/df_estresado[vars_grupo].sum(axis = 1).to_numpy()[:,np.newaxis]

###---------------------------------------------------------------
transformers = trfs.Transformers(
        {},
        df_input = df_estresado,
    )

# set some shortcuts
mat = transformers.model_attributes
time_periods = sc.TimePeriods(mat);

# set an ouput path and instantiate

trf.instantiate_default_strategy_directory(
        transformers,
        SSP_OUTPUT_PATH,
    )

# then, you can load this back in after modifying (play around with it)
transformations = trf.Transformations(
        SSP_OUTPUT_PATH,
        transformers = transformers,
    )

strategies = trf.Strategies(
        transformations,
        export_path = "transformations",
        prebuild = True,
    )

# call the example
df_vargroups = examples("variable_trajectory_group_specification")

strategies.build_strategies_to_templates(
        df_trajgroup = df_vargroups,
        include_simplex_group_as_trajgroup = True,
        strategies = [0, "AF:ALL"],
    )

ssp = si.SISEPUEDE(
        "calibrated",
        initialize_as_dummy = False, # no connection to Julia is initialized if set to True
        regions = ["iran"],
        db_type = "csv",
        strategies = strategies,
        try_exogenous_xl_types_in_variable_specification = True,
    )


dict_run = {
        ssp.key_future: [0],
        ssp.key_design: [0],
        ssp.key_strategy: [
            0,
            strategies.get_strategy_id("EN:ALL"),
        ],
    }


# we'll save inputs since we're doing a small set of runs
ssp(
        dict_run,
        save_inputs = True,
    )

INPUTS_ESTRESADOS_FILE_PATH = build_path([INPUTS_ESTRESADOS_PATH, f"input_estresados_{id_experimento}.csv"])
OUTPUTS_ESTRESADOS_FILE_PATH = build_path([OUTPUTS_ESTRESADOS_PATH, f"output_estresados_{id_experimento}.csv"])


df_out = ssp.read_output(None)
df_out.to_csv(OUTPUTS_ESTRESADOS_FILE_PATH, index=False)
df_estresado[campos_estresar].to_csv(INPUTS_ESTRESADOS_FILE_PATH, index=False)


#with open("contador.txt", "w") as file:
#    file.write(f"{id_experimento + 1}\n")


