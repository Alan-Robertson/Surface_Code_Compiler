import numpy as np
import copy
from utils import log

from dag_node import DAGNode
from instructions import INIT, PREP, MagicGate, CompositionalGate


class DAG():
    def __init__(self, n_blocks, *initial_gates):

        self.n_blocks = n_blocks
        
        # Initial Nodes
        self.gates = [INIT(i) for i in range(n_blocks)] # List of gates
        self.blocks = {i:self.gates[i] for i in range(n_blocks)}

        # Layer Later
        self.layers = []
        self.layers_conjestion = []
        self.layers_msf = []

        # Magic State Factory and Compositional nodes
        self.composition_units = set()
        self.msf_extra = None # For rewriting, remove

        # Tracks which node each gate was last involved in
        self.last_block = {i:self.gates[i] for i in range(n_blocks)} 
        
        for gate in initial_gates:
            self.add_gate(gate)


    def __repr__(self):
        return str(self.layers)


    def add_gate(self, gate_constructor: type, *args, deps=None, targs=None, **kwargs):
        '''
            add_gate
            Wrapper for adding all gate types
        '''
        if CompositionalGate in gate_constructor.mro():
            return self.add_compositional_gate(gate_constructor, *args, deps=deps, targs=targs, **kwargs)
        else:
            return self.add_single_gate(gate_constructor, *args, deps=deps, targs=targs, **kwargs)

    def add_compositional_gate(self, gate_constructor: type, *args, deps=None, targs=None, **kwargs):
        '''
            add_compositional_gate
            Adds a set of composed gates to the DAG
        '''
        gate_group = gate_constructor(*args, deps=deps, targs=targs, **kwargs).gate_group
        for gate in gate_group:
            add_single_gate(self, None, *args, deps=None, targs=None, gate=gate, **kwargs)


    def add_single_gate(self, gate_constructor: type, *args, deps=None, targs=None, gate=None, **kwargs):
        '''
            add_gate
            Adds a single gate to the DAG
        '''
        if gate is None:
            gate = gate_constructor(*args, deps=deps, targs=targs, **kwargs)

        deps = gate.deps
        symbol = gate.symbol

        # Register a new compositional object
        if isinstance(gate, CompositionalGate) and symbol:
            self.composition_units.add(symbol)

            if symbol not in self.last_block:
                initialiser = INIT(targs=symbol, **kwargs)
                self.last_block[symbol] = initialiser
                self.blocks[symbol] = initialiser

        # Update last block 
        predicates = {}
        for t in gate.deps + gate.targs:
            # Fungibility of magic state factories, to be resolved during allocation
            if t in self.composition_units:
                predicates[t] = self.blocks[t]
            else:
                predicates[t] = self.last_block[t]
                self.last_block[t] = gate
        
        # Resolve gate predicates
        gate.predicates = predicates
        gate.layer_num = max((predicate.layer_num + 1 
                              for predicate in gate.predicates.values()), 
                              default=0)

    
        # Calculate slack on the gate
        for t in gate.predicates:
            gate.predicates[t].slack = max(gate.predicates[t].slack, 1 / (gate.layer_num - gate.predicates[t].layer_num))
            gate.predicates[t].antecedents[t] = gate

        self.gates.append(gate)
        self.layer_gate(gate)

    def layer_gate(self, gate):
        if gate.layer_num >= len(self.layers):
            self.layers += [[] for _ in range(gate.layer_num - len(self.layers) + 1)]
            self.layers_conjestion += [0 for _ in range(gate.layer_num - len(self.layers_conjestion) + 1)]
            self.layers_msf += [[] for _ in range(gate.layer_num - len(self.layers_msf) + 1)]
        
        self.layers_conjestion[gate.layer_num] += gate.non_local
        self.layers[gate.layer_num].append(gate)
        if gate.symbol in self.composition_units:
            self.layers_msf[gate.layer_num].append(gate)


    def layer(self):
        self.layers = []
        for g in self.gates:
            self.layer_gate(g)

    def depth_parallel(self, n_channels):
        return sum(max(1, 1 + layer_conjestion - n_channels) for layer_conjestion in self.layers_conjestion)
        

    def dag_traverse(self, n_channels, *msfs, blocking=True, debug=False):
        traversed_layers = []

        # Magic state factory data
        msfs = list(msfs)
        msfs.sort(key = lambda x : x.cycles)
        msfs_state = [0] * len(msfs)

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
                if gate.resolved:
                    continue

                # Channel resolution
                if (not gate.non_local) or (gate.non_local and non_local_gates_in_layer < n_channels):

                    # Check predicates
                    predicates_resolved = True
                    for predicate in gate.edges_precede:
                        if not gate.edges_precede[predicate].resolved or (gate.edges_precede[predicate].magic_state == False and patch_used[predicate]):
                            predicates_resolved = False
                            break
                    # print("resolved", gate, gate.layer_num)
                    # if gate.layer_num == 12:
                    #     print(f"{ {m: g.resolved for m,g in self.msfs.items()}=} {msfs=} {msfs_state=}")

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
            
            # Update MSF cycle state
            for i, gate in enumerate(msfs):
                if msfs_state[i] <= msfs[i].cycles:
                    msfs_state[i] += 1
                if msfs_state[i] == msfs[i].cycles:
                    self.composition_units[msfs[i].symbol].resolved += 1

            unresolved = copy.copy(unresolved_update)
            if debug:
                print("FL:", front_layer)

        for gate in self.gates:
            gate.resolved = False

        for symbol in self.composition_units:
            self.composition_units[symbol].resolved = 0

        return len(traversed_layers), traversed_layers


    def depth_msf(self, *msfs, blocking=True, debug=True):
        ms_factories = {}
        for msf in msfs:
            if msf.symbol not in ms_factories:
                ms_factories[msf.symbol] = [[msf, 0]]
            else:
                ms_factories[msf.symbol].append([msf, 0])

        # Sort low to high cycles for maximum throughput
        for symbol in ms_factories:
            ms_factories[symbol].sort(key=lambda msf: msf[0].cycles)

        if debug:
            print(ms_factories)

        ms_gates = []
        n_cycles = 0
        while n_cycles < len(self.layers_msf) or len(ms_gates) > 0:
            
            if n_cycles < len(self.layers_msf):
                ms_gates += self.layers_msf[n_cycles]

            if debug:
                print(n_cycles)
                print(ms_factories)
                print(ms_gates)
                print("#####")

            # Clear all gates possible
            if (len(ms_gates) > 0):
                i = 0
                for ms_gate in ms_gates:
                    for j, (factory, count) in enumerate(ms_factories[ms_gate.symbol]):
                        if count >= factory.cycles:
                            ms_factories[ms_gate.symbol[1]] -= factory.cycles
                            ms_gates.pop(i)
                            i -= 1
                            break
                    i += 1

            # Update
            for symbol in ms_factories:
                for i, (factory, count) in enumerate(ms_factories[symbol]):
                    if blocking and count < factory.cycles:
                        ms_factories[symbol][i][1] += 1
                    elif not blocking:
                        ms_factories[symbol][i][1] += 1
            n_cycles += 1
        return n_cycles

              

    
    def calculate_proximity(self):
        m, minv = {}, []
        syms = self.composition_units.keys()
        for i in range(self.n_blocks):
            m[i] = i
            minv.append(i)
        for s in syms:
            m[s] = len(minv)
            minv.append(s)
        
        prox = np.zeros((len(minv), len(minv)))

        for layer in self.layers:
            for gate in layer:
                if len(gate.targs) > 1:
                    for targ in gate.targs:                            
                        for other_targ in gate.targs:
                            if other_targ is not targ:
                                prox[m[targ], m[other_targ]] += 1
        return prox, m, minv

    def calculate_conjestion(self):
        m, minv = {}, []
        syms = self.composition_units.keys()
        for i in range(self.n_blocks):
            m[i] = i
            minv.append(i)
        for s in syms:
            m[s] = len(minv)
            minv.append(s)
        
        conj = np.zeros((len(minv), len(minv)))

        for layer in self.layers:
            for gate in layer:
                if len(gate.targs) > 1:
                    for other_gate in layer:
                        if other_gate is not gate and len(other_gate.targs) > 1:
                            for targ in gate.targs:
                                for other_targ in other_gate.targs:
                                    conj[m[targ], m[other_targ]] += 1
        return conj, m, minv

    def remap_msfs(self, n_channels, msfs):
        # TODO fix ugly hack
        # gates_copy = copy.deepcopy(self.gates)

        self.dag_traverse(n_channels, *msfs)
        new_gates = []
        for gate in self.gates:
            old_msf = None
            log(f"{gate=} {gate.edges_precede=} {gate.edges_antecede=}")
            if gate.magic_state:
                old_msf = gate.magic_state

                msf_id, factory = gate.msf_extra
                new_sym = f"{old_msf}_#{msf_id}"
                
                if old_msf in self.composition_units:
                    del self.composition_units[old_msf]
                del gate.edges_precede[old_msf]

                if new_sym not in self.composition_units:
                    prev = INIT(targs=new_sym, layer_num=0, magic_state=new_sym)
                    new_gates.append(prev)
                else:
                    prev = self.composition_units[new_sym].edges_antecede[new_sym]

                prep = PREP(targs=new_sym, layer_num=prev.layer_num + 1, 
                                magic_state=new_sym, cycles=factory.cycles)

                prev.edges_antecede[new_sym] = prep
                prep.edges_precede[new_sym] = prev
                prep.edges_antecede[new_sym] = gate
                gate.edges_precede[new_sym] = prep
                new_gates.append(prep)
                self.composition_units[new_sym] = prep

                # gates_copy.append(gate.edges_precede[predicate])
                if old_msf:
                    gate.targs[gate.targs.index(old_msf)] = new_sym
        self.gates += new_gates
        log("new_gates", self.gates)
        # return gates_copy
            
