import numpy as np
import copy

class DAGNode():
    def __init__(self, targs, edges=None, data=None, layer_num=None):
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
        return self.__repr__(self)

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
        return self.gates.__repr__()

    def add_gate(self, targs, msf=False, data=None):
        if type(targs) is int:
            targs = [targs]

        targs = copy.deepcopy(targs) 

        edges = {}
        for t in targs:
            edges[t] = self.last_block[t]
        
        if msf is not False:
            if data not in self.msfs:
                self.msfs[data] = DAGNode(-1, layer_num = 0)
            targs += [self.msf]
        gate = DAGNode(targs, edges, data=data)

        for t in targs:
            if t not in self.msfs: 
                self.last_block[t] = gate 

        self.gates.append(gate)
        self.layer_gate(gate)

    def layer_gate(self, gate):
        if gate.layer_num >= len(self.layers):
            self.layers += [[] for _ in range(gate.layer_num - len(self.layers) + 1)]
            self.layers_conjestion += [0 for _ in range(gate.layer_num - len(self.layers_conjestion) + 1)]
            self.layers_msf += [{} for _ in range(gate.layer_num - len(self.layers_conjestion) + 1)]
        self.layers_conjestion[gate.layer_num] += gate.non_local
        self.layers[gate.layer_num].append(gate)


    def layer(self):
        self.layers = []
        for g in self.gates:
            self.layer_gate(g)

    def depth_parallel(self, n_channels):
        return sum(max(1, layer_conjestion - n_channels) for layer_conjestion in self.layers_conjestion)
        

    def depth_msf(self, **msfs):
        return 0
    
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

