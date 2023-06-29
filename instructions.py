from dag_node import DAGNode
from typing import Sequence

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

class CompositionalGate(Gate):
    '''
    Compositional Gate
    This gate wraps other gates
    '''
    def __init__(self, gate_group: tuple[type, tuple, dict], *args, **kwargs):
        self.gate_group = gate_group
        super().__init__(*args, **kwargs)

    def __getitem__(self, index):
        return self.gate_group[index]


class Factory(Gate):
    '''
    Factory
    A special case of a compositional gate with no input
    '''
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        if len(args) > 0:
            targs = args
        super().__init__(targs=targs, **kwargs)

class MagicGate(Factory):
    '''
    Magic Gate
    A special case of a compositional gate with no input
    Magic gates have an associated error rate
    '''
    def __init__(self, *args, deps=None, targs=None, error_rate=0, **kwargs):
        self.error_rate = error_rate
        super().__init__(*args, targs=targs, deps=deps **kwargs)


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

class PREP(CompositionalGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="PREP", **kwargs, cycles=1)

class T(CompositionalGate):
    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            targs = args
        else:
            targs = kwargs['targs']
        gate_group = ((T_Factory), (CNOT, targs[0]))
        super().__init__(gate_group, symbol="", cycles=0)

class T_Factory(MagicGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="T", **kwargs, cycles=17)

class Q(MagicGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="Q", **kwargs, cycles=25)

class Toffoli(CompositionalGate):
    pass

