from qcb import Segment, SCPatch, QCB
from typing import *
from circuit_model import PatchGraph, PatchGraphNode 
from dag import DAG, DAGNode
from queue import PriorityQueue
from mapper import QCBMapper
from instructions import INIT_SYMBOL, RESET_SYMBOL
from bind import RouteBind, AddrBind
from symbol import ExternSymbol
from itertools import chain
from utils import consume

from tikz_utils import tikz_router

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

        for segment in self.mapper.map.values():#qcb.segments:
            for coordinates in segment.range():
                self.graph[coordinates].set_underlying(segment.get_slot())

        self.anc: dict[Any, ANC] = {}    
        
        self.waiting: 'List[DAGNode]' = []
        self.active: 'PriorityQueue[Tuple[int, Any, DAGNode]]' = PriorityQueue()
        self.finished: 'List[DAGNode]' = []

        # Lifecycle: prewarm -> ready -> active -> (done) -> prewarm
        self.phys_externs: dict[ExternSymbol, list[ExternBind, str]] = {}

        self.resolved: set[DAGNode] = set()

        if auto_route:
            self.layers = self.route()

    def route(self):
        self.active_gates = set()
        waiting = list(map(lambda x: RouteBind(x, self.mapper[x]), self.dag.layers[0]))
        resolved = set()
      
        layers = []

        while len(waiting) > 0 or len(self.active_gates) > 0:
            layers.append(list())
            # Initially active gates
            for gate in waiting:
                addresses = self.mapper[gate]
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

            recently_resolved = list(filter(lambda x: x.resolved(), self.active_gates))
            self.active_gates = set(filter(lambda x: not x.resolved(), self.active_gates))
            waiting = list(filter(lambda x: x not in self.active_gates, waiting))
    
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
                   
            for gate in self.active_gates:
                gate.cycle()
                layers[-1].append(gate)

            # Not the most elegant approach, could reorder some things
            if len(layers[-1]) == 0:
                layers.pop()

            waiting.sort()
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
