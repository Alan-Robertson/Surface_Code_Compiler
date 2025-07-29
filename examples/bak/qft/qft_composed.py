from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import CPHASE_theta
from surface_code_routing.lib_instructions import T_Factory
from surface_code_routing.symbol import Symbol

from surface_code_routing.compiled_qcb import compile_qcb

t_factory = T_Factory()

n_qubits = 6 
precision = n_qubits

cphase_cache = {i:CPHASE_theta(2, 2 ** i, precision) for i in range(1, n_qubits + 1)} 

height = 10
width = 10


def cphase_pow_widget(exp, height, width, factory=t_factory): 
    dag = DAG(Symbol(f'cphase_{exp}', ('ctrl', 'targ'), ('ctrl', 'targ')))
    dag.add_gate(cphase_cache[exp]('ctrl', 'targ')) 
    return compile_qcb(dag, width, height, t_factory)


cphase_widget_cache = {}
for i in range(1, n_qubits + 1):
    print("\rBuilding Cache:",  i)
    cphase_widget_cache[i] = cphase_pow_widget(i, height=height, width=width) 

def qft(n_qubits):
    global height
    global width 

    dag_height = height + 2 
    dag_width = width * (n_qubits + 1)

    dag = DAG(f'qft')

    for i in range(n_qubits):
        dag.add_gate(Hadamard(f'q_{i}')) 
        for j in range(i + 1, n_qubits):
            dag.add_gate(cphase_widget_cache[j + 1 - i](f'q_{j}', f'q_{i}'))

    return compile_qcb(dag, dag_height, dag_width, *[cphase_widget_cache[i] for i in range(1, n_qubits + 1)], mapper_kwargs={'extern_allocation_method': 'sized'}) 
