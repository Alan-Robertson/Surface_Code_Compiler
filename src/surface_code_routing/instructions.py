from functools import partial
from surface_code_routing.symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from surface_code_routing.scope import Scope

def in_place_factory(fn, n_cycles=1, n_ancillae=0):
    '''
    Factory method for generating in place gates
    '''
    def instruction(targ):
        targ = Symbol(targ)
        sym = Symbol(fn, 'targ')
        scope = Scope({sym('targ'):targ})
        dag = DAG(sym, scope=scope)
        dag.add_node(sym, n_cycles=n_cycles, n_ancillae=n_ancillae)
        return dag
    return instruction

def in_place_factory_mult(fn, n_cycles=1, n_ancillae=0, singular_instruction=None):
    '''
    Factory method for generating in place gates
    '''
    if singular_instruction is None:
        singular_instruction =  in_place_factory(fn, n_cycles=n_cycles, n_ancillae=n_ancillae)
    
    def instruction(*args):
        args = tuple(map(symbol_resolve, args))
        sym = Symbol(fn, args)

        # Scope injection passes variables from a higher scope
        scope = Scope({sym(arg):arg for arg in args})
        
        dag = DAG(sym, scope=scope)
        
        for arg in args:
            dag.add_gate(singular_instruction(arg))
        
        return dag
    return instruction


def factory_factory(fn, n_cycles=1):
    def instruction(targ):
        targ = symbol_resolve(targ)
        sym = Symbol(fn, 'targ')

        factory = ExternSymbol(fn)
        scope = Scope({factory:factory, sym('targ'):targ})

        dag = DAG(sym, scope=scope)
        dag.add_node(factory, n_cycles=n_cycles)
        dag.add_gate(CNOT(factory('factory_out'), targ))
        dag.add_gate(RESET(factory))
        return dag






def non_local_factory(fn, n_cycles=1, n_ancillae=0):
    '''
    Factory method for generating non-local gates
    '''
    def instruction(*args):
        args = tuple(map(symbol_resolve, args))
        sym = Symbol(fn, args)

        # Scope injection passes variables from a higher scope
        scope = Scope({sym(arg):arg for arg in args})
        
        dag = DAG(sym, scope=scope)

        # This object is jointly initialised
        dag.add_node(sym, n_cycles=n_cycles)
        return dag
    return instruction


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



from surface_code_routing.dag import DAG, DAGNode

PREP = in_place_factory_mult('PREP')
Hadamard = in_place_factory('H', n_ancillae=1)
Phase = in_place_factory('P')
X = in_place_factory('X')
Y = in_place_factory('Y')
Z = in_place_factory('Z')

CNOT = non_local_factory('CNOT', n_cycles=3)
MEAS = non_local_factory('MEAS', n_cycles=1)