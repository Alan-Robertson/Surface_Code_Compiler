import numpy as np

class DAGNode():
    def __init__(self, symbol, *args, scope=None, externs=None, n_cycles=1):
        if not isinstance(symbol, Symbol):
            symbol = Symbol(symbol)

        if externs is None:
            externs = list()
        if isinstance(externs, Symbol):
            externs = [externs]

        self.symbol = symbol
        
        if scope is None:
            scope = self.symbol.bind_scope()
        self.scope = scope
        
        self.predicates = set()
        self.antecedants = set()
        self.externs = externs

        self.n_cycles = n_cycles
        self.gates = [self]
        self.layers = [self]
        self.layer = 0

    def __call__(self, scope=None):
        obj = copy.deepcopy(self)
        obj.predicates = set()
        obj.antecedants = set()
        if scope is not None:
            obj.inject(scope)
        # else:
            # obj.inject(obj.scope)
        return obj


    def inject(self, scope):
        if not isinstance(scope, Scope):
            scope = Scope(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)

    def unrollable(self):
        return self.scope.unrollable()

    def n_cycles(self):
        return self.n_cycles
        
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

        self.externs = list()
        self.predicates = set()
        self.antecedants = set()

        self.layers = []
        self.layer = 0

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
            self.externs += gate.externs
        
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
        gate = gate(scope=self.scope)
        if len(gate.externs) > 0:
            self.externs += gate.externs
        self.gates.append(gate)
                    
    def unroll_gate(self, dag):
        for gate in dag.gates:
            if isinstance(gate, DAG):
                self.unroll_gate(gate)
            else:
                self.gates.append(gate)
                for element in gate.symbol.io:
                    if element not in self.scope:
                        # Merge lower scope into higher
                        self.scope[element] = gate
                        self.last_layer[element] = gate
                self.update_dependencies(gate)

    def update_dependencies(self, gate):
        for dep in gate.symbol.io:
            predicate = self.last_layer[dep]
            predicate.antecedants.add(dep)
            gate.predicates.add(predicate)
            self.last_layer[dep] = gate
        self.update_layer(gate)
        
    def update_layer(self, gate):
        print(gate, list(((predicate, predicate.layer) for predicate in gate.predicates)))
        layer_num = 1 + max((predicate.layer for predicate in gate.predicates if predicate is not gate), default=-1)
        if layer_num > len(self.layers) - 1:
            self.layers += [[] for i in range(layer_num - len(self.layers) + 1)]
        self.layers[layer_num].append(gate)
        gate.layer = layer_num

    def inject(self, scope):
        for gate in self.gates:
            gate.inject(scope)
        self.scope.inject(scope)
        self.symbol.inject(scope)

    def calculate_proximity(self):
        prox_len = len(self.externs) + len(self.scope)
        prox = np.zeros((prox_len, prox_len))
        lookup = (dict(map(lambda x: x[::-1], enumerate(self.scope.keys()))) 
                | dict(map(lambda x: x[::-1], zip(self.externs, range(len(self.scope), prox_len))))
        )
        for layer in self.layers:
            for gate in layer:
                for targ in gate.scope:                            
                    for other_targ in gate.scope:
                        if other_targ is not targ:
                            prox[lookup[targ], lookup[other_targ]] += 1
        return prox, lookup

    def calculate_conjestion(self):
        conj_len = len(self.externs) + len(self.scope)
        conj = np.zeros((conj_len, conj_len))
        lookup = (dict(map(lambda x: x[::-1], enumerate(self.scope.keys()))) 
                | dict(map(lambda x: x[::-1], zip(self.externs, range(len(self.scope), conj_len))))
        )
        for layer in self.layers:
            for gate in layer:
                if len(gate.scope) > 1:
                    for other_gate in layer:
                        if gate is not other_gate and len(other_gate.scope) > 1:
                            for targ in gate.scope:                            
                                for other_targ in other_gate.scope:
                                    conj[lookup[targ], lookup[other_targ]] += 1
        return conj, lookup


    def dag_traverse(self, n_channels, *msfs, blocking=True, debug=False, extern_sort=lambda x : x.n_cycles()):
        traversed_layers = []

        # Magic state factory data
        externs = list(externs)
        externs.sort(key=extern_sort)
        externs_state = [0] * len(externs)

        resolved = set()

        # Labelling
        msfs_index = {}
        msfs_type_counts = {}
        for i, m in enumerate(msfs):
            msfs_index[i] = msfs_type_counts.get(m.symbol, 0)
            msfs_type_counts[m.symbol] = msfs_index[i] + 1 
        # print(f"{msfs_index=}")
        unresolved = copy.copy(self.layers[0])
        unresolved_update = copy.copy(unresolved)

        for symbol in self.composition_units:
            self.composition_units[symbol].resolved = 0

        while len(unresolved) > 0:
            traversed_layers.append([])
            non_local_gates_in_layer = 0
            patch_used = [False] * self.n_blocks

            unresolved.sort(key=lambda x: x.slack, reverse=True)

            for gate in unresolved:
               
                # Gate already resolved, ignore
                if gate in resolved:
                    continue

                # Channel resolution
                if (not gate.non_local) or (gate.non_local and non_local_gates_in_layer < n_channels):

                    # Check predicates
                    predicates_resolved = True
                    for predicate in gate.edges_precede:
                        if not gate.edges_precede[predicate].resolved or (gate.edges_precede[predicate].magic_state == False and patch_used[predicate]):
                            predicates_resolved = False
                            break

                    if predicates_resolved:
                        traversed_layers[-1].append(gate)
                        gate.resolved = True

                        # Fungible MSF nodes
                        for targ in gate.targs:
                            if self.blocks[targ].magic_state is False:
                                patch_used[targ] = True

                        # Add antecedent gates
                        for antecedent in gate.edges_antecede:
                            if (gate.edges_antecede[antecedent] not in unresolved_update):
                                unresolved_update.append(gate.edges_antecede[antecedent])

                        # Expend a channel
                        if gate.non_local:
                            non_local_gates_in_layer += 1

                        # Remove the gate from the next round
                        unresolved_update.remove(gate)

                        # Resolve magic state factory resources
                        for predicate in gate.edges_precede:
                            if gate.edges_precede[predicate].magic_state:
                                for i, factory in enumerate(msfs):
                                    # Consume first predicate for each MS needed for the gate
                                    if predicate == factory.symbol and msfs_state[i] >= factory.cycles:
                                        msfs_state[i] = 0
                                        gate.edges_precede[predicate].resolved -= 1
                                        # TODO fix: ugly hack
                                        log("set", gate, i)
                                        gate.msf_extra = (msfs_index[i], factory)
                                                           #msfs_index[factory]
                                        break


class Bind():
    '''
        Bind
        This allows us to override the regular hashing behaviour of another arbitrary object
        such that we can compare instances of symbols rather than symbol strings 
    '''
    def __init__(obj):
        self.obj = obj
    def __eq__(self, obj):
        if isinstance(obj, Bind):
            return id(self.obj) == id(obj.obj)
        else:
            return id(self.obj) == id(obj)
    def __hash__(self):
        return id(self)

from symbol import Symbol
from scope import Scope
from instructions import INIT
import copy