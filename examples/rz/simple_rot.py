from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import Z_theta
from surface_code_routing.lib_instructions import T_Factory, T, Toffoli
from surface_code_routing.symbol import Symbol
from surface_code_routing.compiled_qcb import compile_qcb

import sys


def arbitrary_rot(p, q, width, height, precision=10, verbose=False):
    dag = DAG(f'rot_{width}_{height}')
    dag.add_gate(Z_theta(p, q, precision=precision)(f'q_0'))
    return compile_qcb(dag, width, height, T_Factory(), verbose=verbose) 

prec = 256
if len(sys.argv) > 1:
    prec = int(sys.argv[1]) 

print("QCB Size, Register Size, Cycles, Volume")

for qcb_size in [8, 16, 32]:
    for i in range(1, prec):
        try:
            qcb = arbitrary_rot(i, prec, qcb_size, qcb_size)
            print(qcb_size, i, qcb.n_cycles(), qcb.space_time_volume())
            print(qcb_size, i, qcb.n_cycles(), qcb.space_time_volume(), file=open('simple_rot_out', 'w+'))
        except:
            pass
