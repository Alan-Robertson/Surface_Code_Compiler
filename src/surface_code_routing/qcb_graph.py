from surface_code_routing.qcb import Segment, SCPatch
from typing import *
import copy

from surface_code_routing.tikz_utils import tikz_graph_qcb


class GraphNode:
    def __init__(self, segment, *neighbours):
        self.segment = segment
        self.neighbours = set(neighbours)

    def get_adjacent(self):
        return self.neighbours

    def get_symbol(self):
        return self.segment.get_symbol()

    def get_slot(self):
        return self.segment.get_slot()

    def get_state(self):
        return self.segment.get_state()

    def get_patch(self):
        return

    def is_extern(self):
        return self.segment.is_extern()

    def get_segment(self):
        return self.segment    

    def get_slot_name(self):
        return self.segment.get_slot_name()

    def __repr__(self):
        return repr(self.segment.get_symbol())

class QCBGraph:
    def __init__(self, qcb) -> None:
        self.graph = set()
        self.graph_to_segments = dict()
        self.segments_to_graph = dict()

        self.pruned_graph = QCBPrune(qcb.segments)
        self.construct_graph(self.pruned_graph.segments)
        self.qcb = qcb

    def __tikz__(self):
        return tikz_graph_qcb(self)

    def get_qcb(self):
        return self.qcb

    def construct_graph(self, segments):
        for segment in segments:
            graph_node = GraphNode(segment)
            self.graph.add(graph_node)
            self.segments_to_graph[segment] = graph_node
            self.graph_to_segments[graph_node] = segment

        for vertex in self.graph:
            vertex.neighbours = set(map(self.segments_to_graph.__getitem__, vertex.segment.get_adjacent()))

    def __iter__(self):
        return iter(self.graph)


class QCBPrune:
    def __init__(self, segments) -> None:
        # reducing variables
        self.segments: 'Set[Segment]' = segments #copy.deepcopy(segments)
        self.map_to_grid()

    def __tikz__(self):
        return tikz_pruned_qcb(self)

    def map_to_grid(self):
        for segment in self.segments:
            self.prune_invalid_edges(segment)

        fringe = (-1, -1)
        done, fringe = self.try_split_route(fringe)
        while not done:
            done, fringe = self.try_split_route(fringe)

        for segment in self.segments:
            self.prune_edges(segment)


    def try_split_route(self, fringe: Tuple[int, int]) \
            -> Tuple[bool, bool, Tuple[int, int]]:
        
        seg = next((s for s in sorted(self.segments, key=Segment.y_position)
                      if s.y_position() > fringe
                      and s.state.state == SCPatch.ROUTE), None)
        if not seg:
            return True, (-1, -1)
    
        
        if len(seg.left) > 1:
            top_left = min((s for s in seg.left), key=lambda s: s.y_0)
            seg.allocated = False
            (top, bottom), confirm = seg.split(seg.y_0, seg.x_0, top_left.y_1 - seg.y_0 + 1, seg.width)
            confirm(self.segments)
            top.allocated = True
            top.state = SCPatch(SCPatch.ROUTE)
            bottom.allocated = True
            bottom.state = SCPatch(SCPatch.ROUTE)

            return False, fringe
        
        if len(seg.right) > 1:
            top_right = min((s for s in seg.right), key=lambda s: s.y_0)
            seg.allocated = False
            (top, bottom), confirm = seg.split(seg.y_0, seg.x_0, top_right.y_1 - seg.y_0 + 1, seg.width)
            confirm(self.segments)
            top.allocated = True
            top.state = SCPatch(SCPatch.ROUTE)
            bottom.allocated = True
            bottom.state = SCPatch(SCPatch.ROUTE)

            return False, fringe

        if len(seg.above) > 1:
            for s in seg.above:
                self.prune_edges(s)

            left_top = min((s for s in seg.above), key=lambda s: s.x_0)
            seg.allocated = False
            (left, right), confirm = seg.split(seg.y_0, seg.x_0, seg.height, left_top.x_1 - seg.x_0 + 1)
            confirm(self.segments)
            left.allocated = True
            left.state = SCPatch(SCPatch.ROUTE)
            right.allocated = True
            right.state = SCPatch(SCPatch.ROUTE)

            return False, fringe

        if len(seg.below) > 1:
            left_bottom = min((s for s in seg.below), key=lambda s: s.x_0)
            seg.allocated = False
            (left, right), confirm = seg.split(seg.y_0, seg.x_0, seg.height, left_bottom.x_1 - seg.x_0 + 1)
            confirm(self.segments)
            left.allocated = True
            left.state = SCPatch(SCPatch.ROUTE)
            right.allocated = True
            right.state = SCPatch(SCPatch.ROUTE)

            return False, fringe
        return False, seg.y_position()


    def prune_invalid_edges(self, seg: Segment):
        if seg.state.state == SCPatch.REG:
            # Remove all left and right edges
            for label, edge in seg.edges(['left', 'right']).items():
                for block in edge:
                    block._inverse(label).remove(seg)
                edge.clear()
            
            # Remove all blocks which are not ROUTE from above and below
            for label, edge in seg.edges(['above', 'below']).items():
                discarded = set()
                for block in edge:
                    if block.state.state != SCPatch.ROUTE:
                        block._inverse(label).remove(seg)
                        discarded.add(block)
                edge.difference_update(discarded)
        
        elif seg.state.state == SCPatch.IO:
            # Remove all left and right edges, no below edges should exist
            for label, edge in seg.edges(['left', 'right']).items():
                for block in edge:
                    block._inverse(label).remove(seg)
                edge.clear()
            
            # Discard all above edges not to route
            for label, edge in seg.edges(['above']).items():
                discarded = set()
                for block in edge:
                    if block.state.state != SCPatch.ROUTE:
                        block._inverse(label).remove(seg)
                        discarded.add(block)
                edge.difference_update(discarded)
        
        elif seg.state.state == SCPatch.EXTERN:
            # Remove all left, right, above edges
            for label, edge in seg.edges(['left', 'right', 'above']).items():
                for block in edge:
                    block._inverse(label).remove(seg)
                edge.clear()
            
            # Discard all below edges not to route
            for label, edge in seg.edges(['below']).items():
                discarded = set()
                for block in edge:
                    if block.state.state != SCPatch.ROUTE:
                        block._inverse(label).remove(seg)
                        discarded.add(block)
                edge.difference_update(discarded)


    def prune_edges(self, seg: Segment):
        if seg.state.state in {SCPatch.EXTERN, SCPatch.REG} and len(seg.below) > 1:

            route_below = min((s for s in seg.below), key=lambda s: s.x_0)

            for n in seg.below:
                n.above.remove(seg)

            seg.below = {route_below}
            route_below.above.add(seg)
        elif seg.state.state in {SCPatch.IO, SCPatch.REG} and len(seg.above) > 1:

            route_above = min((s for s in seg.above), key=lambda s: s.x_0)

            for n in seg.above:
                n.below.remove(seg)

            seg.above = {route_above}
            route_above.above.add(seg)   

