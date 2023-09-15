from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard

from surface_code_routing.compiled_qcb import compile_qcb


def qft_no_factories(n_qubits, width, height):
    dag = DAG(f'qft_{n_qubits}_height')
    for i in range(n_qubits):
        dag.add_gate(Hadamard(f'q_{i}')) 
        for j in range(i + 1, n_qubits):
            dag.add_gate(CNOT(f'q_{j}', f'q_{i}'))
    return compile_qcb(dag, width, height) 


def qft_assume_T_factories(n_qubits, width, height):
    dag = DAG(f'qft_{n_qubits}_height')
    for i in range(n_qubits):
        dag.add_gate(Hadamard(f'q_{i}')) 
        for j in range(i + 1, n_qubits):
            # Some dodgy assumptions about what these factories are doing
            T(f'q_{i}')
            dag.add_gate(CNOT(f'q_{j}', f'q_{i}'))
            T(f'q_{i}')
    return compile_qcb(dag, width, height + 10, T_Factory()) 


