from dag_node import DAGNode
from typing import Sequence 
from dag import DAG

from symbol import Symbol

#from DAG import dag

'''
    Base Gate Behaviours
'''

class Gate(DAGNode):
    pass

class UnaryGate(Gate):
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        if len(args) > 0:
            deps = args
        super().__init__(deps=deps, **kwargs)

class ANCGate(Gate):
    '''
    Ancillary Gate
    This gate requires an integer number of routing blocks as an ancillary overhead
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CompositionalGate(DAG, Gate):
    '''
    Compositional Gate
    This gate wraps other gates
    '''
    def __init__(self, cycles,  symbol='', *args, **kwargs):
        self.symbol = symbol
        self.cycles = cycles
        DAG.__init__(self, *args, **kwargs)

class QCBGate(Gate):
    '''
        This gate wraps a QCB
        TODO IO Handling goes in here
    '''
    def __init__(self, qcb=None, *args, **kwargs):
        self.qcb = qcb
        #super().__init__(*args, cycles=qcb.cycles, **kwargs)
        super().__init__(*args,  **kwargs)

class FactoryGate(QCBGate):
    '''
    Factory
    A special case of a compositional gate with no input
    '''
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        if len(args) > 0:
            targs = args
        super().__init__(targs=targs, **kwargs)

class MagicGate(FactoryGate):
    '''
    Magic Gate
    A special case of a compositional gate with no input
    Magic gates have an associated error rate
    '''
    def __init__(self, *args, deps=None, targs=None, error_rate=0, **kwargs):
        self.error_rate = error_rate
        super().__init__(*args, targs=targs, deps=deps, **kwargs)


class VirtualGate(Gate):
    '''
    VirtualGate
    This gate exists only to create dependencies in the DAG
    '''
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        if len(args) > 0:
            targ = args
        super().__init__(*args, targs=targs, **kwargs)


class DEPENDENCY(VirtualGate):
    '''
    A no action gate that exists only to force dependency management
    '''
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        super().__init__(*args, symbol="DEPENDENCY", cycles=0, **kwargs)

'''
    Particular Choices of Gates
'''
class CNOT(Gate):
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        if len(args) > 0:
            deps = [args[0]]
            targs = [args[1]]
        super().__init__(symbol="CNOT", cycles=3, deps=deps, targs=targs, **kwargs)

class Z(UnaryGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="Z", **kwargs)

class X(UnaryGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="X", **kwargs)

class INIT(UnaryGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="INIT", **kwargs, cycles=1, layer_num=0)

'''
    Compositional Gates
'''
class PREP(Gate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="PREP", **kwargs, cycles=1)

class T(CompositionalGate):
    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            targs = args
        else:
            targs = kwargs['targs']        

        super().__init__(cycles=0, n_blocks=1)
        factory = self.add_gate(T_Factory)
        self.add_gate(CNOT, deps=factory[0], targs=targs)

class T_Factory(FactoryGate):
    # Singleton Symbol
    # This defines our IO handling
  
    symbol = Symbol('T', None, Symbol('T_factory_out'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol=self.symbol , **kwargs, cycles=17)

class Q_Factory(Gate):
    symbol = Symbol('T', None, Symbol('Q_factory_out'))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol=self.symbol, **kwargs, cycles=25)

class Toffoli(CompositionalGate):
    pass
