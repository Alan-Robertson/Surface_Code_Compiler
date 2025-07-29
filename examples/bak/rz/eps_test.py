from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import Z_theta
from surface_code_routing.lib_instructions import T_Factory, T, Toffoli
from surface_code_routing.symbol import Symbol
from surface_code_routing.compiled_qcb import compile_qcb

import sys

def arbitrary_rot(precision, verbose=False):
    dag = DAG(f'rot_{precision}')
    q = 10 ** precision 
    p = q // 3
    dag.add_gate(Z_theta(p, q, precision=precision)(f'q_0'))
    return dag 
