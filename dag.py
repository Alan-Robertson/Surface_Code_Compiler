import numpy as np
import copy

class DAGNode():
    def __init__(self, targs, edges=None, data=None, layer_num=None, slack=0):
        if type(targs) is int:
            targs = [targs]
        if edges is None:
            edges = []

        if data is None:
            data = ""

        self.targs = targs
        self.data = data

        # We will be filling these in once we've got an allocation
        self.start = -1
        self.end = -1
        self.anc = []
        
        self.edges_precede = edges
        self.edges_antecede = {}

        self.non_local = len(self.targs) > 1
        self.slack = slack

        if layer_num is None:
            layer_num = max(self.edges_precede[i].layer_num + 1 for i in self.edges_precede)
        self.layer_num = layer_num

    def add_antecedent(self, targ, node):
        self.edges_antecede[targ] = node 

    def __contains__(self, i):
        return self.targs.__contains__(i)

    def __repr__(self):
        return "{}:{}".format(self.data, self.targs)
    def __str__(self):
        return self.__repr__()

class DAG():
    def __init__(self, n_blocks):

        self.n_blocks = n_blocks
        
        # Initial Nodes
        self.gates = [DAGNode(i, data="INIT", layer_num = 0) for i in range(n_blocks)]

        # Layer Later
        self.layers = []
        self.layers_conjestion = []
        self.layers_msf = []

        # Magic State Factory Node
        self.msfs = {} #

        # Tracks which node each gate was last involved in
        self.last_block = {i:self.gates[i] for i in range(n_blocks)} 
        self.layer()

    def __repr__(self):
        return str(self.layers)

    def add_gate(self, targs, data=None, magic_state=False):
        if type(targs) is int:
            targs = [targs]

        targs = copy.deepcopy(targs) 

        edges = {}
        for t in targs:
            edges[t] = self.last_block[t]
        
        if magic_state is True:
            if data not in self.msfs:
                self.msfs[data] = DAGNode(-1, layer_num = 0)
            targs += [self.msfs[data]]
        gate = DAGNode(targs, edges, data=data)

        for t in targs:
            if t not in self.msfs: 
                self.last_block[t] = gate 

        for t in gate.edges_precede:
            gate.edges_precede[t].slack = max(gate.edges_precede[t].slack, 1 / (gate.layer_num - gate.edges_precede[t].layer_num))
            gate.edges_precede[t].edges_antecede[t] = gate

        self.gates.append(gate)
        self.layer_gate(gate)

    def layer_gate(self, gate):
        if gate.layer_num >= len(self.layers):
            self.layers += [[] for _ in range(gate.layer_num - len(self.layers) + 1)]
            self.layers_conjestion += [0 for _ in range(gate.layer_num - len(self.layers_conjestion) + 1)]
            self.layers_msf += [[] for _ in range(gate.layer_num - len(self.layers_msf) + 1)]
        
        self.layers_conjestion[gate.layer_num] += gate.non_local
        self.layers[gate.layer_num].append(gate)
        if gate.data in self.msfs:
            self.layers_msf[gate.layer_num].append(gate)


    def layer(self):
        self.layers = []
        for g in self.gates:
            self.layer_gate(g)

    def depth_parallel(self, n_channels):
        return sum(max(1, 1 + layer_conjestion - n_channels) for layer_conjestion in self.layers_conjestion)
        

    def dag_traverse(self, n_channels, *msfs, blocking=True, debug=False):
        front_layer = []
        unresolved = []

        traversed_layers = []

        unresolved = copy.copy(self.layers[0])
        unresolved_update = copy.copy(unresolved)

        while len(unresolved) > 0:
            traversed_layers.append([])
            non_local_gates_in_layer = 0

            unresolved.sort(key=lambda x: x.slack, reverse=True)

            if debug:
                print("UNRES:", unresolved)
            for gate in unresolved:
                if debug:
                    print("GATE:", str(gate), gate.non_local, non_local_gates_in_layer)
                if ((not gate.non_local) or (gate.non_local and non_local_gates_in_layer < n_channels)) and (gate not in front_layer):

                    predicates_resolved = True
                    for predicate in gate.edges_precede:
                        if gate.edges_precede[predicate] not in front_layer:
                            predicates_resolved = False
                            break

                    if predicates_resolved:
                        traversed_layers[-1].append(gate)
                        while gate in unresolved_update:
                            unresolved_update.remove(gate)
                        # for predicate in gate.edges_precede:
                        #     if gate.edges_precede[predicate] in front_layer: 
                        #         front_layer.remove(gate.edges_precede[predicate])
                        for antecedant in gate.edges_antecede:
                            if gate.edges_antecede[antecedant] not in front_layer:
                                unresolved_update.insert(0, gate.edges_antecede[antecedant])
                        front_layer.append(gate)
                        if gate.non_local:
                            non_local_gates_in_layer += 1

            front_layer_update = copy.copy(front_layer)
            for gate in front_layer:
                all_antecedants_resolved = True
                for antecedant in gate.edges_antecede:
                    if gate.edges_antecede[antecedant] not in front_layer:
                        all_antecedants_resolved = False
                        break
                if all_antecedants_resolved:
                    front_layer_update.remove(gate)
            front_layer = front_layer_update

            unresolved = copy.copy(unresolved_update)
            if debug:
                print("FL:", front_layer)

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
                    for j, (factory, count) in enumerate(ms_factories[ms_gate.data]):
                        if count >= factory.cycles:
                            ms_factories[ms_gate.data[1]] -= factory.cycles
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
        prox = np.zeros((self.n_blocks + 1, self.n_blocks + 1)) 

        for layer in self.layers:
            for gate in layer:
                if len(gate.targs) > 1:
                    for other_gate in layer:
                        if other_gate is not gate and len(other_gate.targs) > 1:
                            for targ in gate.targs:
                                for other_targ in other_gate.targs:
                                    prox[targ, other_targ] += 1
        return prox

    def calculate_conjestion(self):
        conj = np.zeros((self.n_blocks + 1, self.n_blocks + 1))
        for layer in self.layers:
            for gate in layer:
                if len(gate.targs) > 1:
                    for other_gate in layer:
                        if other_gate is not gate and len(other_gate.targs) > 1:
                            for targ in gate.targs:
                                for other_targ in other_gate.targs:
                                    conj[targ, other_targ] += 1
        return conj

