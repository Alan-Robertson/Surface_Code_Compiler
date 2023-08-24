from qcb import Segment, SCPatch, QCB
from typing import *
from circuit_model import PatchGraph, PatchGraphNode 
from dag import DAG, DAGNode
from queue import PriorityQueue
from utils import log
from mapper import QCBMapper
from instructions import INIT_SYMBOL, RESET_SYMBOL
from bind import RouteBind, AddrBind
from symbol import ExternSymbol
from itertools import chain
from utils import consume

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
            for x in range(segment.x_0, segment.x_1 + 1):
                for y in range(segment.y_0, segment.y_1 + 1):
                    self.graph[(x, y)].set_underlying(segment.get_slot())

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
                if gate.non_local():
                    route_exists, route_addresses = self.find_route(gate, addresses)
                    if route_exists:
                        addresses += route_addresses

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
        for start, end in zip(graph_nodes, graph_nodes[1:]):
            path = self.graph.route(start, end, gate)
            if path is not PatchGraph.NO_PATH_FOUND:
                paths += path
            else:
                return False, PatchGraph.NO_PATH_FOUND

        consume(map(lambda x: x.lock(gate), paths))
        return True, paths
