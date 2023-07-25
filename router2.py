from qcb import Segment, SCPatch, QCB
from typing import *
from circuit_model import Graph, GraphNode, ANC
from dag2 import DAG, DAGNode
from queue import PriorityQueue
from mapper import RegNode
from utils import log
from mapper import QCBMapper
from instructions import INIT_SYMBOL
from extern_interface import ExternInterface
from bind import ExternBind

class QCBRouter:
    def __init__(self, qcb: QCB, dag: DAG, mapper:QCBMapper, allocator):
        '''
            Initialise the router
        '''
        self.graph = Graph(shape=(qcb.width, qcb.height))
        self.dag = dag
        self.mapping: 'Dict[Union[qubit_id, msf_type], resource_loc]' = mapper.generate_mapping_dict()
        self.m = mapper.labels

        allocator.reg_to_route(self.mapping.values())

        for segement in qcb.segments:
            for x in range(segement.x_0, segement.x_1 + 1):
                for y in range(segement.y_0, segement.y_1 + 1):
                    self.graph[(x, y)].set_underlying(segement.state.state)
            
        self.waiting: 'List[DAGNode]' = []
        self.active: 'PriorityQueue[Tuple[int, _, DAGNode]]' = PriorityQueue()
        self.finished: 'List[DAGNode]' = []

        # Lifecycle: prewarm -> ready -> active -> (done) -> prewarm
        self.phys_externs: list[tuple[ExternBind, str]]

        self.resolved: set[DAGNode] = set()


    def debug(self):
        for i, layer in enumerate(self.dag.layers):
            for inst in layer:
                print(inst, inst.anc)
    
    def preprocess_externs(self, layered_ordering):
        from itertools import chain
        # TODO definitely refactor this
        ordering = [g.obj.obj for g in chain.from_iterable(layered_ordering) if g.is_extern()]
        extern_schedule = {phys_extern : [] for phys_extern in self.dag.physical_externs}
        for extern in ordering:
            phys_extern = self.dag.scope[extern.symbol]
            extern_schedule[phys_extern].append(extern)
        return extern_schedule

    def route_all(self):
        # TODO refactor this after discussion
        extern_schedule = self.preprocess_externs(self.dag.compiled_layers)

        for phys_extern in extern_schedule:
            self.prewarm_externs.append(ExternBind(phys_extern))
        # Strategy: loop over extern schedule; then schedule each logical extern on 
        # the specified physical extern according to schedule
        # Add dagnode to resolved and recheck resolved so that 
        # gates that interact with externs get added to active properly

        # end TODO


        gates = set(self.dag.gates)
        inits: set[DAGNode] = set(g for g in self.dag.layers[0] if g.symbol == INIT_SYMBOL)

        for inst in inits:
            self.route_single(next(iter(inst.scope.keys())), inst)
            self.active.put((inst.end, id(inst), inst))
            inst.resolved = True

        while self.waiting or not self.active.empty():
            log(f"{self.waiting=} {self.active.queue=}")
            self.advance()
        
        print(self.waiting, self.active.queue)

    def process_waiting(self):
        new_waiting = []
        for inst in self.waiting:
            if len(inst.symbol) == 1:
                success = self.route_single(inst.symbol[0], inst)
            elif len(inst.symbol) == 2:
                # if isinstance(inst.targs[1], int):
                    success = self.route_double(inst.symbol[0], inst.symbol[1], inst)
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

        # TODO discuss
        from itertools import chain
        for phys_extern in chain(self.prewarm_externs, self.active_externs):
            phys_extern.cycle()
        
        newly_ready = set()
        for phys_extern in self.prewarm_externs:
            if phys_extern.

        # end TODO

        while not self.active.empty() and self.active.queue[0][2].anc in completed:
            inst = self.active.get()[2]
        for anc in completed:
            self.process_completion(anc.inst)
            self.finished.append(anc.inst)
        

    def process_completion(self, inst: DAGNode):
        self.resolved.add(inst)
        for ant in inst.antecedents:
            # print('debug ant', ant, ant.predicates)
            if ant not in self.resolved and all(
                (pre in self.resolved)
                for pre in ant.predicates
                # if not pre.magic_state
                ):
                self.waiting.append(ant)
                self.resolved.add(ant)
            # else:
            #     print('not resolved')
            #     for pre in ant.predicates:
            #         if pre not in self.resolved:
            #             print('fail', pre, self.resolved)
        
    def route_single(self, q, inst: DAGNode):
        q_node = self.graph[self.mapping[q]]
        if q_node.in_use():
            return False
        else:
            inst.anc = self.graph.lock([q_node], inst.n_cycles(), inst)
            inst.start = self.graph.time
            inst.end = inst.start + inst.n_cycles()
            return True
            

    
    def route_double(self, q1, q2, inst: DAGNode):
        q1_node = self.graph[self.mapping[q1]]
        q2_node = self.graph[self.mapping[q2]]
        route = self.graph.path(q1_node, q2_node)

        if not route:
            return False
        else:
            assert inst.anc is None
            inst.anc = self.graph.lock(route, inst.n_cycles(), inst)
            inst.start = self.graph.time
            inst.end = inst.start + inst.n_cycles()
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

