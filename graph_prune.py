from qcb import Segment, SCPatch
from typing import *
import copy

class QCBPrune:
    def __init__(self, grid_segments) -> None:
        # reducing variables
        self.grid_segments: 'Set[Segment]' = copy.deepcopy(grid_segments)

    def map_to_grid(self):
        for s in self.grid_segments:
            self.prune_invalid_edges(s)

        fringe = (-1, -1)
        done, fringe = self.try_split_route(fringe)
        while not done:
            done, fringe = self.try_split_route(fringe)

        for s in self.grid_segments:
            self.prune_edges(s)


    def try_split_route(self, fringe: Tuple[int, int]) \
            -> Tuple[bool, bool, Tuple[int, int]]:
        
        seg = next((s for s in sorted(self.grid_segments, key=Segment.y_position)
                      if s.y_position() > fringe
                      and s.state.state == SCPatch.ROUTE), None)
        if not seg:
            return True, (-1, -1)
    
        
        if len(seg.left) > 1:
            top_left = min((s for s in seg.left), key=lambda s: s.y_0)
            seg.allocated = False
            (top, bottom), confirm = seg.split(seg.x_0, seg.y_0, seg.width, top_left.y_1 - seg.y_0 + 1)
            confirm(self.grid_segments)
            top.allocated = True
            top.state = SCPatch(SCPatch.ROUTE)
            bottom.allocated = True
            bottom.state = SCPatch(SCPatch.ROUTE)

            return False, fringe
        
        if len(seg.right) > 1:
            top_right = min((s for s in seg.right), key=lambda s: s.y_0)
            seg.allocated = False
            (top, bottom), confirm = seg.split(seg.x_0, seg.y_0, seg.width, top_right.y_1 - seg.y_0 + 1)
            confirm(self.grid_segments)
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
            (left, right), confirm = seg.split(seg.x_0, seg.y_0, left_top.x_1 - seg.x_0 + 1, seg.height)
            confirm(self.grid_segments)
            left.allocated = True
            left.state = SCPatch(SCPatch.ROUTE)
            right.allocated = True
            right.state = SCPatch(SCPatch.ROUTE)

            return False, fringe

        if len(seg.below) > 1:
            left_bottom = min((s for s in seg.below), key=lambda s: s.x_0)
            seg.allocated = False
            (left, right), confirm = seg.split(seg.x_0, seg.y_0, left_bottom.x_1 - seg.x_0 + 1, seg.height)
            confirm(self.grid_segments)
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

    
        
