# from dag_node import DAGNode
# from typing import Sequence 
# from dag import DAG
from functools import partial
from symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from scope import Scope

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
    sym = Symbol('Toffoli', {'ctrl_a', 'ctrl_b'}, 'targ')
    scope = Scope({sym('ctrl_a'):ctrl_a, sym('ctrl_b'):ctrl_b, sym('targ'):targ})
    dag = DAG(sym)

    dag.add_gate(Hadamard('targ'))
    dag.add_gate(CNOT('ctrl_b', 'targ'))
    dag.add_gate(T('targ'))
    dag.add_gate(CNOT('ctrl_a', 'targ'))

    dag = dag(scope=scope)
    return dag

def TST(ctrl_a):
    ctrl_a = Symbol(ctrl_a)
    sym = Symbol('TST', 'ctrl_a')
    scope = Scope({sym('ctrl_a'):ctrl_a, Symbol('b'):Symbol('b')})
    dag = DAG(sym)

    dag.add_gate(INIT('b'))
    dag.add_gate(CNOT('ctrl_a', 'b'))
    
    dag = dag(scope=scope)
    return dag
    # self.add_gate(CNOT, deps[1], targs[0])
    # self.add_gate(Tdag, targs[0])
    # self.add_gate(CNOT, deps[0], targs[0])
    # self.add_gate(T, targs[0])
    # self.add_gate(CNOT, deps[1], targs[0])
    # self.add_gate(Tdag, targs[0])
    # self.add_gate(CNOT, deps[0], targs[0])
    # self.add_gate(T, deps[1])
    # self.add_gate(T, targs[0])
    # self.add_gate(CNOT, deps[0], deps[1])
    # self.add_gate(Hadamard, targs[0])
    # self.add_gate(T, deps[0])
    # self.add_gate(Tdag, deps[1])
    # self.add_gate(CNOT, deps[0], deps[1])


#from DAG import dag

'''
    Base Gate Behaviours
'''

# class Gate(DAGNode):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#     def resolve_scope(self, **symbols):
#         self.scope.inject(**symbols) 

# class UnaryGate(Gate):
#     def __init__(self, *args, deps=None, targs=None, **kwargs):
#         if len(args) > 0:
#             deps = args
#         super().__init__(deps=deps, **kwargs)

# class ANCGate(Gate):
#     '''
#     Ancillary Gate
#     This gate requires an integer number of routing blocks as an ancillary overhead
#     '''
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

# class CompositionalGate(DAG):
#     '''
#     Compositional Gate
#     This gate wraps other gates
#     '''
#     def __init__(self, symbol, *args, scope=None, **kwargs):
#         self.symbol = symbol
#         self.cycles = 0

#         if scope is None: 
#             scope = {}
#         for sym in symbol.io:
#             if sym not in scope:
#                 scope[sym] = None

#         DAG.__init__(self, scope=scope, *args, **kwargs)

#         self.deps = kwargs.get('deps', tuple())
#         self.targs = kwargs.get('targs', tuple())

# class QCBGate(Gate):
#     '''
#         This gate wraps a QCB
#         TODO IO Handling goes in here
#     '''
#     def __init__(self, qcb=None, *args, **kwargs):
#         self.qcb = qcb
#         #super().__init__(*args, cycles=qcb.cycles, **kwargs)
#         super().__init__(*args,  **kwargs)

# class FactoryGate(QCBGate):
#     '''
#     Factory
#     A special case of a compositional gate with no input
#     This is an abstract class
#     '''
#     def __init__(self, *args, deps=None, targs=None, **kwargs):
#         if len(args) > 0:
#             targs = args
#         super().__init__(targs=targs, symbol = copy.deepcopy(self.symbol), **kwargs)

# class MagicGate(FactoryGate):
#     '''
#     Magic Gate
#     A special case of a compositional gate with no input
#     Magic gates have an associated error rate
#     '''
#     def __init__(self, *args, deps=None, targs=None, error_rate=0, **kwargs):
#         self.error_rate = error_rate
#         super().__init__(*args, targs=targs, deps=deps, **kwargs)

# '''
#     Particular Choices of Gates
# '''
# class CNOT(Gate):
#     def __init__(self, *args, deps=None, targs=None, **kwargs):
#         if len(args) > 0:
#             deps = [args[0]]
#             targs = [args[1]]
#         super().__init__(symbol="CNOT", cycles=3, deps=deps, targs=targs, **kwargs)

# class Z(UnaryGate):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, symbol="Z", **kwargs)

# class X(UnaryGate):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, symbol="X", **kwargs)

# class Hadamard(UnaryGate):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, symbol="H", **kwargs)




# '''
#     Compositional Gates
# '''
# class PREP(Gate):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, symbol="PREP", **kwargs, cycles=1)

# class SWAP(CompositionalGate):
#     def __init__(self, *args, **kwargs):
        
#         targs = [Symbol('a'), Symbol('b')]
#         scope = dict((zip(args), targs))
#         super().__init__(symbol=Symbol('T_Factory', set(targs)), scope=scope)
#         self.add_gate(CNOT, targs[0], targs[1])
#         self.add_gate(CNOT, targs[1], targs[0])
#         self.add_gate(CNOT, targs[0], targs[1])

# class T(CompositionalGate):
#     def __init__(self, *args, **kwargs):
#         if len(args) > 0:
#             targs = args
#         else:
#             targs = kwargs['targs']

#         super().__init__(symbol = Symbol('T_Factory', args[0]), n_blocks=1)

#         factory = self.add_gate(T_Factory)
#         self.add_gate(CNOT, deps=factory(Symbol('T_out')), targs=targs)


# class T_Factory(FactoryGate):
#     # Singleton Symbol
#     # This templates our IO handling
#     symbol = Symbol('T', None, Symbol('T_out'))

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

# class Q_Factory(Gate):
#     symbol = Symbol('T', None, Symbol('Q_factory_out'))
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, symbol=self.symbol, **kwargs)

# class Toffoli(CompositionalGate):
#     def __init__(self, *args, **kwargs):
#         if len(args) > 0:
#             deps = args[0:2]
#             targs = args[2:3]
#         else:
#             deps = kwargs['deps']
#             targs = kwargs['targs']

#         super().__init__(cycles=0, n_blocks=3)

#         self.add_gate(Hadamard, targs[0])
#         self.add_gate(CNOT, deps[1], targs[0])
#         self.add_gate(Tdag, targs[0])
#         self.add_gate(CNOT, deps[0], targs[0])
#         self.add_gate(T, targs[0])
#         self.add_gate(CNOT, deps[1], targs[0])
#         self.add_gate(Tdag, targs[0])
#         self.add_gate(CNOT, deps[0], targs[0])
#         self.add_gate(T, deps[1])
#         self.add_gate(T, targs[0])
#         self.add_gate(CNOT, deps[0], deps[1])
#         self.add_gate(Hadamard, targs[0])
#         self.add_gate(T, deps[0])
#         self.add_gate(Tdag, deps[1])
#         self.add_gate(CNOT, deps[0], deps[1])
