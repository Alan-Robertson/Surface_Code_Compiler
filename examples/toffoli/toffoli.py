import numpy as np
from functools import partial
from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.lib_instructions import T_Factory, Toffoli

from surface_code_routing.compiled_qcb import compile_qcb


def toffoli(height, width, t_factory=None):
    if t_factory is None:
        t_factory = T_Factory() 
    dag = DAG(Symbol('Toffoli', ('ctrl_a', 'ctrl_b', 'targ'))) 
    dag.add_gate(Toffoli('ctrl_a', 'ctrl_b', 'targ'))
    return compile_qcb(dag, height, width, t_factory) 


def toff_network_dag(n_qubits, height, width, *externs, n_rounds = 1, t_factory=None, teleport=False):
    if t_factory is None:
        t_factory = T_Factory() 
    dag = DAG(f'CNOTS_{n_qubits}')
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j, k in zip(gate_round[::3], gate_round[1::3], gate_round[2::3]):
            dag.add_gate(Toffoli(f'q_{i}', f"q_{j}", f"q_{k}"))

    return compile_qcb(dag, height, width, t_factory, *externs, router_kwargs={'teleport':teleport}) 

def toff_network_extern(n_qubits, height, width, toffoli_extern=None, n_rounds=1): 
    if toffoli_extern is None:
        toffoli_extern = toffoli(14, 21)
    dag = DAG(f'CNOTS_{n_qubits}')
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j, k in zip(gate_round[::3], gate_round[1::3], gate_round[2::3]):
            dag.add_gate(toffoli_extern((f'q_{i}', f"q_{j}"), (f"q_{k}",)))

    return compile_qcb(dag, height, width, toffoli_extern, router_kwargs={'teleport':False}) 
