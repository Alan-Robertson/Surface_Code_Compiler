from functools import partial
from symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from scope import Scope
from dag import DAG, DAGNode

from instructions import INIT, RESET, CNOT, Hadamard, T, Toffoli, Phase, in_place_factory, non_local_factory 

local_Tdag = in_place_factory('T_dag') 

def T_Factory():
    dag = DAG(Symbol('T_Factory', 'factory_out'))
    dag.add_gate(INIT('q_{i}'.format(i=i) for i in range(4)))
    dag.add_gate(INIT('a_{i}'.format(i=i) for i in range(11)))
    dag.add_gate(PREP('factory_out'))
    dag.add_gate(CNOT('q_3', *('a_{i}'.format(i=i) for i in range(1, 8))))
    dag.add_gate(CNOT('q_2', *('a_{i}'.format(i=i) for i in (0, 2, 3, 4, 5, 8, 9)))
    dag.add_gate(CNOT('q_1', *('a_{i}'.format(i=i) for i in (0, 1, 3, 4, 6, 8, 10))))
    dag.add_gate(CNOT('q_0', *('a_{i}'.format(i=i) for i in (0, 1, 2, 4, 7, 9, 10))))
    dag.add_gate(CNOT('factory_out', *('a_{i}'.format(i=i) for i in range(10, 3, -1))))




def MAJ():
    dag = DAG(Symbol('MAJ', ('a', 'b', 'c')))
    dag.add_gate(CNOT('c', 'b'))
    dag.add_gate(CNOT('c', 'a'))
    dag.add_gate(Toffoli('a', 'b', 'c'))

    
    
    
