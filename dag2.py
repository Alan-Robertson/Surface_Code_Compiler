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
        self.antecedants = set()
        self.externs = externs

        self.n_cycles = n_cycles
        self.gates = [self]

    def __call__(self, scope=None):
        obj = copy.deepcopy(self)
        obj.predicates = set()
        obj.antecedants = set()
        if scope is not None:
            obj.inject(scope)
        else:
            obj.inject(obj.scope)
        return obj

    def inject(self, scope):
        if not isinstance(scope, Scope):
            scope = Scope(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)

    def unrollable(self):
        return self.scope.unrollable()
        
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
        self.antecedants = set()

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

        if gate.unrollable():
            self.unroll_gate(gate)
        else:
            self.gates.append(gate)
            self.update_dependencies(gate)
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
                for element in gate.symbol.io:
                    if element not in self.scope:
                        self.scope[element] = gate
                        self.last_layer[element] = gate
                self.update_dependencies(gate)

    def update_dependencies(self, gate):
        for dep in gate.symbol.io:
            predicate = self.last_layer[dep]
            predicate.antecedants.add(dep)
            gate.predicates.add(predicate)
            self.last_layer[dep] = gate

    def inject(self, scope):
        for gate in self.gates:
            gate.inject(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)

from symbol import Symbol
from scope import Scope
from instructions import INIT
import copy