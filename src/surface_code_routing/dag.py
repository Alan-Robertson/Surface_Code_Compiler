import numpy as np
from heapq import heappush

from itertools import chain
from functools import reduce

import sys

from surface_code_routing import utils

# This gets triggered by deep copy in some areas
sys.setrecursionlimit(10000)

class DAGNode():
    def __init__(self, symbol, *args, scope=None, externs=None, n_cycles=1, n_ancillae=0, rotation=False, ancillae_type=None):
        symbol = symbol_resolve(symbol)
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
        # Predicate factories to inject
        self.antecedents = set()
        self.externs = externs

        # To be injected if all other predicates are resolved
        self.predicate_factories = set()
        self.__is_factory = None

        self.__n_cycles = n_cycles
        self.n_ancillae = n_ancillae
        self.ancillae_type = ancillae_type
        self.__rotates = rotation
        self.gates = [self]
        self.layers = [self]
        self.layer = 0
        self.slack = float('inf')

        self.back_edges = dict()
        self.forward_edges = dict()

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

    def rotates(self):
        return self.__rotates

    def rotate(self):
        self.__rotates ^= True

    def __repr__(self):
        return self.symbol.__repr__()

    def __contains__(self, other):
        return other in self.symbol.io


    def is_factory(self):
        # Factories are externs with no inputs
        # By design, all factories must eventually have a non-extern antecedent
        # If this isn't possible then the factory should be rolled into the scope of the anteceding extern
        if self.__is_factory is None:
            self.__is_factory = self.is_extern() and (sum(i is not self.symbol for i in self.symbol.io_in) == 0)

        return self.__is_factory


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
    def __init__(self, symbol, scope=None, verbose=False):

        symbol = symbol_resolve(symbol)
        self.symbol = symbol
        self.verbose = verbose

        if scope is None:
            scope = Scope()
        self.scope = scope

        for sym in self.symbol.io:
            if sym not in self.scope:
                self.scope[sym] = None

        self.gates: list[DAGNode] = []
        self.last_layer = {}

        self.n_ancillae = 0

        self.externs = Scope()
        self.predicates = set()
        self.antecedents = set()

        self.predicate_factories = set()

        self.forward_edges = dict()
        self.back_edges = dict()

        self.physical_externs = set()

        # Catches any undeclared externs in the scope
        for sym in self.scope.values():
            if sym is not None:
                if sym.is_extern():
                    self.externs[sym] = None

        self.layers = []
        self.compiled_layers = []
        self.layer = 0
        self.slack = float('inf')

        for obj in self.scope:
            if self.scope[obj] is None:
                init_node = DAGNode(Symbol(INIT_SYM, obj), n_cycles=1) 
                self.gates.append(init_node)
                self.last_layer[obj] = init_node
                self.update_dependencies(init_node)

    def debug_print(self, *args):
        return utils.debug_print(*args, debug=self.verbose)

    def extern(self):
        return self.symbol.extern()

    def io(self):
        return self.symbol.io

    def __getitem__(self, index):
        return self.scope(index)

    def n_cycles(self):
        return len(self.layers)

    def rotates(self):
        return False

    def rotate(self):
        for i in self.gates:
            i.rotate()

    def add_gate(self, dag, *args, scope=None, **kwargs):

        gate = dag(scope=scope)

        operands = gate.symbol.io
        if len(gate.externs) > 0:
            self.externs |= gate.externs

        if gate.unrollable():
            gate = self.unroll_gate(gate)
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
        if not self.is_extern():
            self.merge_scopes(gate)
        self.update_dependencies(gate)
        return gate

    def unroll_gate(self, dag):
        unrolled = []
        for gate in dag.gates:
            if isinstance(gate, DAG):
                unrolled += self.unroll_gate(gate)
            else:
                self.gates.append(gate)
                self.merge_scopes(gate)
                self.update_dependencies(gate)
                unrolled.append(gate)
        return unrolled
        

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
            # Used for complex factory logic
            # Without this skip a linear DAG structure is enforced
            # On the output of extern factories
            # This linear dag structure can cause deadlocks
            if (dep.is_extern() and dep.is_factory()): 
                continue

            else: # Linearity of dependencies
                predicate = self.last_layer[dep]
                gate.back_edges[dep] = predicate
                predicate.forward_edges[dep] = gate

            # Breaks self-referencing gates
            if predicate is not gate:
                predicate.antecedents.add(gate)
                gate.predicates.add(predicate)
                self.last_layer[dep] = gate

        self.update_layer(gate)

        # Propagate factories till non_local operation
        for dep in gate.predicates:
            if not dep.non_local() and not dep.is_factory():
                gate.predicate_factories |= dep.predicate_factories
            if dep.is_factory():
               gate.predicate_factories.add(dep)
        # Non-local gates implies more than zero predicates
        if len(gate.predicates) > 0 and gate.non_local() and all(map(lambda x: (not x.non_local()) and (len(x.predicate_factories) > 0), gate.predicates)):
            raise Exception("Cannot Depend on multiple externs directly, wrap the extern dependencies within the original extern, or introduce a register within the current scope")

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

    def calculate_logical_proximity(self):
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

    def calculate_logical_conjestion(self):
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


    def calculate_physical_conjestion(self):
        conj_len = len(self.internal_scope()) + len(self.physical_externs)
        conj = np.zeros((conj_len, conj_len))

        lookup_inv = list(chain(self.internal_scope().keys(), self.physical_externs))
        lookup = dict(map(lambda x: x[::-1], enumerate(lookup_inv)))

        for layer in self.layers:
            for gate in layer:
                if len(gate.scope) > 1:
                    for other_gate in layer:
                        if gate is not other_gate and len(other_gate.scope) > 1:
                            for targ in gate.scope:
                                for other_targ in other_gate.scope:
                                    tmp_targ = targ.get_parent()
                                    tmp_other_targ = other_targ.get_parent()

                                    if tmp_targ.is_extern():
                                        tmp_targ = self.scope[tmp_targ]
                                    if tmp_other_targ.is_extern():
                                        tmp_other_targ = self.scope[tmp_other_targ]

                                    conj[lookup[tmp_targ], lookup[tmp_other_targ]] += 1
        return conj, lookup

    def lookup(self):
        initial_list = list(self.internal_scope().keys()) + self.physical_externs
        register = symbol_resolve('REG')
        lookup_list = list()
        for element in initial_list:
            if element.get_symbol().is_extern():
                lookup_list.append(element.get_symbol())

            else:
                sym = symbol_resolve(element)
                sym.predicate = register
                lookup_list.append(sym)
        return lookup_list

    def calculate_physical_proximity(self):
        prox_len = len(self.internal_scope()) + len(self.physical_externs)
        prox = np.zeros((prox_len, prox_len))
        lookup_inv = list(chain(self.internal_scope().keys(), self.physical_externs))
        lookup = dict(map(lambda x: x[::-1], enumerate(lookup_inv)))

        for layer in self.layers:
            for gate in layer:
                for targ in gate.scope:
                    for other_targ in gate.scope:
                        if other_targ is not targ:

                            tmp_targ = targ.get_parent()
                            tmp_other_targ = other_targ.get_parent()

                            if tmp_targ.is_extern():
                                tmp_targ = self.scope[tmp_targ]
                            if tmp_other_targ.is_extern():
                                tmp_other_targ = self.scope[tmp_other_targ]

                            prox[lookup[tmp_targ], lookup[tmp_other_targ]] += 1

        return prox, lookup

    def compile(self, n_channels, *externs, extern_minimise=lambda extern: extern.n_cycles(), debug=False, exact_alloc=True):

        # Clear any previous extern allocation
        self.externs.clear_scope()
        self.physical_externs = list(externs)

        # Check I have enough channels
        assert(n_channels > 0)

        # Check that all externs are mapped
        if exact_alloc:
            assert(all(any(map(lambda i: i.satisfies(extern), self.physical_externs)) for extern in self.externs.keys()))


        # Map of physical externs to binds 
        # This tracks the state of the input externs
        extern_map = dict(zip(self.physical_externs, map(ExternBind, externs)))
        # First free cycle for each extern object
        externs_first_free_cycle = {extern: 0 for extern in extern_map.values()}

        # Performs a lookup from a gate to 
        extern_gate_to_bind = (
            lambda gate: extern_map[
                self.externs[gate.get_unary_symbol()]
            ]
        )

        # Currently unallocated externs
        idle_externs = list(extern_map.values())
        idle_externs.sort(key=extern_minimise)

        # Active and waiting gates
        active = set()
        waiting = list()

        # Initially active gates
        for gate in self.layers[0]:

            # Ignore factories
            if gate.is_factory():
                continue

            if gate.is_extern():
                # Grab the next matching binding
                index, binding = next(
                    ((index, extern) for index, extern in enumerate(idle_externs) if extern.satisfies(gate)),
                     (None, None)
                     )
                if binding is not None:
                    idle_externs.pop(index)
                    self.externs[gate.get_unary_symbol()] = binding.get_obj()
                    self.scope[gate.get_unary_symbol()] = binding.get_obj()

                    bind = ExternDAGBind(gate, binding)
                    active.add(bind)

                else:
                    # Cannot find a binding, add it to the wait list
                    waiting.append(ExternBind(gate))
            else:
                active.add(DAGBind(gate))
        self.debug_print(f"Initial Gates: {active}\nWaiting: {waiting}")

        # Gates that have finished, how many cycles this took, what happened in each layer
        resolved = set()
        n_cycles = 0
        layers = []

        # This is a semaphore
        active_non_local_gates = 0
    
        # Prevents multi-queueing of factories
        queued_factories = set()

        # Keep running until all gates are resolved
        while len(active) > 0 or len(waiting) > 0:
            self.debug_print(f"Active: {active}\n Waiting: {waiting}\nIdle:{idle_externs}")

            layers.append([])
            n_cycles += 1

            # Update each active gate
            for gate in active:
                layers[-1].append(gate)
                gate.cycle()

            # Non-extern gates resolve directly
            recently_resolved = list(filter(lambda x: x.resolved(), active))

            # Active gate set reduces to the unresolved gates 
            active = set(filter(lambda x: not x.resolved(), active))

            # Fast forwarding
            # No gates resolved, state does not change, fast forward
            if len(recently_resolved) == 0 and len(active) > 0:
                fast_forward = float('inf')  
                for gate in active:
                    fast_forward = min(fast_forward, gate.n_cycles() - gate.curr_cycle())

                if fast_forward > 2:
                    self.debug_print(f"Fast Forward: {fast_forward}")
                    self.debug_print(active)

                    fast_forward -= 1

                    # Fast-forward each gate
                    for gate in active:
                        gate.cycle(step=fast_forward)

                    # Update layers
                    for _ in range(fast_forward):  
                        layers.append(list(layers[-1]))

                    n_cycles += fast_forward

                # Return to checking for completed gates 
                continue

            # Gates resolved in the previous cycle, update active gates and dependencies
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
                            if DAGBind(predicate) not in resolved:
                                all_resolved = False
                                break

                        if all_resolved:
                            if antecedent.is_extern():
                                targ = ExternBind(antecedent)
                                waiting.append(targ)
                                
                            else:
                                waiting.append(DAGBind(antecedent))

                    # Unlock Externs For Reallocation
                    if gate.get_symbol() == RESET_SYMBOL:
                        self.debug_print(f"RESET {gate}")

                        extern_bind = extern_gate_to_bind(gate)
                        extern_bind.reset()


                        idle_externs.append(extern_bind)
                        externs_first_free_cycle[extern_bind] = len(layers)

            # Sort the waiting list based on the current slack
            waiting.sort()
            for gate in waiting:
                # If it's an extern gate then see if a free resource exists
                if gate.is_extern():
                    if len(idle_externs) == 0:
                        continue

                    index, binding = next(
                        ((index, extern) for index, extern in enumerate(idle_externs) if extern.satisfies(gate)),
                         (None, None)
                         )

                    if binding is not None:

                        extern = idle_externs.pop(index)

                        self.externs[gate.get_unary_symbol()] = binding.get_obj()
                        self.scope[gate.get_unary_symbol()] = binding.get_obj()
                        gate = gate.bind_physical_extern(binding)
                        
                        # Pre-warming factories
                        if gate.is_factory():
                            last_free_cycle = externs_first_free_cycle[extern]
                            previous_cycles = min(binding.n_cycles(), len(layers) - last_free_cycle)
                            gate.set_cycles_completed(previous_cycles)
                            binding.set_cycles_completed(previous_cycles)
                            for layer in layers[last_free_cycle:]:
                                layer.append(gate)
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

            # Dodgy fix for a bug
            # Somehow externs are escaping from the idle extern list :/
            #if len(active) == 0:
            #    print("FIX")
            #    idle_externs = list(extern_map.values())
            #    idle_externs.sort(key=extern_minimise)

            self.debug_print(f"""
 ####
CYCLE {n_cycles}
ACTIVE {active}
WAITING {waiting}
IDLE {idle_externs}
CHANNELS {active_non_local_gates} / {n_channels}
{resolved}
####
                             """)

        self.compiled_layers = layers
        return n_cycles, layers

    def __tikz__(self):
        return tikz_dag(self)


from surface_code_routing.symbol import symbol_resolve, Symbol
from surface_code_routing.scope import Scope
from surface_code_routing.instructions import INIT, RESET_SYMBOL, IDLE_SYMBOL, INIT_SYM
from surface_code_routing.bind import DAGBind, ExternBind, ExternDAGBind
from surface_code_routing.tikz_utils import tikz_dag
import copy
