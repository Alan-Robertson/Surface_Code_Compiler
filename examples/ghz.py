from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard

from surface_code_routing.compiled_qcb import compile_qcb


def ghz(n_qubits):
    # This one is actually quite trivial
    dag = DAG(f'GHZ{n_qubits}')
    dag.add_gate(Hadamard('q_0')) 
    dag.add_gate(CNOT('q_0', *['q_{i}'.format(i=i) for i in range(1, n_qubits)]))
    return compile_qcb(dag, n_qubits, 2) 
