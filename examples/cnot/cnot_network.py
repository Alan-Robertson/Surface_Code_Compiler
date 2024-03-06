import numpy as np
from functools import partial
from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.lib_instructions import T_Factory, Toffoli

from surface_code_routing.compiled_qcb import compile_qcb



def cnot_network(n_qubits, height, width, n_rounds = 1, teleport=True):
    dag = DAG(f'CNOTS_{n_qubits}')
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j in zip(gate_round[::2], gate_round[1::2]):
            dag.add_gate(CNOT(f'q_{i}', f"q_{j}" ))

    return compile_qcb(dag, height, width, router_kwargs={'teleport':teleport}) 


def toff_network(n_qubits, height, width, *externs, n_rounds = 1, teleport=True):
    dag = DAG(f'CNOTS_{n_qubits}')
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j, k in zip(gate_round[::3], gate_round[1::3], gate_round[2::3]):
            dag.add_gate(Toffoli(f'q_{i}', f"q_{j}", f"q_{k}"))

    return compile_qcb(dag, height, width, *externs, router_kwargs={'teleport':teleport}) 

def route_example(n_qubits, height, width, *externs, n_rounds = 1, teleport=True):
    dag = DAG(Symbol('a', 'b', 'c'))
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j, k in zip(gate_round[::3], gate_round[1::3], gate_round[2::3]):
            dag.add_gate(Toffoli(f'q_{i}', f"q_{j}", f"q_{k}"))

    return compile_qcb(dag, height, width, *externs, router_kwargs={'teleport':teleport}) 

