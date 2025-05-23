"""
    circuit_model
    Provides a graph as a regular lattice of surface code patches
"""

import queue
import numpy as np

from surface_code_routing.qcb import SCPatch
from surface_code_routing.tikz_utils import tikz_patch_graph
from surface_code_routing.utils import debug_print
from surface_code_routing.bind import AddrBind

from surface_code_routing.constants import SINGLE_ANCILLAE, ELBOW_ANCILLAE


class PatchGraphNode:
    """
    Single surface code patch
    """

    INITIAL_LOCK_STATE = AddrBind("INITIAL LOCK STATE")
    Z_ORIENTED = AddrBind("Z")  # Smooth edge up
    X_ORIENTED = AddrBind("X")  # Rough edge up
    SUGGEST_ROUTE = AddrBind("Suggest Route")
    SUGGEST_ROTATE = AddrBind("Suggest Rotate")
    ANCILLAE_STATES = {SCPatch.ROUTE, SCPatch.LOCAL_ROUTE}
    SCOPE_STATES = {SCPatch.REG, SCPatch.IO}


    def __init__(
        self, graph, i: int, j: int, orientation: AddrBind = None, verbose: bool = False
    ):
        self.graph = graph
        self.y = i
        self.x = j
        self.state = SCPatch.ROUTE
        self.last_used = -1

        if orientation is None:
            orientation = self.X_ORIENTED
        self.orientation = orientation
        self.lock_state = self.INITIAL_LOCK_STATE

        self.verbose = verbose

    def set_underlying(self, state):
        """
        Sets the underlying state of the patch
        """
        debug_print(self, state, debug=self.verbose)
        self.state = state

    def adjacent(self, gate, **kwargs) -> set:
        """
        Returns adjacent elements
        """
        return self.graph.adjacent(self.y, self.x, gate, **kwargs)

    def anc_check(self, anc, gate, unique: bool = True):
        """
        Checks if this patch qualifies for use as an ancillae
        """
        if anc.state not in PatchGraphNode.ANCILLAE_STATES or not anc.probe(gate, unique=unique):
            return None
        return anc

    def anc_above(self, gate, unique: bool = True):
        """
        Checks the patch above for ancillae use
        """
        if self.y == 0:
            return None
        anc = self.graph[self.y - 1, self.x]
        return self.anc_check(anc, gate, unique=unique)

    def anc_below(self, gate, unique: bool = True):
        """
        Checks the patch below for ancillae use
        """
        if self.y == self.graph.graph.shape[0] - 1:
            return None
        anc = self.graph[self.y + 1, self.x]
        return self.anc_check(anc, gate, unique=unique)

    def anc_left(self, gate, unique=True):
        """
        Checks the patch to the left for ancillae use
        """
        if self.x == 0:
            return None
        anc = self.graph[self.y, self.x - 1]
        return self.anc_check(anc, gate, unique=unique)

    def anc_right(self, gate, unique=True):
        """
        Checks the patch to the right for ancillae use
        """
        if self.x == self.graph.graph.shape[1] - 1:
            return None
        anc = self.graph[self.y, self.x + 1]
        return self.anc_check(anc, gate, unique=unique)

    def anc_vertical(self, gate):
        """
        Checks above and below for ancillae use
        """
        ancs = self.anc_above(gate), self.anc_below(gate)
        return filter(lambda i: i is not None, ancs)

    def anc_horizontal(self, gate):
        """
        Checks left and right for ancillae use
        """

        ancs = self.anc_left(gate), self.anc_right(gate)
        return filter(lambda i: i is not None, ancs)

    def __gt__(self, *args) -> bool:
        return 1

    def __repr__(self) -> str:
        return str(f"[{self.y}, {self.x}]")

    def __str__(self) -> str:
        return self.__repr__()

    def cost(self):
        """
        Currently unused
        """
        return 1

    def active_gates(self) -> set:
        """
        Wrapper around the graph's active gates
        """
        return self.graph.active_gates()

    def valid_edge(self, other_patch, edge):
        """
        Wrapper around the qcb valid edge call
        """
        return self.state.valid_edge(other_patch.state, edge)

    def probe(self, lock_request, unique=False) -> bool:
        """
        Probes whether this patch is locked or may be locked by the given gate
        """
        if not unique and self.lock_state is lock_request:
            return True
        if unique and self.lock_state is lock_request:
            return False
        # Gate has completed and is no longer active
        if self.lock_state not in self.active_gates():
            return True
        return False

    def lock(self, dag_node):
        """
        Locks the patch for use by a dag node
        """
        if probe := self.probe(dag_node):
            self.lock_state = dag_node
        return probe

    def route_or_rotate(self, orientation) -> AddrBind:
        """
        Determines if this patch should be used for routing or rotating
        """
        if orientation == self.orientation:
            debug_print("MATCHING ORIETATION", self, debug=self.verbose)
            return self.SUGGEST_ROUTE
        if (
            next(self.adjacent(None, bound=False, vertical=False, probe=False), None)
            is not None
        ):
            debug_print(
                "HORIZONTAL_ROUTING",
                self,
                tuple(self.adjacent(None, bound=False, vertical=False, probe=False)),
                debug=self.verbose,
            )

            return self.SUGGEST_ROUTE
        debug_print("FALLBACK ROTATE", self, debug=self.verbose)
        return self.SUGGEST_ROTATE

    def rotate(self):
        """
        Flip patch orientation
        """
        if self.orientation == self.Z_ORIENTED:
            self.orientation = self.X_ORIENTED
        else:
            self.orientation = self.Z_ORIENTED


class PatchGraph:
    """
    Graph of patches
    """

    VOLUME_PROBE = object()
    NO_PATH_FOUND = object()

    def __init__(
        self,
        shape: tuple,
        mapper,
        environment,
        default_orientation=PatchGraphNode.X_ORIENTED,
        verbose: bool = False,
    ):
        self.shape = shape
        self.environment = environment
        self.mapper = mapper
        self.default_orientation = default_orientation

        self.verbose = verbose

        self.graph = np.array(
            [
                [
                    PatchGraphNode(
                        self,
                        i,
                        j,
                        orientation=self.default_orientation,
                        verbose=self.verbose,
                    )
                    for j in range(shape[1])
                ]
                for i in range(shape[0])
            ]
        )

        for segment in self.mapper.map.values():
            for coordinates in segment.range():
                if self.graph[coordinates].state == SCPatch.ROUTE:
                    self.graph[coordinates].set_underlying(segment.get_slot())

        local_patches = []
        for segment in self.mapper.qcb:
            if segment.get_state() == SCPatch.LOCAL_ROUTE:
                for coordinates in segment.range():
                    self.graph[coordinates].set_underlying(SCPatch.LOCAL_ROUTE)
                    local_patches.append(self.graph[coordinates])

        # See if we can't eliminate some local patches
        # TODO BFS this
        expand = True
        while expand:
            expand = False
            uncleared_patches = []
            for local_patch in local_patches:
                if any(
                    p.state is SCPatch.ROUTE
                    for p in local_patch.adjacent(None, bound=False, probe=False)
                ):
                    expand = True
                    local_patch.set_underlying(SCPatch.ROUTE)
                else:
                    uncleared_patches.append(local_patch)
            local_patches = uncleared_patches

    def space_time_volume(self) -> int: 
        '''
            Counts the number of in-use patches
        '''
        volume = 0
        for row in self.graph: 
            for patch in row:
                if patch.state in PatchGraphNode.ANCILLAE_STATES:
                    if not patch.probe(PatchGraph.VOLUME_PROBE):
                        volume += 1
                elif patch.state in PatchGraphNode.SCOPE_STATES:
                    volume += 1
        return volume


    def debug_print(self, *args, **kwargs):
        """
        Debug print wrapper
        """
        debug_print(*args, **kwargs, debug=self.verbose)

    def __getitem__(self, coords) -> PatchGraphNode:
        return self.graph.__getitem__(tuple(coords))

    def active_gates(self) -> set:
        """
        Returns the set of active gates
        """
        return self.environment.active_gates

    def adjacent(
        self,
        i,
        j,
        gate,
        bound=True,  # Not constrained by initial graph node state
        horizontal=True,  # Checks horizonal
        vertical=True,  # Checks vertical
        probe=True,  # Probes for locking
        orientation=None,  # Constrains on orientation
    ):
        """
        Returns adjacent patches subject to constraints
        """
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
                if self.graph[i, j + 1].state is SCPatch.ROUTE:
                    opt.append([i, j + 1])

            if j - 1 >= 0:
                if self.graph[i, j - 1].state is SCPatch.ROUTE:
                    opt.append([i, j - 1])

        if vertical:
            if i + 1 < self.shape[0]:
                if (self.graph[i, j].state is SCPatch.ROUTE) or (
                    self.graph[i + 1, j].state is SCPatch.ROUTE
                ):
                    opt.append([i + 1, j])

            if i - 1 >= 0:
                if (self.graph[i, j].state is SCPatch.ROUTE) or (
                    self.graph[i - 1, j].state is SCPatch.ROUTE
                ):
                    opt.append([i - 1, j])
        for idx in opt:
            # Return without worrying about locks
            if probe is False:
                yield self[tuple(idx)]
            elif self[tuple(idx)].probe(gate):
                yield self[tuple(idx)]

    def flush(self):
        """
            Force unlock all routes
        """
        for grp in self.graph:
            for node in grp:
                if node.state in PatchGraphNode.ANCILLAE_STATES:
                    node.lock_state = PatchGraphNode.INITIAL_LOCK_STATE

    def route(
        self,
        start,  # Start node
        end,  # End node
        gate,  # Gate object
        heuristic=None,  # A* cost heuristic
        track_rotations=True,  # Rotation tracking
        start_orientation=None,  # Orietnation of start node
        end_orientation=None,  # Orientation of end node
    ):
        """
        route
        Attempts to route from start to end using a given gate as a resource lock
        """

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
                debug_print(
                    current,
                    gate,
                    orientation,
                    current.adjacent(gate, orientation=orientation),
                    debug=self.verbose,
                )

            for i in current.adjacent(gate, orientation=orientation):
                # Correct join at the end, currently causes deadlocks
                # if track_rotations and i == end:
                #    if current not in end.adjacent(gate, orientation=end_orientation):
                #        continue
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
            """
            Helper function
            """
            next_end = path[end]
            if next_end is not None:
                return [next_end] + traverse(path, next_end)
            return []

        final_route = traverse(path, end)[::-1] + [end]
        return final_route

    def ancillae(self, gate, start, n_ancillae):
        """
        ancillae
        Attempts to lock ancillae for a gate
        """
        # Currently supports a single ancillae
        if gate.ancillae_type() == SINGLE_ANCILLAE:
            return self.single_ancillae(gate, start)
        if gate.ancillae_type() == ELBOW_ANCILLAE:
            return self.elbow_ancillae(gate, start)
        # This is never reached
        return None

    def single_ancillae(self, gate, start):
        """
        Locks a single ancillae
        """
        potential_ancillae = start.adjacent(gate, bound=False)
        for anc in potential_ancillae:
            if anc.probe(gate) and anc.lock_state is not gate:
                return [anc]
        return self.NO_PATH_FOUND

    def ancillae_elbow_path(self, start, gate, gen_function, transverse_function):
        """
        Locks an elbow ancillae
        """
        ancillae = []
        curr = start
        while curr is not None:
            ancillae.append(curr)
            transverse_ancillae = transverse_function(curr, gate)
            transverse_ancilla = next(iter(transverse_ancillae), None)
            if transverse_ancilla is not None:
                ancillae.append(transverse_ancilla)
                return ancillae
            curr = gen_function(curr, gate)
        return None

    def elbow_ancillae(self, gate, start):
        """
        ## #   # ##
        #  ## ##  #
        """
        # Try local deformation first
        h_anc = next(iter(anc for anc in start.anc_horizontal(gate)), None)
        v_anc = next(iter(anc for anc in start.anc_vertical(gate)), None)

        if h_anc is not None and v_anc is not None:
            return [h_anc, start, v_anc]

        for generative_fn, transverse_fn in zip(
            [
                PatchGraphNode.anc_above,
                PatchGraphNode.anc_below,
                PatchGraphNode.anc_left,
                PatchGraphNode.anc_right,
            ],
            [
                PatchGraphNode.anc_horizontal,
                PatchGraphNode.anc_horizontal,
                PatchGraphNode.anc_vertical,
                PatchGraphNode.anc_vertical,
            ],
        ):
            ancillae = self.ancillae_elbow_path(
                generative_fn(start, gate), gate, generative_fn, transverse_fn
            )
            if ancillae is not None:
                return ancillae

        return self.NO_PATH_FOUND

    def l_ancillae(self, gate, start):
        """
        Gets potential unlocked ancillae
        """
        potential_ancillae = start.adjacent(gate, bound=False)
        for anc in potential_ancillae:
            if anc.lock_state is not gate:
                return [anc]
        return self.NO_PATH_FOUND

    @staticmethod
    def heuristic(a, b, bias=1 + 1e-7):
        """
        Default A* routing heuristic
        """
        return abs(a.x - b.x) + bias * abs(a.y - b.y)

    def __tikz__(self):
        return tikz_patch_graph(self)
