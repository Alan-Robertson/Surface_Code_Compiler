from qcb import Segment, SCPatch, QCB
from typing import *
from circuit_model import Graph, GraphNode, ANC
from dag2 import DAG, DAGNode
from queue import PriorityQueue
from utils import log
from mapper2 import QCBMapper
from instructions import INIT_SYMBOL, RESET_SYMBOL
from bind import Bind, ExternBind
from symbol import ExternSymbol

class QCBRouter:
    def __init__(self, qcb: QCB, dag: DAG, mapper:QCBMapper, allocator):
        '''
            Initialise the router
        '''
        self.graph = Graph(shape=(qcb.width, qcb.height))
        self.dag = dag
        self.qcb = qcb
        self.mapping = mapper.generate_mapping_dict()
        # self.m = mapper.labels

        allocator.reg_to_route(self.mapping.values())

        for segment in qcb.segments:
            for x in range(segment.x_0, segment.x_1 + 1):
                for y in range(segment.y_0, segment.y_1 + 1):
                    self.graph[(x, y)].set_underlying(segment.state.state)

        self.anc: dict[Any, ANC] = {}    
        
        self.waiting: 'List[DAGNode]' = []
        self.active: 'PriorityQueue[Tuple[int, Any, DAGNode]]' = PriorityQueue()
        self.finished: 'List[DAGNode]' = []

        # Lifecycle: prewarm -> ready -> active -> (done) -> prewarm
        self.phys_externs: dict[ExternSymbol, list[ExternBind, str]] = {}

        self.resolved: set[DAGNode] = set()

        self.physical_layers: list[list[DAGNode]] = []


    # Probs not working
    def debug(self):
        for i, layer in enumerate(self.dag.layers):
            for inst in layer:
                print(inst, inst.anc)
    
    def preprocess_externs(self, layered_ordering):
        from itertools import chain
        ordering = [g.obj.obj for g in chain.from_iterable(layered_ordering) if g.is_extern()]
        extern_schedule = {phys_extern : [] for phys_extern in self.dag.physical_externs}
        for extern in ordering:
            phys_extern = self.dag.scope[extern.symbol]
            extern_schedule[phys_extern].append(extern)
        return extern_schedule

    def route_all(self):
        self.extern_schedule = self.preprocess_externs(self.qcb.compiled_layers)

        for phys_extern in self.extern_schedule:
            self.phys_externs[phys_extern] = [ExternBind(phys_extern), 'IDLE']

        # gates = set(self.dag.gates)

        inits: list[DAGNode] = [g for g in self.dag.layers[0]]
        self.waiting = inits
        # self.process_waiting()

        while self.waiting or not self.active.empty():
            log(f"{self.waiting=} {self.active.queue=}")
            self.advance()
            
        
        print(self.waiting, self.active.queue)

    def process_waiting(self):
        new_waiting = []
        for inst in self.waiting:
            success = self.route_inst(inst)
            if not success:
                new_waiting.append(inst)
            else:
                self.active.put((self.anc[inst].expiry, id(inst), inst))
        self.waiting = new_waiting
    
    def route_inst(self, inst: DAGNode) -> bool:
        if inst.is_extern():
            success = self.route_extern(inst)
        elif len(inst.symbol) == 1:
            success = self.route_single(inst.symbol[0], inst)
        elif len(inst.symbol) == 2:
            # if isinstance(inst.targs[1], int):
                success = self.route_double(inst.symbol[0], inst.symbol[1], inst)
            # else:
            #     success = self.route_msf(inst.targs[0], inst.targs[1], inst)
        else:
            raise Exception("invalid in advance:", inst)
        return success
        

    def advance(self):
        self.process_waiting()
        time = self.graph.time
        completed = self.graph.advance()
        dtime = self.graph.time - time
        self.physical_layers += [list(self.active.queue)] * (dtime) 
        log(f"{completed=}")

        # TODO discuss
        # from itertools import chain
        # for phys_extern in chain(self.prewarm_externs, self.active_externs):
        #     phys_extern.cycle()
        
        # newly_ready = set()
        # for phys_extern in self.prewarm_externs:
        #     # if phys_extern.
        #     pass

        # end TODO

        while not self.active.empty() and self.anc.get(self.active.queue[0][2], None) in completed:
            inst = self.active.get()[2]
        for anc in completed:
            self.process_completion(anc.inst)
            self.finished.append(anc.inst)
        
    def predicates_resolved(self, inst):
        return all(
                (pre in self.resolved)
                for pre in inst.predicates
                # if not pre.magic_state
                )


    def process_completion(self, inst: DAGNode):
        if inst.symbol == RESET_SYMBOL:
            self.reset_extern(inst)

        self.resolved.add(inst)
        for ant in inst.antecedents:
            # print('debug ant', ant, ant.predicates)
            if ant not in self.resolved and self.predicates_resolved(ant):
                self.waiting.append(ant)
                self.resolved.add(ant)
            # else:
            #     print('not resolved')
            #     for pre in ant.predicates:
            #         if pre not in self.resolved:
            #             print('fail', pre, self.resolved)
    
    def get_coord(self, symbol):
        if symbol in self.mapping:
            return self.mapping[symbol]
        elif symbol.get_symbol() in self.mapping:
            return self.mapping[symbol.get_symbol()]
        elif symbol in self.dag.scope:
            return self.get_coord(self.dag.scope[symbol])
        elif symbol.parent is not symbol:
            offset = symbol.parent(symbol)
            x, y = self.get_coord(symbol.parent)
            # return (x + offset, y)
            return (x, y) # TODO rejig for extern offsets



    def route_single(self, q, inst: DAGNode):
        q_node = self.graph[self.get_coord(q)]
        if q_node.in_use():
            return False
        else:
            self.anc[inst] = self.graph.lock([q_node], inst.n_cycles(), inst)
            inst.start = self.graph.time
            inst.end = inst.start + inst.n_cycles()
            return True
            

    
    def route_double(self, q1, q2, inst: DAGNode):
        q1_node = self.graph[self.get_coord(q1)]
        q2_node = self.graph[self.get_coord(q2)]
        route = self.graph.path(q1_node, q2_node)

        if not route:
            return False
        else:
            assert inst not in self.anc
            self.anc[inst] = self.graph.lock(route, inst.n_cycles(), inst)
            # inst.start = self.graph.time
            # inst.end = inst.start + inst.n_cycles()
            return True

    def reset_extern(self, inst):
        phys_extern_impl = self.dag.scope[inst.symbol[0]]
        phys_extern_binding, phys_extern_state = self.phys_externs[phys_extern_impl]
        assert self.phys_externs[phys_extern_impl][1] == 'ACTIVE'
        self.phys_externs[phys_extern_impl][1] = 'IDLE'

    def route_extern(self, inst):
        if not self.predicates_resolved(inst):
            return False

        phys_extern_impl = self.dag.scope[inst.symbol]
        phys_extern_binding, phys_extern_state = self.phys_externs[phys_extern_impl]
        if phys_extern_state == 'IDLE':
            self.phys_externs[phys_extern_impl][1] = 'ACTIVE'
            dur = phys_extern_binding.n_cycles() - phys_extern_binding.get_cycles_completed()
            self.anc[inst] = self.graph.lock([self.graph[self.get_coord(phys_extern_impl)]], dur, inst)
            # inst.start = self.graph.time
            # inst.end = inst.start + dur
            return True
        return False
        # return self.route_double(q1, extern, inst)
    
    

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
                    assert inst not in self.anc
                    self.anc[inst] = self.graph.lock(route, dur, inst)
                    # inst.start = self.graph.time
                    # inst.end = inst.start + dur
                    return True
            else:
                return False

    def __tikz__(self):
        from test_tikz_helper2 import tikz_header, tikz_footer, new_frame, make_bg, animate_header, animate_footer
        output = animate_header()

        for layer in self.physical_layers:
            output += tikz_header(scale=1.5)
            output += make_bg(self.qcb.segments)
            for _, _, inst in layer:
                nodes = self.anc[inst].nodes
                # offset = 0.03 * inst.start
                offset = 0
                if len(nodes) > 1:
                    x, y = nodes[0].x+0.5+offset, -nodes[0].y-0.5-offset
                    output += f"\\draw ({x}, {y}) "
                    for node in nodes[1:]:
                        x, y = node.x+0.5+offset, -node.y-0.5-offset
                        output += f"-- ({x}, {y}) "
                    output += ";\n"
                x, y = nodes[0].x+0.5+offset, -nodes[0].y-0.5-offset
                output += f"\\node[shape=circle,draw=black] at ({x}, {y}) {{}};\n"
                x, y = nodes[-1].x+0.5+offset, -nodes[-1].y-0.5-offset
                output += f"\\node[shape=circle,draw=black] at ({x}, {y}) {{}};\n"

            output += tikz_footer()
            output += new_frame()
        output += animate_footer()
        return output
