from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import CPHASE_theta
from surface_code_routing.lib_instructions import T_Factory

from surface_code_routing.compiled_qcb import compile_qcb


def qft(n_qubits, width, height, precision=10):
    dag = DAG(f'qft_{n_qubits}_{height}')
    instruction_cache = {i:CPHASE_theta(2, 2 ** i, precision=precision) for i in range(2, n_qubits + 1)} 
    for i in range(n_qubits):
        dag.add_gate(Hadamard(f'q_{i}')) 
        for j in range(i + 1, n_qubits):
            dag.add_gate(instruction_cache[j + 1](f'q_{j}', f'q_{i}'))
    return compile_qcb(dag, width, height, T_Factory()) 

