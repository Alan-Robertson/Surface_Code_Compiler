from typing import *
from queue import PriorityQueue
from surface_code_routing.utils import debug_print

from surface_code_routing.qcb import Segment, SCPatch, QCB
from surface_code_routing.circuit_model import PatchGraph, PatchGraphNode 
from surface_code_routing.dag import DAG, DAGNode
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.bind import RouteBind, AddrBind
from surface_code_routing.symbol import ExternSymbol

from surface_code_routing.utils import consume
from surface_code_routing.tikz_utils import tikz_router
from surface_code_routing.instructions import RESET_SYMBOL, ROTATION_SYMBOL, HADAMARD_SYMBOL, Rotation

from surface_code_routing.inject_teleportation_routes import TeleportInjector

class QCBRouter:
    def __init__(self, qcb:QCB, dag:DAG, mapper:QCBMapper, graph=None, auto_route=True, verbose=False, teleport=True):
        '''
            Initialise the router
        '''
        if graph is None: 
            graph = PatchGraph(shape=(qcb.height, qcb.width), mapper=mapper, environment=self)
        else:
            graph.environment = self
        self.graph = graph

        self.dag = dag
        self.qcb = qcb
        self.mapper = mapper

        self.verbose = verbose
        self.routes = dict()
        self.active_gates = set()

        self.anc: dict[Any, ANC] = {}    
        
        self.waiting: 'List[DAGNode]' = []
        self.active: 'PriorityQueue[Tuple[int, Any, DAGNode]]' = PriorityQueue()
        self.finished: 'List[DAGNode]' = []

        # This acts as a lock over the externs
        self.resolved: set[DAGNode] = set()

        if teleport:
            self.teleport_injector = TeleportInjector(self)

        self.layers = []
        if auto_route:
            # Fills layers
            self.route()

    def route(self):
        self.active_gates = set()
        waiting = list(map(lambda x: RouteBind(x, self.mapper[x]), self.dag.layers[0]))
        resolved = set()
      
        layers = self.layers 
        extern_queue = []
        extern_lock = {i:None for i in self.dag.physical_externs}
        unlocked_externs = len(self.dag.physical_externs)

        while len(waiting) > 0 or len(self.active_gates) > 0:
            curr_layer = len(layers)
            debug_print(waiting, self.active_gates, unlocked_externs, extern_lock, debug=self.verbose) 
            layers.append(list())

            recently_resolved = list()
            if len(self.active_gates) > 0:
                for gate in self.active_gates:
                    gate.cycle()
                    if gate.resolved():
                        recently_resolved.append(gate)

                    # Release an extern allocation
                    if gate.get_symbol() == RESET_SYMBOL:
                        extern_lock[self.dag.externs[gate.get_unary_symbol()]] = None
                        unlocked_externs += 1
                    layers[-1].append(gate)

                if len(recently_resolved) == 0:
                    # No gates resolved, state of the system does not change, fastfoward
                    continue

            self.active_gates = set(filter(lambda x: not x.resolved(), self.active_gates))
            for gate in recently_resolved:
                resolved.add(gate) 
                if gate.rotates():
                    self.rotate(gate, self.mapper[gate])
                # Should only trigger when the final antecedent is resolved
                for antecedent in gate.antecedents():
                    all_resolved = True
                    for predicate in antecedent.predicates:
                        if RouteBind(predicate, None) not in resolved:
                            all_resolved = False
                            break
                    if all_resolved:
                        waiting.append(RouteBind(antecedent, addresses))
            
            waiting.sort()
            waiting_clear = list()
            # Initially active gates
            for gate in waiting:
                addresses = self.mapper[gate]

                # Attempt to acquire locks for externs
                externs_acquired = list()
                extern_requirements_satisfied = True
                for argument in gate.get_symbol().io:
                    if argument.is_extern():

                        # If all externs locked just skip checks and keep going
                        if unlocked_externs == 0:
                            break

                        logical_extern = argument
                        physical_extern = self.dag.externs[argument]

                        # Unlocked, potentially acquire lock
                        lock_state = extern_lock[physical_extern]
                        if lock_state is None:
                            # Unlocked, potentially acquire the lock
                            externs_acquired.append((physical_extern, argument))
                        elif lock_state != argument:
                            # Resource already locked, give up
                            extern_requirements_satisfied = False
                            break
                        # Final case assumes that the lock state is the argument and the lock is already held
                if not extern_requirements_satisfied:
                    continue
                            
                # Check that all addresses are free
                if not all(self.probe_address(gate, address) for address in addresses):
                    # Not all addresses are currently free, keep waiting
                    continue

                # Attempt to route between the gates
                route_exists = True
                if gate.non_local() or gate.n_ancillae() > 0:
                    route_exists, route_addresses = self.find_route(gate, addresses)
                    addresses = route_addresses
                    if route_exists and self.teleport_injector is not None:
                        self.teleport_injector(gate, addresses, curr_layer)
                else:
                    addresses = tuple(map(self.graph.__getitem__, addresses))


                # Route exists, all nodes are free
                if route_exists:
                    self.routes[AddrBind(gate)] = addresses 
                    self.active_gates.add(gate)

                    for patch in addresses:
                        # This patch will be locked for this duration
                        # Storing this information in advance helps with ALAP vs ASAP scheduling
                        patch.last_used = curr_layer + gate.n_cycles()

                    for physical_extern, argument in externs_acquired:
                        unlocked_externs -= 1
                        extern_lock[physical_extern] = argument

            # Update the waiting list 
            waiting = list(filter(lambda x: x not in self.active_gates and x not in resolved and x not in waiting_clear, waiting))

            # Not the most elegant approach, could reorder some things
            if len(layers[-1]) == 0:
                layers.pop()
             
        return layers

    def probe_address(self, dag_node, address):
        return self.graph[address].probe(dag_node)

    def find_route(self, gate, addresses):
        paths = []
        graph_nodes = map(lambda address: self.graph[address], addresses)
        gate_symbol = gate.get_symbol()
        orientations = [PatchGraphNode.Z_ORIENTED, PatchGraphNode.X_ORIENTED]

        # Find routes
        iterable = self.mapper.dag_node_to_symbol_map(gate)
        start = next(iterable)
        start_symbol, start_node = start
        start_node = self.graph[start_node]
        start_orientation = orientations[start_symbol in gate_symbol.x]
        while (end := next(iterable, None)) != None:
            end_symbol, end_node = end
            end_node = self.graph[end_node]
            end_orientation = orientations[end_symbol in gate_symbol.x]
            path = self.graph.route(start_node, end_node, gate, start_orientation=start_orientation, end_orientation=end_orientation)
            if path is not PatchGraph.NO_PATH_FOUND:
                paths += path
            else:
                return False, PatchGraph.NO_PATH_FOUND
            start_symbol = end_symbol
            start_node = end_node
            start_orientation = end_orientation

        # Add any ancillae
        for graph_node in graph_nodes:
            path = self.add_ancillae(gate, graph_node)
            if path is not PatchGraph.NO_PATH_FOUND:
                paths += path
            else:
                return False, PatchGraph.NO_PATH_FOUND

        # Apply locks
        consume(map(lambda x: x.lock(gate), paths))
        return True, paths

    def add_ancillae(self, gate, graph_node):
        '''
            Ancillae are defined here as memory objects that last for
            a single operation and hence are unscoped
        '''
        if gate.n_ancillae() == 0:
            return list()
        # For the moment this only supports single ancillae gates
        ancillae = self.graph.ancillae(gate, graph_node, gate.n_ancillae)
        if ancillae is not PatchGraph.NO_PATH_FOUND:
            return [graph_node] + ancillae
        return PatchGraph.NO_PATH_FOUND 

    def __tikz__(self):
        return tikz_router(self) 

    def rotate(self, dag_node, addresses):
        for address in addresses:
            self.graph[address].rotate()
