# from dag_node import DAGNode
# from typing import Sequence 
# from dag import DAG
from functools import partial
from symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from scope import Scope

INIT_SYMBOL = Symbol('INIT')
def INIT(*symbol_constructors):
    sym = Symbol('INIT', symbol_constructors)
    
    # Breaks recursive expansion
    scope = Scope({i:i for i in sym.io})

    dag = DAG(sym, scope=scope)

    # Initialise each object independently
    # This will be unrolled when injected into the DAG
    for obj in sym.io:
        dag.add_node(Symbol("INIT", obj), n_cycles=1)
    return dag

RESET_SYMBOL = Symbol('RESET')
def RESET(*symbol_constructors):
    sym = Symbol('RESET', symbol_constructors)
    scope = Scope({i:i for i in sym.io})
    dag = DAG(sym, scope=scope)

    # Reset each object independently
    # This will be unrolled when injected into the DAG
    for obj in sym.io:
        dag.add_node(Symbol("RESET", obj), n_cycles=1)
    return dag

def CNOT(ctrl, targ):
    ctrl, targ = symbol_map(ctrl, targ)
    sym = Symbol('CNOT', 'ctrl', 'targ')

    # Scope injection passes variables from a higher scope
    scope = Scope({sym('ctrl'):ctrl, sym('targ'):targ})
    
    dag = DAG(sym, scope=scope)

    # This object is jointly initialised
    dag.add_node(sym, n_cycles=3)
    return dag

from dag2 import DAG, DAGNode


def T(targ):
    targ = symbol_resolve(targ)
    sym = Symbol('T', 'targ')

    factory = ExternSymbol('T_Factory')

    scope = Scope({factory:factory, sym('targ'):targ})

    dag = DAG(sym, scope=scope)
    dag.add_node(factory, n_cycles=17)
    dag.add_gate(CNOT(factory('factory_out'), targ))
    dag.add_gate(RESET(factory))
    return dag

def Hadamard(targ):
    targ = Symbol(targ)
    sym = Symbol('H', 'targ')
    scope = Scope({sym('targ'):targ})
    dag = DAG(sym, scope=scope)
    dag.add_node(sym, n_cycles=1)
    return dag


def Toffoli(ctrl_a, ctrl_b, targ):
    ctrl_a, ctrl_b, targ = map(Symbol, (ctrl_a, ctrl_b, targ))
    sym = Symbol('Toffoli', {'ctrl_a', 'ctrl_b', 'targ'})
    scope = Scope({sym('ctrl_a'):ctrl_a, sym('ctrl_b'):ctrl_b, sym('targ'):targ})
    dag = DAG(sym, scope=scope)

    dag.add_gate(Hadamard(targ))
    dag.add_gate(CNOT(ctrl_b, targ))
    dag.add_gate(T(targ))
    dag.add_gate(CNOT(ctrl_a, targ))

    return dag
