from dag_node import DAGNode

'''
    Base Gate Behaviours
'''
class MultiQubitGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

class InPlaceGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

class ANCGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

class CompositionalGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

'''
    Particular Choices of Gates
'''
class CNOT(MultiQubitGate):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, cycles=3, **kwargs)

class Z(InPlaceGate):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, data='Z', **kwargs)

class X(InPlaceGate):
    pass

class INIT(InPlaceGate):
    pass

'''
    Compositional Gates
'''

class PREP(CompositionalGate):
    pass

class Toffoli(CompositionalGate):
    pass

