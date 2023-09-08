from functools import partial, cache
from symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from scope import Scope
from dag import DAG, DAGNode

from qcb import QCB
from mapper import QCBMapper
from qcb_graph import QCBGraph
from qcb_tree import QCBTree
from router import QCBRouter
from allocator import Allocator
from compiled_qcb import CompiledQCB

from instructions import INIT, RESET, CNOT, Hadamard, Phase, in_place_factory, non_local_factory, PREP, MEAS, X

local_Tdag = in_place_factory('T_dag') 

@cache
def T_Factory(height=5, width=6):
        dag = DAG(Symbol('T_Factory', (), 'factory_out'))
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

        qcb = QCB(height, width, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb, dag, mapper)

        compiled_t_factory = CompiledQCB(qcb, router, dag) 

        return CompiledQCB(qcb, router, dag) 

def T(targ, height=5, width=9):
    factory = T_Factory(height=height, width=width)
    dag = factory.instruction((), (targ,))
    return dag

@cache
def MAJ():
    dag = DAG(Symbol('MAJ', ('a', 'b', 'c')))
    dag.add_gate(CNOT('c', 'b'))
    dag.add_gate(CNOT('c', 'a'))
    dag.add_gate(Toffoli('a', 'b', 'c'))


def Toffoli(ctrl_a, ctrl_b, targ):
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

