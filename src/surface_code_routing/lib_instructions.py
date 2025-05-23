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

def T_Factory(*externs, height=5, width=6, t_gate=local_Tdag, **compiler_arguments):

        if 'router_kwargs' in compiler_arguments:
            if 'teleport' not in compiler_arguments:
                compiler_arguments['teleport'] = False
        else:
            router_kwargs = {'teleport': False}
            compiler_arguments['router_kwargs'] = router_kwargs 

        dag = DAG(Symbol('T_Factory', (), 'factory_out'))
        dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(4)]))
        dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in range(11)]))
        dag.add_gate(CNOT('q_3', *['a_{i}'.format(i=i) for i in range(1, 8)]))
        dag.add_gate(CNOT('q_2', *['a_{i}'.format(i=i) for i in (0, 2, 3, 4, 5, 8, 9)]))
        dag.add_gate(CNOT('q_1', *['a_{i}'.format(i=i) for i in (0, 1, 3, 4, 6, 8, 10)]))
        dag.add_gate(CNOT('q_0', *['a_{i}'.format(i=i) for i in (0, 1, 2, 4, 7, 9, 10)]))
        dag.add_gate(CNOT('factory_out', *('a_{i}'.format(i=i) for i in range(10, 3, -1))))

        for i in range(4):
            dag.add_gate(t_gate(f'q_{i}'))
            dag.add_gate(MEAS(f'q_{i}'))

        for i in range(11):
            dag.add_gate(t_gate(f'a_{i}'))
            dag.add_gate(MEAS(f'a_{i}'))

        dag.add_gate(X('factory_out'))

        qcb_kwargs = compiler_arguments.get('compiled_qcb_kwargs', dict()) 
        qcb_kwargs['readout_operation'] = T_SLICE
        compiler_arguments['compiled_qcb_kwargs'] = qcb_kwargs

        return compile_qcb(dag, height, width, *externs, **compiler_arguments)

def T_gate(factory=None, height=5, width=7):
    if factory is not None:
        height = factory.height
        width = factory.width
    return partial(T, height=height, width=width, factory=factory)

def T(targ, height=5, width=7, factory=None):
    if factory is None:
        factory = T_Factory(height=height, width=width)
    dag = factory.instruction((), (targ,))
    return dag

def Toffoli(ctrl_a, ctrl_b, targ, T=T):
    ctrl_a, ctrl_b, targ = map(Symbol, (ctrl_a, ctrl_b, targ))
    sym = Symbol('Toffoli', {'ctrl_a', 'ctrl_b', 'targ'})
    scope = Scope({sym('ctrl_a'):ctrl_a, sym('ctrl_b'):ctrl_b, sym('targ'):targ})
    dag = DAG(sym, scope=scope)

    dag.add_gate(Hadamard(targ))
    dag.add_gate(CNOT(ctrl_b, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_a, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_b, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_a, targ))
    dag.add_gate(T(targ))
    dag.add_gate(T(ctrl_b))
    dag.add_gate(Hadamard(targ))
    dag.add_gate(CNOT(ctrl_a, ctrl_b))
    dag.add_gate(T(ctrl_a))
    dag.add_gate(T(ctrl_b))
    dag.add_gate(CNOT(ctrl_a, ctrl_b))
    return dag

def CSWAP(ctrl, targ_a, targ_b, Toffoli=Toffoli, **kwargs):
    ctrl, targ_a, targ_b = map(Symbol, (ctrl, targ_a, targ_b))
    sym = Symbol('CSWAP', {'ctrl'}, {'targ_a','targ_b'})
    scope = Scope({sym('ctrl'):ctrl, sym('targ_a'):targ_b, sym('targ_b'):targ_b})
    dag = DAG(sym, scope=scope)

    dag.add_gate(Toffoli(ctrl, targ_a, targ_b))
    dag.add_gate(Toffoli(ctrl, targ_b, targ_a))
    dag.add_gate(Toffoli(ctrl, targ_a, targ_b))
    return dag

def MAJ(a, b, c, Toffoli=Toffoli):
    dag = DAG(Symbol('MAJ', ('a', 'b', 'c')))
    dag.add_gate(CNOT('c', 'b'))
    dag.add_gate(CNOT('c', 'a'))
    dag.add_gate(Toffoli('a', 'b', 'c'))
    return dag

def UMA(a, b, c, Toffoli=Toffoli):
    dag = DAG(Symbol('MAJ', ('a', 'b', 'c')))
    dag.add_gate(X('b'))
    dag.add_gate(CNOT('a', 'b'))
    dag.add_gate(Toffoli('a', 'b', 'c'))
    dag.add_gate(X('b'))
    dag.add_gate(CNOT('c', 'a', 'b'))
