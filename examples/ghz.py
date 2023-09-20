from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard

from surface_code_routing.compiled_qcb import compile_qcb


def ghz(n_qubits, height, width):
    # This one is actually quite trivial
    dag = DAG(f'GHZ{n_qubits}')
    dag.add_gate(Hadamard('q_0')) 
    dag.add_gate(CNOT('q_0', *['q_{i}'.format(i=i) for i in range(1, n_qubits)]))
    return compile_qcb(dag, height, width) 


def ghz_linear(n_qubits, height, width):
    # Breaking it down just for routing
    dag = DAG(f'GHZ{n_qubits}')
    dag.add_gate(Hadamard('q_0')) 
    for i in range(1, n_qubits):
        dag.add_gate(CNOT('q_0', f"q_{i}" ))
    return compile_qcb(dag, height, width) 
