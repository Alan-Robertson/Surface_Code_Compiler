import sys
import numpy as np
from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import CPHASE_theta, Z_theta
from surface_code_routing.compiled_qcb import compile_qcb



j = int(sys.argv[1])

prec = int(3 / 2 * (j ** 2 + j))

for i in range(1, j):
    dag = DAG('qft')
    dag.add_gate(INIT('x'))
     
    dag.add_gate(Z_theta(1, 2 ** (i + 1), precision=int(3 * (np.log2(j) + 4)))('x'))

    print(f"{i} : ###")
    print(dag.gates)
    print("###")
