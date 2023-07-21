import numpy as np
from heapq import heappush

from itertools import takewhile
from functools import reduce

class DAGNode():
    def __init__(self, symbol, *args, scope=None, externs=None, n_cycles=1):
        if not isinstance(symbol, Symbol):
            symbol = Symbol(symbol)

        if externs is None:
            externs = dict()
        if isinstance(externs, Symbol):
            externs = {externs:None}
        externs = Scope({extern:None for extern in externs})

        self.symbol = symbol

        if scope is None:
            scope = self.symbol.bind_scope()
        self.scope = scope

        # Catches any undeclared externs in the scope
        for sym in self.scope.values():
            if sym.is_extern():
                externs[sym] = None
        
        self.predicates = set()
        self.antecedants = set()
        self.externs = externs

        self.__n_cycles = n_cycles
        self.gates = [self]
        self.layers = [self]
        self.layer = 0
        self.slack = float('inf')

    def __call__(self, scope=None):
        self.predicates = set()
        self.antecedants = set()
        if scope is not None:
            self.inject(scope)
        return self


    def inject(self, scope):
        if not isinstance(scope, Scope):
            scope = Scope(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)

    def unrollable(self):
        return self.scope.unrollable()

    def n_cycles(self):
        return self.__n_cycles
        
    def __repr__(self):
        return self.symbol.__repr__()

    def non_local(self):
        return len(self.symbol.io) > 1

    def is_extern(self):
        return self.symbol.is_extern()

    def get_symbol(self):
        return self.symbol

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

        self.externs = Scope()
        self.predicates = set()
        self.antecedants = set()

        # Catches any undeclared externs in the scope
        for sym in self.scope.values():
            if sym.is_extern():
                self.externs[sym] = None

        self.layers = []
        self.layer = 0
        self.slack = float('inf')

        for obj in self.scope:
            if self.scope[obj] is None:
                init_gate = INIT(obj)
                self.gates.append(init_gate)
                self.last_layer[obj] = init_gate
                self.update_layer(init_gate)
                self.update_dependencies(init_gate)


    def __getitem__(self, index):
        return self.scope(index)

    def n_cycles(self):
        return len(self.layers)

    def add_gate(self, dag, *args, scope=None, **kwargs):

        gate = dag(scope=scope)
        
        operands = gate.symbol.io
        if len(gate.externs) > 0:
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
        # Todo, check if this is needed
        gate = gate(scope=self.scope)
        if len(gate.externs) > 0:
            self.externs |= gate.externs
        self.gates.append(gate)
        self.merge_scopes(gate)
        self.update_dependencies(gate)
        return gate
                    
    def unroll_gate(self, dag):
        for gate in dag.gates:
            if isinstance(gate, DAG):
                self.unroll_gate(gate)
            else:
                self.gates.append(gate)
                self.merge_scopes(gate)                
                self.update_dependencies(gate)

    def merge_scopes(self, gate):
        for element in gate.symbol.io:
            if element not in self.scope:
                # Merge lower scope into higher
                self.scope[element] = gate
            if element not in self.last_layer:
                self.last_layer[element] = gate
        return

    def update_dependencies(self, gate):
        for dep in gate.symbol.io:
            predicate = self.last_layer[dep]
            # Breaks self-referencing gates
            if predicate is not gate:
                predicate.antecedants.add(gate)
                gate.predicates.add(predicate)
                self.last_layer[dep] = gate
        self.update_layer(gate)
        return
        
    def update_layer(self, gate):
        layer_num = 1 + max((predicate.layer for predicate in gate.predicates if predicate is not gate), default=-1)

        # Create layers
        if layer_num > len(self.layers) - 1:
            self.layers += [[] for i in range(layer_num - len(self.layers) + 1)]
        self.layers[layer_num].append(gate)
        gate.layer = layer_num

        # Update slack on predicates
        for predicate in gate.predicates:
            predicate.slack = min(predicate.slack, gate.layer - predicate.layer)
        return

    def inject(self, scope):
        for gate in self.gates:
            gate.inject(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)
        return

    def calculate_proximity(self):
        prox_len = len(self.scope)
        prox = np.zeros((prox_len, prox_len))
        lookup = dict(map(lambda x: x[::-1], enumerate(self.scope.keys())))

        for layer in self.layers:
            for gate in layer:
                for targ in gate.scope:                            
                    for other_targ in gate.scope:
                        if other_targ is not targ:
                            prox[lookup[targ], lookup[other_targ]] += 1
        return prox, lookup

    def calculate_conjestion(self):
        conj_len = len(self.scope)
        conj = np.zeros((conj_len, conj_len))
        lookup = dict(map(lambda x: x[::-1], enumerate(self.scope.keys()))) 

        for layer in self.layers:
            for gate in layer:
                if len(gate.scope) > 1:
                    for other_gate in layer:
                        if gate is not other_gate and len(other_gate.scope) > 1:
                            for targ in gate.scope:                            
                                for other_targ in other_gate.scope:
                                    conj[lookup[targ], lookup[other_targ]] += 1
        return conj, lookup


    # TODO Create this as a separate wrapper
    def compile(self, n_channels, *externs, debug=False, extern_minimise=lambda extern: extern.n_cycles()):
        
        # Check I have enough channels
        assert(n_channels > 0)

        # Check that all externs are mapped
        assert(all(any(map(lambda i: i.satisfies(extern), externs)) for extern in self.externs.keys()))

        traversed_layers = []

        # Magic state factory data
        idle_externs = list(externs)
        idle_externs.sort(key=extern_minimise)
        idle_externs = list(map(ExternBind, externs))

        # In use externs are locked
        locked_externs = dict()
        
        active = set()
        waiting = list()

        # Initially active gates
        for gate in self.layers[0]:
            if gate.is_extern():
                index, binding = next(
                    ((index, extern) for index, extern in enumerate(idle_externs) if extern.satisfies(gate)),
                     (None, None)
                     )

                if binding is not None:
                    print(f"Bound: {gate} -> {binding}")
                    idle_externs.pop(index)
                    self.externs[gate] = binding
                else:
                    # Cannot find a binding, add it to the wait list
                    waiting.append(ExternBind(gate))
            else:
                active.add(DAGBind(gate))

        resolved = set()
            
        n_cycles = 0

        layers = []

        # This is a semaphore
        active_non_local_gates = 0

        while len(active) > 0:
            layers.append([])
            n_cycles += 1
            # Update each active gate
            for gate in active:
                gate.cycle()
                layers[-1].append(gate)
                print(gate)

            # Update each extern
            for extern in idle_externs:
                if extern.pre_warm():
                    layers[-1].append(extern)

            recently_resolved = list(filter(lambda x: x.resolved(), active))
            active = set(filter(lambda x: not x.resolved(), active))

            # For each gate we resolve check if there are any antecedents that can be added to the waiting list
            for gate in recently_resolved:
                if gate.resolved():
                    resolved.add(gate)

                    if gate.non_local():
                        active_non_local_gates -= 1

                    if gate.is_extern():
                        print('BOUND', gate, self.externs[gate])

                    for antecedent in gate.antecedants:
                        all_resolved = True
                        for predicate in antecedent.predicates:                           
                            if DAGBind(predicate) not in resolved:
                                all_resolved = False
                                break
                        if all_resolved:
                            waiting.append(DAGBind(antecedent))
            

            # Sort the waiting list based on the current slack
            waiting.sort()

            for gate in waiting:
                # Gate is purely local, add it
                if not gate.non_local():
                    active.add(gate)
                    continue

                # Non-local gates only
                # Already expended all channels, skip
                if active_non_local_gates >= n_channels:
                    continue

                # Gate is non-local but we have channel capacity for it
                active.add(gate)
                active_non_local_gates += 1

            # Update the waiting list
            waiting = list(filter(lambda x: x not in active, waiting))

        return n_cycles, layers

class Bind():
    def __init__(self, obj):
        self.obj = obj
        self.cycles_completed = 0

    def get_symbol(self):
        return self.obj.get_symbol()

    # Getters and Setters
    def get_cycles_completed():
        return self.cycles_completed

    def reset_cycles_completed():
        self.cycles_completed = 0

    def cycle():
        self.cycles_completed += 1

    def __repr__(self):
        return f"{repr(self.obj)} : {self.curr_cycle()} {self.n_cycles()}"

    # Wrapper functions
    def predicates(self):
        return self.obj.predicates

    def antecedents(self):
        return self.obj.predicates

    def n_pre_warm_cycles(self):
        return self.obj.pre_warm()

    def n_cycles(self):
        return self.obj.n_cycles()

    def n_pre_warm_cycles(self):
        return self.obj.n_pre_warm_cycles()

    def non_local(self):
        return self.obj.non_local()

    def satisfies(self, other):
        return self.get_symbol().satisfies(other.get_symbol())

    # Cycle functions
    def cycle(self):
        self.cycles_completed += 1

    def curr_cycle(self):
        return self.cycles_completed

    def resolved(self):
        return self.cycles_completed >= self.n_cycles()

    def reset(self):
        self.cycles_completed = 0

    
class ExternBind(Bind):
    def __init__(self, obj):
        # Nesting this ensures non-fungibility
        self.obj = Bind(obj)

    # def __repr__(self):
    #     return f"{repr(self.obj)} {self.n_cycles()}"

    def pre_warm(self):
        if self.n_cycles() < self.n_pre_warm_cycles():
            self.cycle()
            return True
        return False

    # Wrappers
    def get_cycles_completed(self):
        return self.obj.cycles_completed()

    def reset_cycles_completed(self):
        self.obj.reset_cycles_completed()

    def cycle(self):
        self.obj.cycle()

    def curr_cycle(self):
        self.obj.curr_cycle()

    def n_pre_warm_cycles(self):
        return self.obj.n_pre_warm_cycles()


    def is_extern(self):
        return True


class DAGBind(Bind):
    '''
        Bind
        This allows us to override the regular hashing behaviour of another arbitrary object
        such that we can compare instances of symbols rather than symbol strings 
    '''
    def __init__(self, obj):
        self.slack = obj.slack
        self.antecedants = obj.antecedants
        self.predicates = obj.predicates
        self.symbol = obj.symbol
        super().__init__(obj)

    def wait(self):
        self.slack -= 1

    def satisfies(self, other):
        if isinstance(other, Bind):
            return self.obj.symbol == other.obj.symbol
        else:
            self.obj.symbol == other.symbol

    def pre_warm(self):
        return False

    def __gt__(self, other):
        return self.slack > other.slack

    def __lt__(self, other):
        return self.slack < other.slack

    def __ge__(self, other):
        return self.slack >= other.slack

    def __le__(self, other):
        return self.slack <= other.slack

    def __eq__(self, obj):
        if isinstance(obj, Bind):
            return id(self.obj) == id(obj.obj)
        else:
            return id(self.obj) == id(obj)

    def __hash__(self):
        return id(self.obj)

    def is_extern(self):
        return False

from symbol import Symbol
from scope import Scope
from instructions import INIT
import copy