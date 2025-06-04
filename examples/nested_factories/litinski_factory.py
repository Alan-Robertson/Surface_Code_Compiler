from surface_code_routing.dag import DAG
from surface_code_routing.compiled_qcb import compile_qcb
from surface_code_routing.instructions import Z_MULTI, Phase, MEAS
from surface_code_routing.instructions import INIT, RESET, CNOT, T_SLICE, X 
from surface_code_routing.instructions import Hadamard, local_Tdag

import itertools

def T_Factory_Lit(*externs, height=5, width=6, t_gate=local_Tdag, n_injection_sites=1, **compiler_arguments):
    '''
        Figure 3
        https://arxiv.org/pdf/1905.06903
        n_injection_sites sets the number of T register sites
    '''

    if 'router_kwargs' in compiler_arguments:
        if 'teleport' not in compiler_arguments:
            compiler_arguments['teleport'] = False
    else:
        router_kwargs = {'teleport': False}
        compiler_arguments['router_kwargs'] = router_kwargs 

    dag = DAG(Symbol('T_Factory', (), 'factory_out'))

    dag.add_gate(INIT(*['t_{i}'.format(i=i) for i in range(n_injection_sites)]))
    dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(1, 5)]))

    # Rotate through injection sites
    injection_rotation = itertools.cycle(list(range(n_injection_sites)))

    for i in range(1, 5):  
        targ = 't_{j}'.format(j=next(injection_rotation))
        dag.add_gate(t_gate(targ))
        dag.add_gate(Z_MULTI(targ, f'q_{i}'))
        dag.add_gate(Phase(f'q_{i}'))

    pi8_gates = [
        [1, 2, 3], # 5
        ['factory_out', 1, 2], # 6
        ['factory_out', 1, 3], # 7
        ['factory_out', 2, 3], # 8
        ['factory_out', 3, 4], # 9
        ['factory_out', 1, 4], # 10
        ['factory_out', 2, 4], # 11 
        ['factory_out', 1, 2, 3, 4], # 12
        [2, 3, 4], # 13
        [1, 3, 4], # 14
        [1, 2, 4] # 15
    ]

    for targs in pi8_gates:
        t_targ = 't_{j}'.format(j=next(injection_rotation))
        registers = [[f'q_{i}', f'{i}'][len(str(i)) > 1] for i in targs]

        dag.add_gate(t_gate(t_targ))

        # T gate
        dag.add_gate(Z_MULTI(t_targ, *registers))

        # Phase gate
        dag.add_gate(Z_MULTI(*registers))

    for i in range(1, 5):
        targ = 'q_{i}'.format(i=i)
        dag.add_gate(MEAS(targ))

    qcb_kwargs = compiler_arguments.get('compiled_qcb_kwargs', dict()) 
    qcb_kwargs['readout_operation'] = T_SLICE
    compiler_arguments['compiled_qcb_kwargs'] = qcb_kwargs

    return compile_qcb(dag, height, width, *externs, **compiler_arguments)
