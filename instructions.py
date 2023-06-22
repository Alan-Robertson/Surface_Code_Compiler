from dag_node import DAGNode

'''
    Base Gate Behaviours
'''
class MultiQubitGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class InPlaceGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ANCGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CompositionalGate(DAGNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

