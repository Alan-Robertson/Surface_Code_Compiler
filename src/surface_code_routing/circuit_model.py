import numpy as np
import queue
from surface_code_routing.qcb import SCPatch
from typing import *
from surface_code_routing.tikz_utils import tikz_patch_graph 


class PatchGraphNode():

    INITIAL_LOCK_STATE = object()
    Z_ORIENTED = object() # Smooth edge up
    X_ORIENTED = object() # Rough edge up
    SUGGEST_ROUTE = object()
    SUGGEST_HADAMARD = object()

    def __init__(self, graph, i, j, orientation = None):
        self.graph = graph
        self.x = i
        self.y = j
        self.state = SCPatch.ROUTE

        if orientation is None:
            orientation = self.X_ORIENTED
        self.orientation = orientation
        self.lock_state = self.INITIAL_LOCK_STATE
    
    def set_underlying(self, state):
        self.state = state

    def adjacent(self, gate, **kwargs):
        return self.graph.adjacent(self.x, self.y, gate, **kwargs)

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

    def route_or_hadamard(self, orientation):
        if orientation == self.orientation:
            return self.SUGGEST_ROUTE
        if next(self.adjacent(None, bound=False, vertical=False, probe=False), None) is not None:
            return self.SUGGEST_ROUTE
        return self.SUGGEST_HADAMARD

    def rotate(self):
        if self.orientation == self.Z_ORIENTED:
            self.orientation = self.X_ORIENTED
        else:
            self.orientation = self.Z_ORIENTED


class PatchGraph():

    NO_PATH_FOUND = object()

    def __init__(self, shape, mapper, environment, default_orientation = PatchGraphNode.X_ORIENTED ):
        self.shape = shape
        self.environment = environment
        self.mapper = mapper
        self.default_orientation = default_orientation

        self.graph = np.array([[PatchGraphNode(self, j, i, orientation=self.default_orientation) for i in range(shape[1])] for j in range(shape[0])])

        for segment in self.mapper.map.values():
            for coordinates in segment.range():
                self.graph[coordinates].set_underlying(segment.get_slot())


    def __getitem__(self, coords):
        return self.graph.__getitem__(tuple(coords))

    def active_gates(self):
        return self.environment.active_gates

    def adjacent(self, i, j, gate, 
                 bound=True, # Not constrained by initial graph node state
                 horizontal=True, # Checks horizonal
                 vertical=True, # Checks vertical
                 probe=True, # Probes for locking 
                 orientation=None # Constrains on orientation
                 ):
        opt = []

        if orientation is not None:
            if orientation == self.graph[i, j].orientation:
                horizontal = False
            else:
                vertical = False

        if horizontal and (not bound or self.graph[i, j].state is SCPatch.ROUTE):
            if i + 1 < self.shape[0]:
                if (self.graph[i + 1, j].state is SCPatch.ROUTE):
                    opt.append([i + 1, j])

            if i - 1 >= 0:
                if (self.graph[i - 1, j].state is SCPatch.ROUTE):
                    opt.append([i - 1, j])
          
        if vertical:
            if j + 1 < self.shape[1]:
                opt.append([i, j + 1])

            if j - 1 >= 0:
                opt.append([i, j - 1]) 

        for i in opt:
            # Return without worrying about locks
            if probe is False:
                yield self[tuple(i)]
            elif self[tuple(i)].probe(gate):
                yield self[tuple(i)]
        return
   
    def route(self, start, end, gate, heuristic=None, track_rotations=True, start_orientation=None, end_orientation=None):
        
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
            if track_rotations and current == start:
                orientation = start_orientation
            for i in current.adjacent(gate, orientation=orientation):
                if track_rotations and i == end:
                    if current not in end.adjacent(gate, orientation=end_orientation):
                        continue
                if (i == end and current != start) or i.state == SCPatch.ROUTE:
                    cost = path_cost[current] + i.cost()
                    if i not in path_cost or cost < path_cost[i]:
                        path_cost[i] = cost
                        frontier.put((cost + heuristic(i, end), i))
                        path[i] = current
            if current == start:
                orientation = None
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
        potential_ancillae = start.adjacent(gate, bound=False)
        for anc in potential_ancillae:
            if anc.lock_state is not gate:
                return [anc]
        return self.NO_PATH_FOUND

    @staticmethod
    def heuristic(a, b):
        return abs(a.x - b.x) + 1.01 * abs(a.y - b.y)

    def __tikz__(self):
        return tikz_patch_graph(self)
