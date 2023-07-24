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
        self.antecedents = set()
        self.externs = externs

        self.__n_cycles = n_cycles
        self.gates = [self]
        self.layers = [self]
        self.layer = 0
        self.slack = float('inf')

    def __call__(self, scope=None):
        self.predicates = set()
        self.antecedents = set()
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

    def get_unary_symbol(self):
        return next(iter(self.symbol))

    def internal_scope(self):
        return Scope(dict((i, j) for i, j in self.scope.items() if not i.is_extern()))

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
        self.antecedents = set()

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
                predicate.antecedents.add(gate)
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
    def compile(self, n_channels, *externs, extern_minimise=lambda extern: extern.n_cycles(), debug=False):
        
        # Clear any previous extern allocation
        self.externs.clear_scope()

        # Check I have enough channels
        assert(n_channels > 0)

        # Check that all externs are mapped
        assert(all(any(map(lambda i: i.satisfies(extern), externs)) for extern in self.externs.keys()))

        # Magic state factory data
        idle_externs = list(externs)
        idle_externs.sort(key=extern_minimise)

        # Map of extern binds
        extern_map = dict(zip(externs, map(ExternBind, externs)))
        extern_gate_to_bind = lambda gate: extern_map[self.externs[gate.get_unary_symbol()]]

        # Currently unallocated externs
        idle_externs = list(extern_map.values())
        
        # Active and waiting gates
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
                    idle_externs.pop(index)
                    self.externs[gate.symbol] = binding.get_obj()
                    active.add(ExternBind(gate))
                else:
                    # Cannot find a binding, add it to the wait list
                    waiting.append(ExternBind(gate))
            else:
                active.add(DAGBind(gate))

        # Gates that have finished, how many cycles this took, what happened in each layer
        resolved = set() 
        n_cycles = 0
        layers = []

        # This is a semaphore
        active_non_local_gates = 0

        # Keep running until all gates are resolved
        while len(active) > 0 or len(waiting) > 0:
            layers.append([])
            n_cycles += 1

            # Update each active gate
            for gate in active:
                gate.cycle()
                layers[-1].append(gate)
                
                # Update the underlying binding of each gate
                if gate.is_extern():
                    extern_gate_to_bind(gate).cycle()
                
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

                    # Decrement semaphore for non-local gates 
                    if gate.non_local():
                        active_non_local_gates -= 1

                    # See if any antecedents can be direct added to active
                    for antecedent in gate.antecedents():
                        all_resolved = True

                        # Check the predicate of each antecedent
                        for predicate in antecedent.predicates:       
                            # Catches nodes that are externs
                            # Ensure that the predicate has been mapped
                            if predicate.is_extern() and self.externs[predicate.get_unary_symbol()] is not None:
                                if not extern_gate_to_bind(predicate).resolved():
                                    all_resolved = False
                                    break

                            elif DAGBind(predicate) not in resolved:
                                all_resolved = False
                                break
                        if all_resolved:
                            waiting.append(DAGBind(antecedent))

                    # Unlock Externs For Reallocation
                    if gate.get_symbol() == RESET_SYMBOL:
                        reset_extern = gate.get_unary_symbol()
                        extern_bind = extern_map[self.externs[reset_extern]]
                        extern_bind.reset()                        
                        idle_externs.append(extern_bind)

            # Sort the waiting list based on the current slack
            waiting.sort()
            for gate in waiting:

                # If it's an extern gate then see if a free resource exists
                if gate.is_extern():
                    index, binding = next(
                        ((index, extern) for index, extern in enumerate(idle_externs) if extern.satisfies(gate)),
                         (None, None)
                         )

                    if binding is not None:
                        idle_externs.pop(index)
                        self.externs[gate.get_symbol()] = binding.get_obj()
                        active.add(gate)

                else:
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
            
            if debug:
                print("\n####")
                print("CYCLE {n_cycles}")
                print(f"\tACTIVE {active}\n\t WAITING {waiting}\n\t IDLE {idle_externs}\n\tCHANNELS {active_non_local_gates} / {n_channels}\n\t{resolved}")
                print("####\n")

        return n_cycles, layers


from symbol import Symbol
from scope import Scope
from instructions import INIT, RESET_SYMBOL
from bind import DAGBind, ExternBind
import copy