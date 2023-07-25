from qcb import Segment, SCPatch
from allocator import QCB
from typing import *
from circuit_model import Graph, GraphNode, ANC
from dag2 import DAG
from queue import PriorityQueue
from mapper import RegNode
from utils import log
from mapper import QCBMapper

class QCBRouter:
    def __init__(self, qcb: QCB, dag: DAG, mapper:QCBMapper):
        '''
            Initialise the router
        '''
        self.graph = Graph(shape=(qcb.width, qcb.height))
        self.dag = dag
        self.mapping: 'Dict[Union[qubit_id, msf_type], resource_loc]' = mapper.generate_mapping_dict()
        self.m = mapper.labels

        qcb.reg_to_route(self.mapping.values())

        for segement in qcb.segments:
            for x in range(segement.x_0, segement.x_1 + 1):
                for y in range(segement.y_0, segement.y_1 + 1):
                    self.graph[(x, y)].set_underlying(segement.state.state)
            
        self.waiting: 'List[DAGNode]' = []
        self.active: 'PriorityQueue[Tuple[int, _, DAGNode]]' = PriorityQueue()
        self.finished: 'List[DAGNode]' = []


    def debug(self):
        for i, layer in enumerate(self.dag.layers):
            for inst in layer:
                print(inst, inst.anc)
    
    def route_all(self):

        gates = set(self.dag.gates)
        inits = set(g for g in gates if g.data == 'INIT' and g.layer_num == 0)

        for inst in inits:
            self.route_single(inst.targs[0], inst)
            self.active.put((inst.end, id(inst), inst))
            inst.resolved = True

        while self.waiting or not self.active.empty():
            log(f"{self.waiting=} {self.active.queue=}")
            self.advance()

    def process_waiting(self):
        new_waiting = []
        for inst in self.waiting:
            if len(inst.targs) == 1:
                success = self.route_single(inst.targs[0], inst)
            elif len(inst.targs) == 2:
                # if isinstance(inst.targs[1], int):
                    success = self.route_double(inst.targs[0], inst.targs[1], inst)
                # else:
                #     success = self.route_msf(inst.targs[0], inst.targs[1], inst)
            else:
                raise Exception("invalid in advance:", inst)
            if not success:
                new_waiting.append(inst)
            else:
                self.active.put((inst.end, id(inst), inst))
        self.waiting = new_waiting
            

    def advance(self):
        self.process_waiting()
        completed = self.graph.advance()
        log(f"{completed=}")
        while not self.active.empty() and self.active.queue[0][2].anc in completed:
            inst = self.active.get()[2]
        for anc in completed:
            self.process_completion(anc.inst)
            self.finished.append(anc.inst)
        

    def process_completion(self, inst: DAGNode):
        inst.resolved = True
        for ant in inst.edges_antecede.values():
            if not ant.resolved and all(
                pre.resolved 
                for pre in ant.edges_precede.values() 
                # if not pre.magic_state
                ):
                self.waiting.append(ant)
                ant.resolved = True

        
    def route_single(self, q, inst: DAGNode):
        q_node = self.graph[self.mapping[q]]
        if q_node.in_use():
            return False
        else:
            inst.anc = self.graph.lock([q_node], inst.cycles, inst)
            inst.start = self.graph.time
            inst.end = inst.start + inst.cycles
            return True
            

    
    def route_double(self, q1, q2, inst: DAGNode):
        q1_node = self.graph[self.mapping[q1]]
        q2_node = self.graph[self.mapping[q2]]
        route = self.graph.path(q1_node, q2_node)

        if not route:
            return False
        else:
            assert inst.anc is None
            inst.anc = self.graph.lock(route, inst.cycles, inst)
            inst.start = self.graph.time
            inst.end = inst.start + inst.cycles
            return True

    def route_extern(self, q1, extern, inst):
        
        return self.route_double(q1, extern, inst)
    
        

        q1_node = self.graph[self.mapping[q1]]
        msf_nodes = [(self.graph[pos], seg) for pos, seg in self.mapping[msf].items() if not self.graph[pos].in_use()]
        if not msf_nodes:
            return False
        else:
            # msf priority
            msf_nodes.sort(key=lambda n: abs(q1_node.x - n[0].x) + abs(q1_node.y - n[0].y))
            for node, seg in msf_nodes:
                route = self.graph.path(q1_node, node)
                if route: 
                    dur = max(inst.cycles, seg.state.msf.cycles)
                    assert inst.anc is None
                    inst.anc = self.graph.lock(route, dur, inst)
                    inst.start = self.graph.time
                    inst.end = inst.start + dur
                    return True
            else:
                return False

