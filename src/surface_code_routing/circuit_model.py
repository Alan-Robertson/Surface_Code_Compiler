import numpy as np
import queue
from surface_code_routing.qcb import SCPatch
from typing import *
from surface_code_routing.tikz_utils import tikz_patch_graph
from surface_code_routing.utils import debug_print
from surface_code_routing.bind import AddrBind


class PatchGraphNode():

    INITIAL_LOCK_STATE = AddrBind('INITIAL LOCK STATE')
    Z_ORIENTED = AddrBind('Z') # Smooth edge up
    X_ORIENTED = AddrBind('X') # Rough edge up
    SUGGEST_ROUTE = AddrBind('Suggest Route')
    SUGGEST_ROTATE = AddrBind('Suggest Rotate')

    def __init__(self, graph, i, j, orientation = None, verbose=False):
        self.graph = graph
        self.y = i
        self.x = j
        self.state = SCPatch.ROUTE

        if orientation is None:
            orientation = self.X_ORIENTED
        self.orientation = orientation
        self.lock_state = self.INITIAL_LOCK_STATE

        self.verbose = verbose
    
    def set_underlying(self, state):
        debug_print(self, state, debug=self.verbose)
        self.state = state

    def adjacent(self, gate, **kwargs):
        return self.graph.adjacent(self.y, self.x, gate, **kwargs)

    def __gt__(self, *args):
        return 1

    def __repr__(self):
        return str('[{}, {}]'.format(self.y, self.x))

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
            debug_print('MATCHING ORIETATION', self, debug=self.verbose)
            return self.SUGGEST_ROUTE
        if next(self.adjacent(None, bound=False, vertical=False, probe=False), None) is not None:
            debug_print('HORIZONTAL_ROUTING', self, tuple(self.adjacent(None, bound=False, vertical=False, probe=False)), debug=self.verbose)
            return self.SUGGEST_ROUTE
        debug_print('FALLBACK ROTATE', self, debug=self.verbose)
        return self.SUGGEST_ROTATE

    def rotate(self):
        if self.orientation == self.Z_ORIENTED:
            self.orientation = self.X_ORIENTED
        else:
            self.orientation = self.Z_ORIENTED


class PatchGraph():

    NO_PATH_FOUND = object()

    def __init__(self, shape, mapper, environment, default_orientation = PatchGraphNode.X_ORIENTED, verbose=False):
        self.shape = shape
        self.environment = environment
        self.mapper = mapper
        self.default_orientation = default_orientation

        self.verbose = verbose

        self.graph = np.array([[PatchGraphNode(self, i, j, orientation=self.default_orientation, verbose=False) for j in range(shape[1])] for i in range(shape[0])])

        for segment in self.mapper.map.values():
            for coordinates in segment.range():
                if self.graph[coordinates].state == SCPatch.ROUTE: 
                    self.graph[coordinates].set_underlying(segment.get_slot())
                else:
                    break
        for segment in self.mapper.qcb:
            if segment.get_state() == SCPatch.LOCAL_ROUTE:
                for coordinates in segment.range():
                    self.graph[coordinates].set_underlying(SCPatch.LOCAL_ROUTE)


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
                bound = False
            else:
                vertical = False
                bound = False

        if horizontal and (not bound or self.graph[i, j].state is SCPatch.ROUTE):
            if j + 1 < self.shape[1]:
                if (self.graph[i, j + 1].state is SCPatch.ROUTE):
                    opt.append([i, j + 1])

            if j - 1 >= 0:
                if (self.graph[i, j - 1].state is SCPatch.ROUTE):
                    opt.append([i, j - 1])
          
        if vertical:
            if i + 1 < self.shape[0]:
                if (self.graph[i, j].state is SCPatch.ROUTE) or (self.graph[i + 1, j].state is SCPatch.ROUTE):
                    opt.append([i + 1, j])

            if i - 1 >= 0:
                if (self.graph[i, j].state is SCPatch.ROUTE) or (self.graph[i - 1, j].state is SCPatch.ROUTE):
                    opt.append([i - 1, j]) 
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

        orientation = None
        while not frontier.empty():
            current = frontier.get()[1]
            if current == end:
                break

            # Correct join at the start
            if track_rotations and current == start:
                orientation = start_orientation
            debug_print(current, gate, orientation, current.adjacent(gate, orientation=orientation) , debug=self.verbose)
            for i in current.adjacent(gate, orientation=orientation):
                # Correct join at the end
                if False and track_rotations and i == end:
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
        # Currently supports a single ancillae
        return self.single_ancillae(gate, start)

    def single_ancillae(self, gate, start):
        potential_ancillae = start.adjacent(gate, bound=False)
        for anc in potential_ancillae:
            if anc.lock_state is not gate:
                return [anc]
        return self.NO_PATH_FOUND


    def l_ancillae(self, gate, start):
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
