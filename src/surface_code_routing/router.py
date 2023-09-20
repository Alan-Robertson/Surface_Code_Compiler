from typing import *
from queue import PriorityQueue

from surface_code_routing.qcb import Segment, SCPatch, QCB
from surface_code_routing.circuit_model import PatchGraph, PatchGraphNode 
from surface_code_routing.dag import DAG, DAGNode
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.bind import RouteBind, AddrBind
from surface_code_routing.symbol import ExternSymbol

from surface_code_routing.utils import consume
from surface_code_routing.tikz_utils import tikz_router
from surface_code_routing.instructions import RESET_SYMBOL


class QCBRouter:
    def __init__(self, qcb:QCB, dag:DAG, mapper:QCBMapper, auto_route=True):
        '''
            Initialise the router
        '''
        self.graph = PatchGraph(shape=(qcb.width, qcb.height), environment=self)
        self.dag = dag
        self.qcb = qcb
        self.mapper = mapper

        self.routes = dict()
        self.active_gates = set()

        for segment in self.mapper.map.values():
            for coordinates in segment.range():
                self.graph[coordinates].set_underlying(segment.get_slot())

        self.anc: dict[Any, ANC] = {}    
        
        self.waiting: 'List[DAGNode]' = []
        self.active: 'PriorityQueue[Tuple[int, Any, DAGNode]]' = PriorityQueue()
        self.finished: 'List[DAGNode]' = []

        # This acts as a lock over the externs

        self.resolved: set[DAGNode] = set()

        if auto_route:
            self.layers = self.route()

    def route(self):
        self.active_gates = set()
        waiting = list(map(lambda x: RouteBind(x, self.mapper[x]), self.dag.layers[0]))
        resolved = set()
      
        layers = []
        extern_queue = []
        extern_lock = {i:None for i in self.dag.physical_externs}

        while len(waiting) > 0 or len(self.active_gates) > 0:
            layers.append(list())

            recently_resolved = list()
            if len(self.active_gates) > 0:
                for gate in self.active_gates:
                    gate.cycle()
                    if gate.resolved():
                        recently_resolved.append(gate)

                    # Release an extern allocation
                    if gate.get_symbol() == RESET_SYMBOL:
                        extern_lock[self.dag.externs[gate.get_unary_symbol(())]] = None
                    layers[-1].append(gate)

                if len(recently_resolved) == 0:
                    # No gates resolved, state of the system does not change, fastfoward
                    continue

            self.active_gates = set(filter(lambda x: not x.resolved(), self.active_gates))
            for gate in recently_resolved:
                resolved.add(gate)            
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
            # Initially active gates
            for gate in waiting:
                addresses = self.mapper[gate]

                # Attempt to acquire locks for externs
                externs_acquired = list()
                extern_requirements_satisfied = True
                for argument in gate.get_symbol().io:
                    if argument.is_extern():
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
                if not all(self.attempt_gate(gate, address) for address in addresses):
                    # Not all addresses are currently free, keep waiting
                    continue

                # Attempt to route between the gates
                route_exists = True
                if gate.non_local() or gate.n_ancillae() > 0:
                    route_exists, route_addresses = self.find_route(gate, addresses)
                    addresses = route_addresses

                # Route exists, all nodes are free
                if route_exists:
                    self.routes[AddrBind(gate)] = addresses 
                    self.active_gates.add(gate)
                    for physical_extern, argument in externs_acquired:
                        extern_lock[physical_extern] = argument

            # Update the waiting list 
            waiting = list(filter(lambda x: x not in self.active_gates and x not in resolved, waiting))

            # Not the most elegant approach, could reorder some things
            if len(layers[-1]) == 0:
                layers.pop()
             
        return layers

    def attempt_gate(self, dag_node, address):
        return self.graph[address].lock(dag_node)

    def find_route(self, gate, addresses):
        paths = []
        graph_nodes = list(map(lambda address: self.graph[address], addresses))

        # Find routes
        for start, end in zip(graph_nodes, graph_nodes[1:]):
            path = self.graph.route(start, end, gate)
            if path is not PatchGraph.NO_PATH_FOUND:
                paths += path
            else:
                return False, PatchGraph.NO_PATH_FOUND

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
