from surface_code_routing.dag import DAG
from surface_code_routing.instructions import CNOT, INIT

from surface_code_routing.compiled_qcb import compile_qcb

import numpy as np

def random_cnot(n_registers, n_gates=None, n_targs=1, seed=None, **compiler_arguments):
    if seed is not None:
        np.random.seed(seed)
    dag = DAG(f'RANDOM CNOT: {n_registers}')
   
    if n_gates is None:
        n_gates = 2 * n_registers
    gate = INIT(*['q_{i}'.format(i=i) for i in range(n_registers)])
    dag.add_gate(gate)

    for i in range(n_gates):
        args = np.random.choice(range(n_registers), n_targs + 1, replace=False)
        ctrl = args[0]
        targs = args[1:]
        gate = CNOT(f'q_{ctrl}', *['q_{i}'.format(i=i) for i in targs])
        dag.add_gate(gate)

    return dag 
    

if __name__ == '__main__':
    # Single CNOT gates
    for i in range(10, 100, 2):
        qcb = compile_qcb(random_cnot(50, n_gates=100), 5, i + 10)
        print(qcb.n_cycles())

