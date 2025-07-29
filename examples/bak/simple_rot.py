from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import Z_theta
from surface_code_routing.lib_instructions import T_Factory, T, Toffoli
from surface_code_routing.symbol import Symbol
from surface_code_routing.compiled_qcb import compile_qcb


def arbitrary_rot(p, q, width, height, precision=10, verbose=False):
    dag = DAG(f'rot_{width}_{height}')
    dag.add_gate(Z_theta(p, q, precision=precision)(f'q_0'))
    return compile_qcb(dag, width, height, T_Factory(), verbose=verbose) 


def toffoli(width, height, factory=T_Factory, verbose=False):
    dag = DAG(Symbol(f'toffoli_{width}_{height}', ('a', 'b', 'c'), ('a', 'b', 'c')))
    dag.add_gate(Toffoli('a', 'b', 'c'))
    return compile_qcb(dag, width, height, factory(), verbose=verbose) 

def MAJ(width, height, factory=toffoli):
    toffoli_gate = factory.instruction

    dag = DAG(Symbol(f'MAJ_{width}_{height}', ('c', 'b', 'a'), ('c', 'b', 'a')))
    dag.add_gate(CNOT('a', 'b', 'c'))
    dag.add_gate(toffoli_gate(('c', 'b', 'a'), ('c', 'b', 'a')))
    return compile_qcb(dag, width, height, factory) 

def MAJ(width, height, factory=toffoli):
    toffoli_gate = factory.instruction
    dag = DAG(Symbol(f'MAJ_{width}_{height}', ('c', 'b', 'a'), ('c', 'b', 'a')))
    dag.add_gate(CNOT('a', 'b', 'c'))
    dag.add_gate(toffoli_gate(('c', 'b', 'a'), ('c', 'b', 'a')))
    return compile_qcb(dag, width, height, factory) 
   

def CARRY_CALC(n_qubits, width, height, factory):
    maj_gate = factory.instruction
    dag = DAG(Symbol(f'carry_bit_{width}_{height}'))
    dag.add_gate(INIT('ancillae'))
    dag.add_gate(INIT('carry'))

    dag.add_gate(maj_gate(('ancillae', 'b_0', 'a_0'), ('ancillae', 'b_0', 'a_0')))
    for i in range(1, n_qubits):
        dag.add_gate(maj_gate((f'a_{i - 1}', f'b_{i}', f'a_{i}'), (f'a_{i - 1}', f'b_{i}', f'a_{i}')))
    dag.add_gate(CNOT(f'a_{n_qubits - 1}', 'carry'))

    return compile_qcb(dag, width, height, factory) 


def T_Factory_local(height=5, width=7):
        dag = DAG(Symbol('T_Factory'))
        dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(4)]))
        dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in range(11)]))
        dag.add_gate(CNOT('q_3', *['a_{i}'.format(i=i) for i in range(1, 8)]))
        dag.add_gate(CNOT('q_2', *['a_{i}'.format(i=i) for i in (0, 2, 3, 4, 5, 8, 9)]))
        dag.add_gate(CNOT('q_1', *['a_{i}'.format(i=i) for i in (0, 1, 3, 4, 6, 8, 10)]))
        dag.add_gate(CNOT('q_0', *['a_{i}'.format(i=i) for i in (0, 1, 2, 4, 7, 9, 10)]))
        dag.add_gate(CNOT('factory_out', *('a_{i}'.format(i=i) for i in range(10, 3, -1))))
        dag.add_gate(MEAS(
            *['q_{i}'.format(i=i) for i in range(4)], 
            *['a_{i}'.format(i=i) for i in range(11)],
            'factory_out'))
        dag.add_gate(X('factory_out'))

        return compile_qcb(dag, height, width)
