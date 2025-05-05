from functools import partial
from itertools import chain
from surface_code_routing.symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from surface_code_routing.scope import Scope
from surface_code_routing.constants import SINGLE_ANCILLAE, ELBOW_ANCILLAE

def in_place_factory(fn, **kwargs):
    '''
    Factory method for generating in place gates
    '''
    def instruction(targ):
        targ = symbol_resolve(targ)
        sym = Symbol(fn, 'targ')
        scope = Scope({sym('targ'):targ})
        dag = DAG(sym, scope=scope)
        dag.add_node(sym, **kwargs)
        return dag
    return instruction

def pure_ancillae_instruction_factory(fn, **kwargs):
    '''
        Instructions that target only ancillae and have no impact on the named registers
    '''
    def instruction():
        sym = Symbol(fn)
        scope = Scope({})
        dag = DAG(sym, scope=scope)
        dag.add_node(sym, **kwargs)
        return dag
    return instruction


def in_place_factory_mult(fn, singular_instruction=None, **kwargs):
    '''
    Factory method for generating in place gates
    '''
    if singular_instruction is None:
        singular_instruction = in_place_factory(fn, **kwargs)
    
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

def factory_factory(fn, **kwargs):
    def instruction(targ):
        targ = symbol_resolve(targ)
        sym = Symbol(fn, 'targ')

        factory = ExternSymbol(fn)
        scope = Scope({factory:factory, sym('targ'):targ})

        dag = DAG(sym, scope=scope)
        dag.add_node(factory, **kwargs)
        dag.add_gate(CNOT(factory('factory_out'), targ))
        dag.add_gate(RESET(factory))
        return dag

def non_local_factory(fn, n_cycles=1, n_ancillae=0, max_args=None):
    '''
    Factory method for generating non-local gates
    '''
    def instruction(*args):
        if (max_args is not None) and (len(args) > max_args):
            raise Exception(f"Too many arguments: {fn} ({args})")
        args = tuple(map(symbol_resolve, args))
        sym = Symbol(fn, args)

        # Scope injection passes variables from a higher scope
        scope = Scope({sym(arg):arg for arg in args})
        
        dag = DAG(sym, scope=scope)

        # This object is jointly initialised
        dag.add_node(sym, n_cycles=n_cycles)
        return dag
    return instruction

def ZX_factory(fn, **kwargs):
    def instruction(z_args, x_args):
        args = tuple(map(symbol_resolve, chain(z_args, x_args)))
        sym = Symbol(fn, z_args, x_args)
        
        scope = Scope({sym(arg):arg for arg in args})

        dag = DAG(sym, scope=scope)
        dag.add_node(sym, **kwargs)
        # This object is jointly initialised
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

def XYZ_PI_4(X, Y, Z):
    X, Y, Z = tuple(map(lambda arg: tuple(map(symbol_resolve, x)), (X, Y, Z)))
    args = tuple(chain(X, Y, Z))
    sym = Symbol(fn, args)

    scope = Scope({sym(arg):arg for arg in args})
    
    dag = DAG(sym, scope=scope)
    
    # Joint on all Ys in Z basis
    dag.add_gate(JOINT_MEASURE(Y))

    # Flip X and Zs
    for arg in chain(X, Y):
        dag.add_gate(Hadamard(arg))

    # Joint on all Zs and Xs
    dag.add_gate(JOINT_MEASURE(args))

    # Flip all Xs and Zs back
    for arg in chain(X, Y):
        dag.add_gate(Hadamard(arg))

    # Joint on all Ys in Z basiss
    dag.add_gate(JOINT_MEASURE(Y))

    for arg in chain(X, Y):
        dag.add_gateHadamard(arg)

    # This object is jointly initialised
    dag.add_gate(JOINT_MEASURE(*args))
    dag.add_gate(Hadamard(args[0]))
    return dag


CNOT_BASE = ZX_factory('CNOT', n_cycles=2)
def CNOT(ctrl, *targs):
   return CNOT_BASE((ctrl,), targs) 

CZ_BASE = ZX_factory('CZ', n_cycles=2)
def CZ(*targs):
   return CZ_BASE(targs, tuple()) 

X_MULTI_BASE = ZX_factory('X*', n_cycles=2)
def X_MULTI(*targs):
    return X_MULTI_BASE(tuple(), targs)

Z_MULTI_BASE = ZX_factory('Z*', n_cycles=2)
def Z_MULTI(*targs):
    return Z_MULTI_BASE(targs, tuple())

# Two cycle operation proxy
S_SLICE_BASE = ZX_factory('SROT', n_cycles=2)
def S_SLICE(ctrl, *targs):
   return S_SLICE_BASE((ctrl,), targs) 

# Three cycle operation proxy
# Example is a T gate using a magic state resource
# Measure ZZ (1)
# Conditional S (2, 3)
T_SLICE_BASE = ZX_factory('TROT', n_cycles=3)
def T_SLICE(ctrl, *targs):
   return T_SLICE_BASE((ctrl,), targs) 


MEAS = non_local_factory('MEAS', n_cycles=1)
PREP = in_place_factory_mult('PREP')

# Idling gate
Identity = in_place_factory('I', n_cycles=1)

IDLE_SYMBOL = Symbol('_IDLE')
IDLE = in_place_factory('_IDLE', n_cycles=1)

HADAMARD_SYMBOL = Symbol('H')
Hadamard = in_place_factory('H', n_cycles=1, rotation=True)

# Elbow style Hadamard
#Hadamard = in_place_factory('H', n_cycles=3, n_ancillae=1, ancillae_type=ELBOW_ANCILLAE)

ROTATION_SYMBOL = Symbol('Rotation')
Rotation = in_place_factory('Rotation', n_cycles=3, n_ancillae=1, ancillae_type=SINGLE_ANCILLAE, rotation=True)

# Rotation for elements of the extern IO. It is assumed that the internal routes are uses for the appropriate ancillae
EXTERN_IO_ROTATION = in_place_factory('Rotation', n_cycles=3, rotation=True)

MOVE_SYMBOL = Symbol('MOVE')
MOVE = non_local_factory("MOVE", n_cycles=1, max_args=2) 

Phase = in_place_factory('P', n_ancillae=1, ancillae_type=SINGLE_ANCILLAE, n_cycles=2)
X = in_place_factory('X')
Z = in_place_factory('Z')
local_Tdag = in_place_factory('T_dag', n_cycles = 1) 

JOINT_MEASURE = non_local_factory('MEAS ANC', n_cycles=1, max_args=2)

def SWAP(targ_a, targ_b):
    targ_a, targ_b = map(Symbol, (targ_a, targ_b))
    sym = Symbol('CSWAP', {'targ_a','targ_b'})
    scope = Scope({sym('targ_a'):targ_b, sym('targ_b'):targ_b})
    dag = DAG(sym, scope=scope)

    dag.add_gate(CNOT(targ_a, targ_b))
    dag.add_gate(CNOT(targ_b, targ_a))
    dag.add_gate(CNOT(targ_a, targ_b))
    return dag


from surface_code_routing.dag import DAG, DAGNode
