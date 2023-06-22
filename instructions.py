from dag_node import DAGNode

'''
    Base Gate Behaviours
'''
class UnaryGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class BinaryGate(DAGNode):
    def 

class ANCGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CompositionalGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class OutOfPlaceOperation(CompositionalGate):
    def add_node(self):
        '''
            Overload this to add initialiser nodes
        '''
        init_nodes = []
        for t in targs:
            if not isinstance(t, DAGNode):
                init_nodes.append(CNOT(t, ))
         
            


'''
    Particular Choices of Gates
'''
class CNOT(MultiQubitGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, data="CNOT", cycles=3, **kwargs)

class Z(InPlaceGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, data="Z", **kwargs)

class X(InPlaceGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, data="X", **kwargs)

class INIT(InPlaceGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, data="INIT", **kwargs)

'''
    Compositional Gates
'''

class PREP(CompositionalGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, data="PREP", **kwargs)

class Toffoli(CompositionalGate):
    pass

