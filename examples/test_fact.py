from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.scope import Scope 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard, Phase
from surface_code_routing.lib_instructions import T_Factory, T


from surface_code_routing.compiled_qcb import compile_qcb


def basic_gates(n_qubits, width, height, precision=10, verbose=False):
    ctrl_a, ctrl_b, targ = map(Symbol, ('ctrl_a', 'ctrl_b', 'targ'))
    sym = Symbol('Toffoli', {'ctrl_a', 'ctrl_b', 'targ'})
    scope = Scope({sym('ctrl_a'):ctrl_a, sym('ctrl_b'):ctrl_b, sym('targ'):targ})
    dag = DAG(sym, scope=scope)

    dag.add_gate(Hadamard(targ))
    dag.add_gate(CNOT(ctrl_b, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_a, ctrl_b))
    dag.add_gate(Phase(targ))
    return compile_qcb(dag, width, height, T_Factory(), verbose=verbose) 

if __name__ == '__main__':
    basic_gates(10, 10, 10)
