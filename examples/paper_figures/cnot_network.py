import numpy as np
from functools import partial
from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard, X_MULTI, local_Tdag
from surface_code_routing.lib_instructions import T_Factory, Toffoli, T_gate

from surface_code_routing.compiled_qcb import compile_qcb
from surface_code_routing.scope import Scope 

def cnot_network(n_qubits, height, width, n_rounds = 1, teleport=True):
    dag = DAG(f'CNOTS_{n_qubits}')
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j in zip(gate_round[::2], gate_round[1::2]):
            dag.add_gate(CNOT(f'q_{i}', f"q_{j}" ))

    return compile_qcb(dag, height, width, router_kwargs={'teleport':teleport}) 


def toffoli(height, width, t_factory=None):
    '''
        Toffoli Extern
    '''
    if t_factory is None:
        t_factory = T_Factory()
    t_gate = T_gate(factory=t_factory) 
    dag = DAG(Symbol('Toffoli', ('ctrl_a', 'ctrl_b', 'targ'), ('ctrl_a', 'ctrl_b', 'targ'))) 
    dag.add_gate(Toffoli('ctrl_a', 'ctrl_b', 'targ', T=t_gate))
    return compile_qcb(dag, height, width, t_factory)


def toffoli_from_ccz(ctrl_a, ctrl_b, targ, ccz_factory=None, init=False):
    '''
        Toffoli Dag wrapper 
    '''

    if ccz_factory is None:
        raise Exception("Missing ccz_factory")

    sym = Symbol('Toffoli', {'ctrl_a', 'ctrl_b', 'targ'})
    scope = Scope({sym('ctrl_a'):ctrl_a, sym('ctrl_b'):ctrl_b, sym('targ'):targ})

    dag = DAG(sym, scope=scope) 

    dag.add_gate(Hadamard(targ))
    dag.add_gate(ccz_factory(tuple(), (ctrl_a, ctrl_b, targ)))
    dag.add_gate(Hadamard(targ))
    return dag 

def CCZ_factory(height, width, t_factory=None, t_gate=local_Tdag,  **compiler_arguments):
    '''
        Defines a CCZ factory
    '''
    if t_factory is not None:
        #t_factory = T_Factory()
        t_gate = T_gate(factory=t_factory)

    if 'router_kwargs' in compiler_arguments:
        if 'teleport' not in compiler_arguments:
            compiler_arguments['teleport'] = False
    else:
        router_kwargs = {'teleport': False}
        compiler_arguments['router_kwargs'] = router_kwargs 

    # Using nonclemature from figure 8 of arxiv:1812.01238  
    ancillae = 'abcdefgh'
     
    dag = DAG(Symbol('CCZ_Factory', (), ('ctrl_0', 'ctrl_1', 'targ')))
    dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in ancillae]))

    dag.add_gate(X_MULTI('ctrl_0', *['a_{i}'.format(i=i) for i in 'abcd']))
    dag.add_gate(X_MULTI(*['a_{i}'.format(i=i) for i in ancillae]))
    dag.add_gate(X_MULTI('targ', *['a_{i}'.format(i=i) for i in 'aceg']))
    dag.add_gate(X_MULTI('ctrl_1', *['a_{i}'.format(i=i) for i in 'abef']))

    for i in ancillae:
        dag.add_gate(t_gate(f'a_{i}'))
        dag.add_gate(Hadamard(f'a_{i}'))
        dag.add_gate(MEAS(f'a_{i}'))

    # These could be tracked
    dag.add_gate(X(f'ctrl_0'))
    dag.add_gate(X(f'ctrl_1'))
    dag.add_gate(X(f'targ'))

    if t_factory is not None:
        return compile_qcb(dag, height, width, t_factory, **compiler_arguments)

    # Raw injection sites
    return compile_qcb(dag, height, width, **compiler_arguments)

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


def toff_extern(toffoli_extern):
    def _wrap(ctrl_a, ctrl_b, targ): 
        return toffoli_extern((ctrl_a, ctrl_b, targ), (ctrl_a, ctrl_b, targ))
    return _wrap

def toff_network(n_qubits, height, width, *externs, n_rounds = 1, teleport=True, toffoli=Toffoli):
    dag = DAG(f'Toff_{n_qubits}')
    qubit_ordering = list(range(n_qubits))

    # Pre-calc ordering to ensure seeding works correctly
    gate_orderings = [np.random.permutation(qubit_ordering) for _ in range(n_rounds)]

    for i in range(n_qubits):
        dag.add_gate(INIT(f'q_{i}'))

    for gate_round in gate_orderings:
        for i, j, k in zip(gate_round[::3], gate_round[1::3], gate_round[2::3]):
            dag.add_gate(toffoli(f'q_{i}', f"q_{j}", f"q_{k}"))

    return compile_qcb(dag, height, width, *externs, router_kwargs={'teleport':teleport}) 


def multi_toffoli(n_ctrls, height, width, *externs, init=True, toffoli=Toffoli, **kwargs):

    dag = DAG(f'MCToff_{n_ctrls}')

    if init:
        # Initialise gates
        for i in range(n_ctrls):
            dag.add_gate(INIT(f'ctrl_{i}'), )

        for i in range(1, n_ctrls - 1):
            dag.add_gate(INIT(f'anc_{i}'), )

        dag.add_gate(INIT(f'targ'), )

    
    # First Toffoli
    dag.add_gate(toffoli('ctrl_0', 'ctrl_1', 'anc_1'))

    
    for i in range(2, n_ctrls - 1):
        dag.add_gate(toffoli(f'anc_{i - 1}', f'ctrl_{i}', f'anc_{i}'))

    dag.add_gate(toffoli(f'anc_{n_ctrls - 2}', f'ctrl_{n_ctrls - 1}', 'targ'))

    for i in range(n_ctrls - 2,  1, -1):
        dag.add_gate(toffoli(f'anc_{i - 1}', f'ctrl_{i}', f'anc_{i}'))

    dag.add_gate(toffoli('anc_1', 'ctrl_0', 'ctrl_1'))

    return dag #compile_qcb(dag, height, width, *externs, **kwargs) 
