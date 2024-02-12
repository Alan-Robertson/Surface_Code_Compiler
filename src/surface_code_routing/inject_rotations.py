from typing import *
from queue import PriorityQueue

from surface_code_routing.utils import debug_print

from surface_code_routing.qcb import Segment, SCPatch, QCB
from surface_code_routing.circuit_model import PatchGraph, PatchGraphNode 
from surface_code_routing.dag import DAG, DAGNode
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.symbol import ExternSymbol

from surface_code_routing.utils import consume
from surface_code_routing.tikz_utils import tikz_router
from surface_code_routing.instructions import ROTATION_SYMBOL, HADAMARD_SYMBOL, Rotation, INIT_SYMBOL


class RotationInjector():
    def __init__(self, dag, mapper, qcb, graph=None, autorun=True, verbose=False):

        self.dag = dag
        self.mapper = mapper
        self.qcb = qcb
        self.verbose = verbose

        if graph is None: 
            graph = PatchGraph(shape=qcb.shape, mapper=mapper, environment=None)
        self.graph = graph
        if autorun:
            self.inject_rotations()
            self.reset_rotations()
        
        # Delete local routes
        for segment in qcb.segments:
            if segment.get_state() is SCPatch.LOCAL_ROUTE:
                segment.set_state(SCPatch.ROUTE)

    def reset_rotations(self):
        for i in range(self.qcb.width):
            for j in range(self.qcb.height):
                self.graph[j, i].orientation = self.graph.default_orientation

    def inject_rotations(self):
        index = 0
        while index < len(self.dag.gates):
            gate = self.dag.gates[index]
            if gate.non_local():

                rotation_targs = self.check_rotations(gate) 
                if len(rotation_targs) > 0:
                    # Need to rotate some elements before gate can be performed
                    index += self.inject_rotation_gate(gate, rotation_targs)
                    continue
            
            if gate.rotates():
                addresses = self.mapper(gate)
                self.rotate(gate, addresses)
            index += 1


    def check_rotations(self, dag_node):
        rotation_targs = list()
        dag_symbol = dag_node.get_symbol()
        for argument in dag_symbol.z:
            if argument.is_extern():
                continue
            address, rollback = self.mapper.dag_symbol_to_coordinates(argument)
            graph_node = self.graph[address]
            if graph_node.route_or_rotate(graph_node.Z_ORIENTED) is graph_node.SUGGEST_ROTATE:
                debug_print(dag_node, graph_node, graph_node.orientation, 'ROTATE', debug=self.verbose)
                rotation_targs.append(argument)
            else:
                debug_print(dag_node, graph_node, graph_node.orientation, 'ROUTE', debug=self.verbose)
        for argument in dag_symbol.x:
            if argument.is_extern():
                continue
            address, rollback = self.mapper.dag_symbol_to_coordinates(argument)
            graph_node = self.graph[address]
            if graph_node.route_or_rotate(graph_node.X_ORIENTED) is graph_node.SUGGEST_ROTATE:
                debug_print(dag_node, graph_node, graph_node.orientation, 'ROTATE', debug=self.verbose)
                rotation_targs.append(argument)
            else:
                debug_print(dag_node, graph_node, graph_node.orientation, 'ROUTE', debug=self.verbose)

        return rotation_targs
                
    def inject_rotation_gate(self, dag_node, symbols):
        injected_gates = []
        index_tracker = 0
        for symbol in symbols:
            rotation_gate = None
            dag_index = self.dag.gates.index(dag_node)
            predicate_gate = dag_node.back_edges[symbol]

            if predicate_gate.symbol == INIT_SYMBOL:
                predicate_gate.rotate()
                rotation_gate = predicate_gate
            else:
                rotation_gate = Rotation(symbol).gates[0]
            
                predicate_gate.forward_edges[symbol] = rotation_gate
                predicate_gate.antecedents.add(rotation_gate)
                # May have multiple symbols pointing to the same gate, only a subset of which rotate
                if dag_node not in predicate_gate.forward_edges.values() and dag_node in predicate_gate.antecedents:
                    predicate_gate.antecedents.remove(dag_node)

                dag_node.back_edges[symbol] = rotation_gate
                dag_node.predicates.add(rotation_gate)
                if predicate_gate not in dag_node.back_edges.values() and predicate_gate in dag_node.predicates:
                    dag_node.predicates.remove(predicate_gate)

                rotation_gate.forward_edges[symbol] = dag_node
                rotation_gate.back_edges[symbol] = predicate_gate
                rotation_gate.predicates.add(predicate_gate)
                rotation_gate.antecedents.add(dag_node)

                injected_gates.append(rotation_gate)
                self.dag.gates.insert(dag_index, rotation_gate)
                index_tracker += 1 
        
            addresses = self.mapper(rotation_gate)
            self.rotate(rotation_gate, addresses)

        return index_tracker 

    def rotate(self, dag_node, addresses):
        if dag_node.rotates():
            for address in addresses:
                self.graph[address].rotate()

