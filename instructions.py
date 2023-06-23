from dag_node import DAGNode

'''
    Base Gate Behaviours
'''

class Gate(DAGNode):
    pass

class UnaryGate(Gate):
    def __init__(self, *args, dep=None, targ=None, **kwargs):
        if len(args) > 0:
            dep = args
        super().__init__(*args, dep=dep, **kwargs)

class ANCGate(Gate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CompositionalGate(Gate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class MagicGate(CompositionalGate):
    def __init__(self, *args, dep=None, targ=None, **kwargs):
        if len(args) > 0:
            targ = args
        super().__init__(*args, targ=targ, **kwargs)


#class OutOfPlaceOperation(CompositionalGate):
#    def add_node(self):
#        '''
#            Overload this to add initialiser nodes
#        '''
#        init_nodes = []
#        for t in targs:
#            if not isinstance(t, DAGNode):
#                init_nodes.append(CNOT(t, ))
#

'''
    Particular Choices of Gates
'''
class CNOT(Gate):
    def __init__(self, *args, deps=None, targs=None, **kwargs):
        if len(args) > 0:
            deps = [args[0]]
            targs = [args[1]]
        super().__init__(data="CNOT", cycles=3, deps=deps, targs=targs, **kwargs)

class Z(UnaryGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="Z", **kwargs)

class X(UnaryGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="X", **kwargs)

class INIT(UnaryGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="INIT", **kwargs, cycles=1)

'''
    Compositional Gates
'''

class PREP(CompositionalGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="PREP", **kwargs, cycles=1)

class T(MagicGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="T", **kwargs, cycles=17)

class Q(MagicGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, symbol="Q", **kwargs, cycles=25)

class Toffoli(CompositionalGate):
    pass

