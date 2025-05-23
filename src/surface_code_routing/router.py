'''
    Routing object
    Attempts to route the DAG given a QCB layout
'''

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
from surface_code_routing.instructions import RESET_SYMBOL, ROTATION_SYMBOL, HADAMARD_SYMBOL, Rotation, IDLE_SYMBOL

from surface_code_routing.inject_teleportation_routes import TeleportInjector

from surface_code_routing.constants import COULD_NOT_ALLOCATE, COULD_NOT_ROUTE

class QCBRouter:
    '''
        Routing object
        Attempts to route the DAG given a QCB layout
    '''

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
        mapper.router = self

        self.verbose = verbose
        self.routes = dict()
        self.active_gates = set()

        self.anc: dict[Any, ANC] = {}
        self.resolved: set[DAGNode] = set()

        if teleport:
            self.teleport_injector = TeleportInjector(self)
        else:
            self.teleport_injector = None

        self.layers = []
        self.delays = dict()
        self.space_time_volume = 0  # Space-time volume costing
        if auto_route:
            # Fills layers
            self.route()

    def debug_print(self, *args, **kwargs):
        debug_print(*args, debug=self.verbose, **kwargs)

    def route(self):
        '''
            Attempts to route all gates in the DAG
        '''
        self.active_gates = set()
        # Non-factory gates in the first layer are queued
        waiting = list(map(lambda x: RouteBind(x, None), filter(lambda x: not x.is_factory(), self.dag.layers[0])))
        resolved = self.resolved

        quash_flag = 0
        # Externs are not released to the allocator until all gates are ready
        barrier = dict()

        while len(waiting) > 0 or len(self.active_gates) > 0:
            curr_layer = len(self.layers)
            self.layers.append(list())

            fastforward = float('inf') 
        
            recently_resolved = list()
            if len(self.active_gates) > 0:
                for gate in self.active_gates:
                    update = gate.cycle()
                    fastforward = min(fastforward, update)
                    if gate.resolved():
                        recently_resolved.append(gate)

                    # Release an extern allocation
                    if gate.get_symbol() == RESET_SYMBOL:
                        self.mapper.free(gate)
                        
                    self.layers[-1].append(gate)

                if len(recently_resolved) == 0:
                    # No gates resolved, state of the system does not change, fastforward
                    if fastforward > 3:
                        fastforward -= 1
                        self.space_time_volume += self.graph.space_time_volume() * fastforward 
                        for gate in self.active_gates: 
                            gate.cycle(step=fastforward)

                        for _ in range(fastforward):
                            # Copies of the last layer
                            # This is required otherwise later teleported operations and other feed-back mechanisms will fail  
                            self.layers.append([i for i in self.layers[-1]])
 
                    else: # Trivial fast-forwarding
                        self.space_time_volume += self.graph.space_time_volume()
                    continue

            self.active_gates = set(filter(lambda x: not x.resolved(), self.active_gates))
            for gate in recently_resolved:
                resolved.add(gate)
                if gate.rotates():
                    self.rotate(gate, self.mapper[gate])
                # Should only trigger when the final antecedent is resolved

                for antecedent in gate.antecedents():
                    all_resolved = True

                    for predicate_factory in antecedent.predicate_factories:
                        # Yet to be allocated
                        if predicate_factory not in resolved and predicate_factory not in self.active_gates:
                            if all(obj in resolved for obj in predicate_factory.predicates):
                                waiting.append(RouteBind(predicate_factory, None))
                            
                            all_resolved = False
                    if all_resolved is False:
                          continue

                    # Check if predicates have been resolved
                    for predicate in antecedent.predicates:
                        if RouteBind(predicate, None) not in resolved:
                            all_resolved = False
                            break
                    if all_resolved:
                        waiting.append(RouteBind(antecedent, None))

            waiting.sort()
            waiting_clear = list()

            # Initially active gates
            for gate in waiting:
                # Externs
                # Here we're first going to discover the extern gate, then backtrack and find all non-extern dependencies, and see if they've been resolved.
                if len(extern_ante := [i for i in gate.scope if i.is_extern() and not i.is_factory()]) > 0:
                    # Assume the barrier is resolved
                    barrier_resolved = True

                    for ext_symbol in extern_ante:
                        if not barrier_resolved:
                            continue

                        # No barrier for this symbol, create one
                        if ext_symbol not in barrier:
                            barrier[ext_symbol] = tuple()

                            extern_gate = None
                            # Search over extern gate keys
                            # Should replace this with a symbol lookup
                            for i in self.dag.gates:
                                if i.is_extern() and ext_symbol in i.scope:
                                    extern_gate = i
                                    break
                            if extern_gate is None:
                                raise Exception("Missing Extern Gate")

                            non_extern_predicates = []
                            extern_predicates = [extern_gate]

                            # BFS to find non-extern gates
                            while len(extern_predicates) > 0:
                                next_extern_predicates = []
                                for extern_pred in extern_predicates:
                                    for pred in extern_pred.predicates:
                                        if ext_symbol in pred.scope:
                                            next_extern_predicates.append(pred)
                                        else:
                                            non_extern_predicates.append(pred)
                                extern_predicates = next_extern_predicates
                            non_extern_predicates = list(map(lambda x: RouteBind(x, None), non_extern_predicates))
                            barrier[ext_symbol] = non_extern_predicates

                        # Barrier already resolved
                        if len(barrier[ext_symbol]) == 0:
                            continue

                        # Complexity of the barrier scales with O(number of IO in elements)
                        # If the barrier is a tuple, this skips
                        for barrier_gate in barrier[ext_symbol]: # TODO remove elements from the barrier as they are resolved
                            if barrier_gate not in resolved:
                                barrier_resolved = False
                                break

                        if barrier_resolved: # Once the barrier has been resolved all gates are released
                            barrier[ext_symbol] = tuple()

                        else:
                            barrier_resolved = False
                            continue

                    if not barrier_resolved:
                        # Gate caught on barrier, try next gate
                        continue

                # The mapper will also check if it can do an extern allocation
                # The mapper is constrained that if the next call to the mapper is a lock on the same gate that those same addresses should be locked

                addresses = self.mapper[gate]

                # Could not obtain addresses for an extern
                if addresses is COULD_NOT_ALLOCATE:
                    self.track_delay(gate.get_symbol())
                    continue

                # Check that all addresses are free
                if not all(self.probe_address(gate, address) for address in addresses):
                    # Not all addresses are currently free, keep waiting
                    # Track the delayed extern 
                    self.track_delay(gate.get_symbol())
                    continue

                # Attempt to route between the gates
                route_exists = True
                if gate.non_local() or gate.n_ancillae() > 0:
                    route_exists, route_addresses = self.find_route(gate, addresses)
                    addresses = route_addresses
                    if route_exists and curr_layer > 0 and self.teleport_injector is not None:
                        self.teleport_injector(gate, addresses, curr_layer)
                else:
                    addresses = tuple(map(self.graph.__getitem__, addresses))

                # Route exists, all nodes are free
                if route_exists:
                    self.routes[AddrBind(gate)] = addresses
                    self.active_gates.add(gate)

                    # Rollback factories
                    if gate.is_factory():
                        first_free_cycle = self.mapper.first_free_cycle(gate)
                        gate.cycles_completed = min(gate.n_cycles(), curr_layer - first_free_cycle - 1)
                        alap = curr_layer - gate.cycles_completed - 1

                        # Already scheduled on current layer
                        if gate.cycles_completed > 0:
                            for i in range(alap, curr_layer):
                                self.layers[i].append(gate)

                    for patch in addresses:
                        # This patch will be locked for this duration
                        # Storing this information in advance helps with ALAP vs ASAP scheduling
                        patch.last_used = curr_layer + gate.n_cycles() - gate.cycles_completed
                # Route does not exist
                else:
                    self.track_delay(COULD_NOT_ROUTE)

            # Update the waiting list
            waiting = list(filter(lambda x: x not in self.active_gates and x not in resolved and x not in waiting_clear, waiting))

            # Not the most elegant approach, could reorder some things
            # This should never be triggered, but exists as an exit condition
            # if a deadlock occurs in the DAG  
            if len(self.layers[-1]) == 0:
                quash_flag += 1
                if quash_flag > 2:
                    self.debug_print("Layer Quashed")

                elif quash_flag > 10:
                    raise Exception("Deadlock")
                self.layers.pop()
            else:
                self.space_time_volume += self.graph.space_time_volume()
                quash_flag = 0

        # Hard assertion - all gates should be resolved
        # This limits the chance of an accidental early exit
        assert (len(resolved) == len(self.dag.gates))
        return

    def probe_address(self, dag_node, address):
        '''
            Dispatch method for probing an address on the graph
        '''
        return self.graph[address].probe(dag_node)

    def find_route(self, gate, addresses):
        '''
            Attempts to find a route for a gate given a set of addresses
        '''
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

            # Orientation of extern IO nodes can be handled by the internal routing channel
            if start_symbol.is_extern():
                start_orientation = start_node.orientation

            if end_symbol.is_extern():
                end_orientation = end_node.orientation

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
        ancillae = self.graph.ancillae(gate, graph_node, gate.n_ancillae)
        if ancillae is not PatchGraph.NO_PATH_FOUND:
            return [graph_node] + ancillae
        return PatchGraph.NO_PATH_FOUND

    def __tikz__(self):
        return tikz_router(self)

    def track_delay(self, symbol):
        '''
            Tracks extern and routing delays
        '''
        if symbol.is_extern():
            symbol = symbol.predicate

        if symbol in self.delays:
            self.delays[symbol] += 1
        else:
            self.delays[symbol] = 1

    def rotate(self, dag_node, addresses):
        '''
            Dispatch for rotating surface code patches
        '''
        for address in addresses:
            self.graph[address].rotate()
