import numpy as np
import copy
from utils import log

class DAGNode():
    def __init__(self, targs, edges=None, data=None, layer_num=None, slack=0, magic_state=None, cycles=1):
        if type(targs) is int:
            targs = [targs]
        if edges is None:
            edges = {}

        if data is None:
            data = ""

        self.targs = targs
        self.data = data
        self.cycles = cycles

        # We will be filling these in once we've got an allocation
        self.start = -1
        self.end = -1
        self.anc = None
        
        self.edges_precede = edges
        self.edges_antecede = {}

        self.non_local = len(self.targs) > 1
        self.slack = slack

        self.resolved = False
        self.magic_state = magic_state

        if layer_num is None:
            layer_num = max((self.edges_precede[i].layer_num + 1 for i in self.edges_precede), default=0)
        self.layer_num = layer_num

    def add_antecedent(self, targ, node):
        self.edges_antecede[targ] = node 

    def __contains__(self, i):
        return self.targs.__contains__(i)

    def __repr__(self):
        return "{}:{}".format(self.data, self.targs)
    def __str__(self):
        return self.__repr__()

    def add_node(self, targs):
        return self
