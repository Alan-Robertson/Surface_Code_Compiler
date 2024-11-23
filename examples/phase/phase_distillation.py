from functools import partial, cache
from surface_code_routing.symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from surface_code_routing.scope import Scope
from surface_code_routing.dag import DAG, DAGNode

from surface_code_routing.qcb import QCB
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.allocator import Allocator
from surface_code_routing.compiled_qcb import CompiledQCB, compile_qcb

from surface_code_routing.instructions import INIT, RESET, CNOT, T_SLICE, Hadamard, Phase, local_Tdag, PREP, MEAS, X

def P_Factory(*externs, height=5, width=7, t_gate=local_Tdag, **compiler_arguments):
        dag = DAG(Symbol('P_Factory', (), 'factory_out'))
        dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(4)]))
        dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in range(3)]))
        dag.add_gate(CNOT('factory_out', *('q_{i}'.format(i=i) for i in range(0, 4))))
        dag.add_gate(CNOT('a_0', *['a_{i}'.format(i=i) for i in (0, 1, 2)]))
        dag.add_gate(CNOT('a_1', *['a_{i}'.format(i=i) for i in (1, 2, 3)]))
        dag.add_gate(CNOT('a_2', *['a_{i}'.format(i=i) for i in (0, 2, 3)]))

        for i in range(4):
            dag.add_gate(t_gate(f'q_{i}'))
            dag.add_gate(MEAS(f'q_{i}'))

        for i in range(3):
            dag.add_gate(t_gate(f'a_{i}'))
            dag.add_gate(MEAS(f'a_{i}'))

        qcb_kwargs = compiler_arguments.get('compiled_qcb_kwargs', dict()) 
        qcb_kwargs['readout_operation'] = T_SLICE
        compiler_arguments['compiled_qcb_kwargs'] = qcb_kwargs

        return compile_qcb(dag, height, width, *externs, **compiler_arguments)


def P_gate(height=5, width=7, factory=None):
    return partial(T, height=height, width=width, factory=factory)

def P(targ, height=5, width=7, factory=None):
    if factory is None:
        factory = T_Factory(height=height, width=width)
    dag = factory.instruction((), (targ,))
    return dag

