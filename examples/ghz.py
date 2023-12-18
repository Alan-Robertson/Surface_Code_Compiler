from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.lib_instructions import T_Factory, Toffoli

from surface_code_routing.compiled_qcb import compile_qcb



def ghz(n_qubits, height, width):
    # Breaking it down just for routing
    dag = DAG(f'GHZ{n_qubits}')
    dag.add_gate(Hadamard('q_0')) 
    for i in range(1, n_qubits):
        dag.add_gate(CNOT('q_0', f"q_{i}" ))
    return compile_qcb(dag, height, width) 

def ghz_logn(n_qubits, height, width):
    # Breaking it down just for routing
    dag = DAG(f'GHZ{n_qubits}')
    dag.add_gate(Hadamard('q_0')) 

    n_qubits_set = 1
    while n_qubits_set < n_qubits:
        for i in range(n_qubits_set):
            if i + n_qubits_set < n_qubits:
                targ = n_qubits_set + i
                dag.add_gate(CNOT(f"q_{i}", f"q_{targ}" ))
            else:
                break
        n_qubits_set += i + 1
    return compile_qcb(dag, height, width) 


def toffoli_chain(n_ctrls, height, width):
    dag = DAG(f'Toffolis_{n_ctrls}')
    dag.add_gate(Toffoli('ctrl_0', 'ctrl_1', 'anc_0'))
    for i in range(2, n_ctrls - 1):
        dag.add_gate(Toffoli(f'ctrl_{i}', f'anc_{i - 2}', f'anc_{i - 1}')) 
    dag.add_gate(Toffoli(f'ctrl_{n_ctrls - 1}', f'anc_{n_ctrls - 2}', 'targ'))

    for i in range(n_ctrls - 2, 1, -1):
        dag.add_gate(Toffoli(f'ctrl_{i}', f'anc_{i - 2}', f'anc_{i - 1}')) 
        dag.add_gate(Toffoli('ctrl_0', 'ctrl_1', 'anc_0'))

    return compile_qcb(dag, height, width, T_Factory())
