import numpy as np
import queue
from qcb import SCPatch
from typing import *
from tikz_utils import tikz_patch_graph 

class PatchGraphNode():

    INITIAL_LOCK_STATE = object()

    def __init__(self, graph, i, j):
        self.graph = graph
        self.x = i
        self.y = j
        self.state = SCPatch.ROUTE
        self.lock_state = self.INITIAL_LOCK_STATE
    
    def set_underlying(self, state):
        self.state = state

    def adjacent(self, gate):
        return self.graph.adjacent(self.x, self.y, gate)

    def __gt__(self, *args):
        return 1

    def __repr__(self):
        return str('[{}, {}]'.format(self.x, self.y))

    def __str__(self):
        return self.__repr__()

    def cost(self):
        return 1

    def active_gates(self):
        return self.graph.active_gates()

    def valid_edge(self, other_patch, edge):
        return self.state.valid_edge(other_patch.state, edge)

    def probe(self, lock_request):
        if self.lock_state is lock_request:
            return True
        # Gate has completed and is no longer active
        if self.lock_state not in self.active_gates():
            return True
        return False 

    def lock(self, dag_node):
        if probe := self.probe(dag_node):
            self.lock_state = dag_node
        return probe

class PatchGraph():

    NO_PATH_FOUND = object()

    def __init__(self, shape, environment):
        self.graph = np.array([[PatchGraphNode(self, j, i) for i in range(shape[1])] for j in range(shape[0])])
        self.shape = shape
        self.environment = environment

    def __getitem__(self, coords):
        return self.graph.__getitem__(tuple(coords))

    def active_gates(self):
        return self.environment.active_gates

    def adjacent(self, i, j, gate):
        opt = []

        if self.graph[i, j].state is SCPatch.ROUTE:
            if i + 1 < self.shape[0]:
                if (self.graph[i + 1, j].state is SCPatch.ROUTE):
                    opt.append([i + 1, j])

            if i - 1 >= 0:
                if (self.graph[i - 1, j].state is SCPatch.ROUTE):
                    opt.append([i - 1, j])
           
        if j + 1 < self.shape[1]:
            opt.append([i, j + 1])

        if j - 1 >= 0:
            opt.append([i, j - 1]) 

        for i in opt:
            if self[tuple(i)].probe(gate):
                yield self[tuple(i)]
        return
   
    def route(self, start, end, gate, heuristic=None):
        
        if heuristic is None:
            heuristic = self.heuristic

        frontier = queue.PriorityQueue()
        frontier.put((0, start))
        
        path = {}
        path_cost = {}
        path[start] = None
        path_cost[start] = 0

        while not frontier.empty():
            current = frontier.get()[1]
            if current == end:
                break
            for i in current.adjacent(gate):
                if (i == end and current != start) or i.state == SCPatch.ROUTE:
                    cost = path_cost[current] + i.cost()
                    if i not in path_cost or cost < path_cost[i]:
                        path_cost[i] = cost
                        frontier.put((cost + heuristic(i, end), i))
                        path[i] = current
        else:
            return self.NO_PATH_FOUND

        def traverse(path, end):
            next_end = path[end]
            if next_end is not None:
                return [next_end] + traverse(path, next_end)
            return []
        final_route = traverse(path, end)[::-1] + [end]
        return final_route 

    def ancillae(self, gate, start, n_ancillae):
        # Currently only supports a single ancillae
        potential_ancillae = start.adjacent(gate)
        for anc in potential_ancillae:
            if anc.lock_state is not gate:
                return [anc]
        return self.NO_PATH_FOUND

    @staticmethod
    def heuristic(a, b):
        return abs(a.x - b.x) + 1.01 * abs(a.y - b.y)

    def __tikz__(self):
        return tikz_patch_graph(self)
