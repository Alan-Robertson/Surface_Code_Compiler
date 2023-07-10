from IPython.core.debugger import set_trace

class DAGNode():
    def __init__(self, symbol, *args, scope=None, externs=None, n_cycles=1):
        if not isinstance(symbol, Symbol):
            symbol = Symbol(symbol)

        if externs is None:
            externs = set()

        self.symbol = symbol
        
        self.scope = self.symbol.bind_scope()
        
        self.predicates = set()
        self.externs = externs

        self.n_cycles = n_cycles
        self.gates = [self]

    def __call__(self, scope):
        obj = copy.deepcopy(self)
        obj.inject(scope)
        return obj

    def inject(self, scope):
        self.scope.inject(scope)
        #self.symbol.inject(scope)
        

    def __repr__(self):
        return self.symbol.__repr__()

class DAG(DAGNode):
    def __init__(self, symbol, scope=None):

        if not isinstance(symbol, Symbol):
            symbol = Symbol(symbol)
        self.symbol = symbol

        if scope is None:
            scope = Scope()
        self.scope = scope

        for sym in self.symbol.io:
            if sym not in self.scope:
                self.scope[sym] = None

        self.gates = []
        self.last_layer = {}
        self.externs = set()
        self.predicates = set()

        for obj in self.scope:
            if self.scope[obj] is None:
                init_gate = INIT(obj)
                self.gates.append(init_gate)
                self.last_layer[obj] = init_gate

    def __getitem__(self, index):
        return self.scope(index)

        
    def add_gate(self, dag, *args, scope=None, **kwargs):
        gate = dag(scope)
        operands = gate.symbol.io
        self.externs |= gate.externs
        
        for operand in operands:
            if gate.scope[operand] is operand:
                self.scope[operand] = None

        print(gate, self.scope, gate.scope)
        if self.scope.exactly_satisfies(gate.scope):
            self.unroll_gate(gate)
        else:
            pass
            #self.gates.append(gate)
                        
            # predicates = {}
            # for t in operands:
            #     predicates[t] = self.last_block[t]
            #     self.last_block[t] = gate
            # gate.predicates = predicates
        return gate

    def add_node(self, symbol, *args, **kwargs):
        gate = DAGNode(symbol, *args, **kwargs)
        gate(self.scope)
        self.gates.append(gate)
                    
    def unroll_gate(self, dag):
        for gate in dag.gates:
            if isinstance(gate, DAG):
                self.unroll_gate(gate)
            else:
                self.gates.append(gate)

    def inject(self, scope):
        for gate in self.gates:
            gate.inject(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)



from symbol import Symbol
from scope import Scope
from instructions import INIT
import copy