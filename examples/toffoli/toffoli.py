import numpy as np
from functools import partial
from surface_code_routing.dag import DAG
from surface_code_routing.scope import Scope 

from surface_code_routing.symbol import Symbol
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard, T_SLICE
from surface_code_routing.lib_instructions import T_Factory, Toffoli, T

from surface_code_routing.compiled_qcb import compile_qcb


def toffoli(height, width, t_factory=None):
    if t_factory is None:
        t_factory = T_Factory() 
    dag = DAG(Symbol('Toffoli', ('ctrl_a', 'ctrl_b', 'targ'))) 
    dag.add_gate(Toffoli('ctrl_a', 'ctrl_b', 'targ'))
    return compile_qcb(dag, height, width, t_factory) 


def toff_network_dag(n_qubits, height, width, *externs, n_rounds = 1, t_factory=None, teleport=False, Toffoli=Toffoli):
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

import random
def ToffoliBuffered(ctrl_a, ctrl_b, targ, T=T):
    buffer = '_buffer_' + ''.join(chr(random.randint(ord('a'), ord('a') + 26)) for _ in range(10))
    ctrl_a, ctrl_b, targ = map(Symbol, (ctrl_a, ctrl_b, targ))
    sym = Symbol('Toffoli', {'ctrl_a', 'ctrl_b', 'targ'})
    scope = Scope({sym('ctrl_a'):ctrl_a, sym('ctrl_b'):ctrl_b, sym('targ'):targ})

    dag = DAG(sym, scope=scope)
    dag.add_gate(INIT(buffer))
    dag.add_gate(Hadamard(targ))
    dag.add_gate(CNOT(ctrl_b, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_a, targ))
    dag.add_gate(T(buffer))  # Force buffering
    dag.add_gate(T_SLICE(buffer, targ))
    dag.add_gate(CNOT(ctrl_b, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_a, targ))
    dag.add_gate(T(targ))
    dag.add_gate(T(ctrl_b))
    dag.add_gate(Hadamard(targ))
    dag.add_gate(CNOT(ctrl_a, ctrl_b))
    dag.add_gate(T(ctrl_a))
    dag.add_gate(T(ctrl_b))
    dag.add_gate(CNOT(ctrl_a, ctrl_b))
    return dag


