from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import CPHASE_theta
from surface_code_routing.lib_instructions import T_Factory

from surface_code_routing.compiled_qcb import compile_qcb


def qft(n_qubits, height, width, precision=10, gates=None, t_factory=None, **compiler_args):
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()
    dag = DAG(f'qft_{n_qubits}_{height}')
    instruction_cache = {i:CPHASE_theta(2, 2 ** i, precision=precision, **gates) for i in range(2, n_qubits + 1)} 
    for i in range(n_qubits):
        dag.add_gate(Hadamard(f'q_{i}')) 
        for j in range(i + 1, n_qubits):
            dag.add_gate(instruction_cache[j + 1](f'q_{j}', f'q_{i}'))
    return compile_qcb(dag, height, width, t_factory, **compiler_args) 

print("QCB Size, Register Size, Cycles, Volume")
for qcb_size in [10, 12, 16, 24, 32]:
    for i in range(3, 11):
        #try:
        qcb = qft(i, qcb_size, qcb_size, precision=10, t_factory=T_Factory())
        print(qcb_size, i, qcb.n_cycles(), qcb.space_time_volume())
        print(qcb_size, i, qcb.n_cycles(), qcb.space_time_volume(), file=open('qft_out', 'a'))

        #except:
        #    pass
