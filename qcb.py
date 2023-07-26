import numpy as np 
from typing import *
from msf import MSF
from dag2 import DAG
from symbol import Symbol
import copy
from bind import Bind, ExternBind

class QCB():
    '''
        Closure object
        Contains both a QCB memory layout and a DAG execution description
    '''
    def __init__(self, width, height, operations: DAG):
        self.segments: Set[Segment] = {Segment(0, 0, width-1, height-1)}
        self.operations: DAG = operations
        self.cycles = 17
        self.symbol = operations.get_symbol()
        self.prewarm = 0

        self.slack = float('inf')

        self.width = width
        self.height = height
        self.externs = operations.externs

        self.compiled_layers: list[Bind|ExternBind] = []

    # ExternInterface impls
    def n_cycles(self):
        return self.cycles 

    def n_pre_warm_cycles(self):
        return self.prewarm

    def get_symbol(self):
        return self.symbol

    def __repr__(self):
        return f'<impl for {self.symbol.__repr__()}>'

    def __str__(self):
        return self.__repr__()

    def satisfies(self, other):
        return self.symbol.satisfies(other)

    def get_obj(self):
        return self

    def instantiate(self):
        return copy.deepcopy(self)

    def __tikz__(self):
        return test_tikz_helper2.tikz_qcb(self)


class SCPatch():
    # Singletons
    EXTERN = Symbol('EXTERN')
    REG = Symbol('REG')
    ROUTE = Symbol('ROUTE')
    IO = Symbol('IO')
    NONE = None

    def __init__(self, alloc_type: 'None|str|MSF' = None):
        if alloc_type not in [self.REG, self.ROUTE, self.IO, self.NONE]:
            self.state = self.EXTERN
            self.msf = alloc_type
        else:
            self.state = alloc_type

    def get_symbol(self):
        return self.state

class Segment():
    edge_labels = ['above', 'right', 'below', 'left']
    seg_alignments = {
        'above':lambda a, b: a.y_0 - 1 == b.y_1,
        #  b b
        #  a a
        'right':lambda b, a: a.x_0 - 1 == b.x_1,
        #  b a
        #  b a
        'below':lambda a, b: a.y_1 + 1 == b.y_0,
        #  a a
        #  b b
        'left' :lambda b, a: a.x_1 + 1 == b.x_0,
        #  a b
        #  a b
        }
    seg_capture = {
        'above':(lambda a, b: ((a.x_0 <= b.x_0 and a.x_1 >= b.x_0) or (a.x_0 <= b.x_1 and a.x_1 >= b.x_1))),
        #  * a *     OR     * a *
        #    b * *        * * b
        'right':(lambda a, b: ((a.y_0 <= b.y_0 and a.y_1 >= b.y_0) or (a.y_0 <= b.y_1 and a.y_1 >= b.y_1))),
        #  *             *
        #  a b    OR   * *
        #  * *         a b
        #    *         *
        'below':(lambda a, b: ((a.x_0 <= b.x_0 and a.x_1 >= b.x_0) or (a.x_0 <= b.x_1 and a.x_1 >= b.x_1))),
        # Same as above
        'left' :(lambda a, b: ((a.y_0 <= b.y_0 and a.y_1 >= b.y_0) or (a.y_0 <= b.y_1 and a.y_1 >= b.y_1)))
        # Same as right
        }

    seg_adjacent = lambda self, a, b, label: self.seg_alignments[label](a, b) and (
            self.seg_capture[label](a, b) or self.seg_capture[label](b, a)) 

    # Join a.<label> with b reciprocally
    seg_join = {
        'above':lambda a, b: [a.above.add(b), b.below.add(a)], 
        'right':lambda a, b: [a.right.add(b), b.left.add(a)],
        'below':lambda a, b: [a.below.add(b), b.above.add(a)],
        'left' :lambda a, b: [a.left.add(b),  b.right.add(a)]
        } 
    
    # Clear a from a.<label> element
    # seg_clear = {
    #     'above':lambda a, b: b.below.discard(a),
    #     'right':lambda a, b: b.left.discard(a),
    #     'below':lambda a, b: b.above.discard(a),
    #     'left' :lambda a, b: b.right.discard(a)
    #     }
    
    # TODO Pls no properties
    width = property(lambda self: self.x_1 - self.x_0 + 1)
    height = property(lambda self: self.y_1 - self.y_0 + 1)

    def __init__(self, x_0: int, y_0: int, x_1: int, y_1: int):
        assert(x_0 <= x_1)
        assert(y_0 <= y_1)
        self.x_0 = x_0
        self.y_0 = y_0
        self.x_1 = x_1
        self.y_1 = y_1

        self.right: 'Set[Segment]' = set()
        self.left : 'Set[Segment]' = set()
        self.below: 'Set[Segment]' = set()
        self.above: 'Set[Segment]' = set()

        self.allocated = False
        self.state = SCPatch()
        self.debug_name = ""

    def get_symbol(self):
        return self.state.get_symbol()

    def __tikz__(self):
        return test_tikz_helper2.tikz_qcb_segment(self)

    def y_position(self):
        return (self.y_0, self.x_0)

    # def apply_state(self, qcb, state):
    #     for x in range(self.x_0, x_1):
    #         for y in range(self.y_0, y_1):
    #             qcb[x, y].state = state

    def edges(self, labels=None):
        if labels is None:
            labels = self.edge_labels
        edge_dict = {
            'above':self.above,
            'right':self.right,
            'below': self.below,
            'left': self.left}
        return {label:edge_dict[label] for label in labels}

    def __repr__(self):
        return f"Segment({[self.x_0, self.y_0, self.x_1, self.y_1]})"

    def __str__(self):
        return self.__repr__()

    def alloc(self, width: int, height: int) -> 'Tuple[None, None]|Tuple[List[Segment], Callable[[],]]':
        if width > self.width or height > self.height:
            return None, None

        chunks, confirm = self.split(self.x_0, self.y_0, width, height)
        if not confirm:
            return None, None
        
        chunks[0].allocated = True

        return chunks, confirm



    def split(self, x: int, y: int, width: int, height: int) -> \
        'Tuple[None, None]|Tuple[List[Segment], Callable[[Set[Segment]],]]':

        if self.allocated:
            return None, None

        assert(width > 0)
        assert(height > 0)
        assert(x >= self.x_0)
        assert(y >= self.y_0)
        assert(x + width <= self.x_1 + 1)
        assert(y + height <= self.y_1 + 1)
        # Define the possible sets of sub-segments
        positions_x_start = [self.x_0, x, x + width]
        positions_x_end = [x - 1, x + width - 1, self.x_1]
        positions_y_start = [self.y_0, y, y + height]
        positions_y_end = [y - 1, y + height - 1, self.y_1]

        if x == self.x_0:
            positions_x_start.pop(0)
            positions_x_end.pop(0)
        if x + width > self.x_1:
            positions_x_start.pop(-1)
            positions_x_end.pop(-1)

        if y == self.y_0:
            positions_y_start.pop(0)
            positions_y_end.pop(0)
        if y + height > self.y_1:
            positions_y_start.pop(-1)
            positions_y_end.pop(-1)

        segments = []
        for x_start, x_end in zip(positions_x_start, positions_x_end):
            for y_start, y_end in zip(positions_y_start, positions_y_end):
                segment = Segment(x_start, y_start, x_end, y_end)
                segment.right = self._filter_mutual_neighbours(segment, 'right')
                segment.left = self._filter_mutual_neighbours(segment, 'left')
                segment.above = self._filter_mutual_neighbours(segment, 'above')
                segment.below = self._filter_mutual_neighbours(segment, 'below')
                segments.append(segment)

        # Link the edges
        self.link_edges(segments)

        # Place requested segment at the front
        i = 0
        while i is not None and i < len(segments):
            if segments[i].x_0 == x and segments[i].y_0 == y:
                segments.insert(0, segments.pop(i))
                i = None
            else:
                i += 1

        def confirm(segs: 'Set[Segment]'):
            old = {self}

            for s in segments:
                for label, edge in s.edges().items():
                    for block in edge:
                        block._discard(old)
                        block._inverse(label).add(s)

            segs.remove(self)
            segs.update(segments)
        
        return segments, confirm

    # link edges between sets seg_a and seg_b
    # (seg_b is seg_a if not specified)
    def link_edges(self, seg_a: 'Iterable[Segment]', seg_b: 'None|Iterable[Segment]' = None):
        if seg_b is None:
            seg_b = seg_a

        for segment_a in seg_a:
            for segment_b in seg_b:
                for label in self.edge_labels:
                    if self.seg_adjacent(segment_a, segment_b, label):
                        self.seg_join[label](segment_a, segment_b)
        return

    # Merge two blocks horizontally that share a vertical boundary
    #   a b      c c
    #   a b  ->  c c
    #   a b      c c
    def horizontal_merge(self, segment: 'Segment') -> \
        'Tuple[None, None]|Tuple[List[Segment], Callable[[Set[Segment]],]]':

        # Alignment
        if self.allocated or segment.allocated:
            return None, None

        if self.y_0 == segment.y_0 and self.y_1 == segment.y_1:
            if self.x_1 + 1 == segment.x_0: # Self on the left
                left = self
                right = segment
            elif segment.x_1 + 1 == self.x_0: # Self on the right
                left = segment
                right = self
            else: # Cannot merge
                return None, None

            merged_segment = Segment(left.x_0, left.y_0, right.x_1, right.y_1) # y_0 == y_1 here
            merged_segment.left = left.left
            merged_segment.right = right.right
            merged_segment.above = left.above.union(right.above)
            merged_segment.below = left.below.union(right.below)
        else: # Cannot merge
            return None, None

        def confirm(segs: 'Set[Segment]'):
            self._confirm_local_merge(segment, merged_segment)
            segs.remove(self)
            segs.remove(segment)
            segs.add(merged_segment)

        return merged_segment, confirm


    # Merge two blocks vertically that share a horizontal boundary
    #   a a a  ->  c c c
    #   b b b      c c c
    def vertical_merge(self, segment: 'Segment') -> \
        'Tuple[None, None]|Tuple[List[Segment], Callable[[Set[Segment]],]]':

        if self.allocated or segment.allocated:
            return None, None
        # Alignment
        if self.x_0 == segment.x_0 and self.x_1 == segment.x_1:
            if self.y_1 + 1 == segment.y_0: # Self above
                above = self
                below = segment
            elif segment.y_1 + 1 == self.y_0: # Self below
                above = segment
                below = self
            else: # Cannot merge
                return None, None

            merged_segment = Segment(above.x_0, above.y_0, below.x_1, below.y_1)
            merged_segment.left = above.left.union(below.left)
            merged_segment.right = above.right.union(below.right)
            merged_segment.above = above.above
            merged_segment.below = below.below
        else: # Cannot merge
            return None, None
        
        def confirm(segs: 'Set[Segment]'):
            self._confirm_local_merge(segment, merged_segment)
            segs.remove(self)
            segs.remove(segment)
            segs.add(merged_segment)

        return merged_segment, confirm

    def _confirm_local_merge(self, segment: 'Segment', merged_segment: 'Segment'):
        for edge in merged_segment.edges().values():
            for block in edge:
                block.replace(self, merged_segment)
                block.replace(segment, merged_segment)

    # Replace all occurrences of seg_a with seg_b in neighbour sets
    def _replace(self, seg_a: 'Segment', seg_b: 'Segment'):
        for edge in (self.left, self.right, self.above, self.below):
            if seg_a in edge:
                edge.remove(seg_a)
                edge.add(seg_b)
        return
    
    # Discard all occurrences of elements of others in neighbour sets
    def _discard(self, others: 'Set[Segment]'):
        for edge in (self.left, self.right, self.above, self.below):
            edge.difference_update(others)
        return
    
    # Get nodes that are neighbours in the relation node.<label>(self)
    def _inverse(self, label: str):
        r = {
            'left': self.right,
            'right': self.left,
            'above': self.below,
            'below': self.above,
        }
        return r[label]

    # merge cell into right neighbours
    #   b b      E E
    # a b b    B B B
    # a c   -> C C
    # a d      F F
    #   d        D
    def left_merge(self) -> 'Tuple[None, None]|Tuple[List[Segment], Callable[[Set[Segment]],]]':
        
        if self.allocated:
            return None, None
        elif all(map(lambda s:s.allocated, self.right)):
            return [self], lambda s: None

        splits = {self.y_0, self.y_1+1}

        above_seg, below_seg = None, None

        merged_segments = set()
        for edge in self.right:
            if not edge.allocated:
                # Process split y-values
                if self.y_0 < edge.y_0:
                    splits.add(edge.y_0)
                if edge.y_1 + 1 < self.y_1 + 1:
                    splits.add(edge.y_1 + 1)

                # Edge will be guaranteed to be destroyed after global merge
                merged_segments.add(edge)

                if edge.y_0 < self.y_0:
                    above_seg = Segment(edge.x_0, edge.y_0, edge.x_1, self.y_0-1)
                    above_seg.above = edge.above # Fine since edge is destroyed
                    above_seg.below = set()
                    above_seg.right = edge._filter_mutual_neighbours(above_seg, 'right')
                    above_seg.left = edge._filter_mutual_neighbours(above_seg, 'left')
                if self.y_1 < edge.y_1:
                    below_seg = Segment(edge.x_0, self.y_1+1, edge.x_1, edge.y_1)
                    below_seg.above = set()
                    below_seg.below = edge.below # Fine since edge is destroyed
                    below_seg.right = edge._filter_mutual_neighbours(below_seg, 'right')
                    below_seg.left = edge._filter_mutual_neighbours(below_seg, 'left')

        splits = sorted(splits)
        segments = []

        # Process all internal blocks
        for y_start, y_end in zip(splits[:-1], map(lambda h: h-1, splits[1:])):
            segment = Segment(self.x_0, y_start, self.x_1, y_end)
            segment.left = self._filter_mutual_neighbours(segment, 'left')
            segment.right = self._filter_mutual_neighbours(segment, 'right')
            segments.append(segment)

        # Generate above and below for top and bottom segments        
        segments[0].above = self.above
        segments[-1].below = self.below

        # Process above and below for within segments
        for above, below in zip(segments[:-1], segments[1:]):
            above.below.add(below)
            below.above.add(above)
        
        # Process above and below for top and bottom split segments
        # We are guaranteed that there is a first segment if above_seg exists
        # and similarly a last segment for below_seg
        if above_seg:
            segments[0].above.add(above_seg)
            above_seg.below.add(segments[0])
        if below_seg:
            segments[-1].below.add(below_seg)
            below_seg.above.add(segments[-1])

        # Merge each split segment with its right neighbour
        for segment in segments:
            # We know that each split segment either has a bunch of allocated
            # right neighbours, or exactly one unallocated right neighbour
            if all(map(lambda s:s.allocated, segment.right)):
                continue
            right = segment.right.pop()
            segment.x_1 = right.x_1
            segment.right = right._filter_mutual_neighbours(segment, 'right')
            # We need to discard destroyed segments as they are subsumed into these splits 
            segment.above.update(right._filter_mutual_neighbours(segment, 'above').difference(merged_segments))
            segment.below.update(right._filter_mutual_neighbours(segment, 'below').difference(merged_segments))
        
        # Add above and below segments into output list
        if above_seg:
            segments.insert(0, above_seg)
        if below_seg:
            segments.append(below_seg)

        # Unnecessary?
        # self.link_edges(segments)

        def confirm(segs: 'Set[Segment]'):
            old = {self} | merged_segments
    
            # Remove occurrences of old blocks and add new blocks to make mutual link
            # TODO make not O(n^2)
            for s in segments:
                for label, edge in s.edges().items():
                    for block in edge:
                        block._discard(old)
                        block._inverse(label).add(s)
            
            segs.difference_update(old)
            segs.update(segments)

        return segments, confirm  

    # # merge cell into below neighbours
    # #   a a a        F C B
    # # d d c b b -> D F C B E
    # #       b b          B E
    def top_merge(self) -> 'Tuple[None, None]|Tuple[List[Segment], Callable[[Set[Segment]],]]':
        
        if self.allocated:
            return None, None
        elif all(map(lambda s:s.allocated, self.below)):
            return [self], lambda s: None

        splits = {self.x_0, self.x_1+1}

        left_seg, right_seg = None, None

        merged_segments = set()
        for edge in self.below:
            if not edge.allocated:
                # Process split x-values
                if self.x_0 < edge.x_0:
                    splits.add(edge.x_0)
                if edge.x_1 + 1 < self.x_1 + 1:
                    splits.add(edge.x_1 + 1)

                # Edge will be guaranteed to be destroyed after global merge
                merged_segments.add(edge)

                if edge.x_0 < self.x_0:
                    left_seg = Segment(edge.x_0, edge.y_0, self.x_0 - 1, edge.y_1)
                    left_seg.left = edge.left # Fine since edge is destroyed
                    left_seg.right = set()
                    left_seg.below = edge._filter_mutual_neighbours(left_seg, 'below')
                    left_seg.above = edge._filter_mutual_neighbours(left_seg, 'above')
                if self.x_1 < edge.x_1:
                    right_seg = Segment(self.x_1 + 1, edge.y_0, edge.x_1, edge.y_1)
                    right_seg.left = set()
                    right_seg.right = edge.right # Fine since edge is destroyed
                    right_seg.below = edge._filter_mutual_neighbours(right_seg, 'below')
                    right_seg.above = edge._filter_mutual_neighbours(right_seg, 'above')

        splits = sorted(splits)
        segments = []

        # Process all internal blocks
        for x_start, x_end in zip(splits[:-1], map(lambda x: x-1, splits[1:])):
            segment = Segment(x_start, self.y_0, x_end, self.y_1)
            segment.above = self._filter_mutual_neighbours(segment, 'above')
            segment.below = self._filter_mutual_neighbours(segment, 'below')
            segments.append(segment)

        # Generate left and right for left and right segments        
        segments[0].left = self.left
        segments[-1].right = self.right

        # Process above and below for within segments
        for left, right in zip(segments[:-1], segments[1:]):
            left.right.add(right)
            right.left.add(left)
        
        # Process left and right for leftmost and rightmost split segments
        if left_seg:
            segments[0].left.add(left_seg)
            left_seg.right.add(segments[0])
        if right_seg:
            segments[-1].right.add(right_seg)
            right_seg.left.add(segments[-1])

        # Merge each split segment with its below neighbour
        for segment in segments:
            # We know that each split segment either has a bunch of allocated
            # below neighbours, or exactly one unallocated below neighbour
            if all(map(lambda s:s.allocated, segment.below)):
                continue
            below = segment.below.pop()
            segment.y_1 = below.y_1
            segment.below = below._filter_mutual_neighbours(segment, 'below')
            # We need to discard destroyed segments as they are subsumed into these splits 
            segment.left.update(below._filter_mutual_neighbours(segment, 'left').difference(merged_segments))
            segment.right.update(below._filter_mutual_neighbours(segment, 'right').difference(merged_segments))
        
        # Add left and right segments into output list
        if left_seg:
            segments.insert(0, left_seg)
        if right_seg:
            segments.append(right_seg)

        # Unnecessary?
        self.link_edges(segments)

        def confirm(segs: 'Set[Segment]'):
            old = {self} | merged_segments
    
            # Remove occurrences of old blocks and add new blocks to make mutual link
            # TODO make not O(n^2)
            for s in segments:
                for label, edge in s.edges().items():
                    for block in edge:
                        block._discard(old)
                        block._inverse(label).add(s)

            segs.difference_update(old)
            segs.update(segments)

        return segments, confirm  

    def _filter_mutual_neighbours(self, other: 'Segment', label: str):
        edge_dict = {
            'above':self.above,
            'right':self.right,
            'below': self.below,
            'left': self.left
        }
        return set(e for e in edge_dict[label] if self.seg_adjacent(other, e, label))

# class QCB():
#     def __init__(self, height, width, **msfs_templates):
#         self.msfs = {i.symbol:i for i in msfs_templates}
#         self.height = height
#         self.width = width
#         self.qcb = np.array([[SCPatch() for _ in range(width)] for _ in range(height)], SCPatch)

#         self.open_segments = np.array([[0, 0]])

#         self.factories = {}

#     def __getitem__(self, x, y):
#         return self.qcb[x][y]

#     def __repr__(self):
#         string = ''
#         lookups = {None:'_', "MSF":"@", "Routing":"~", "Data":"#"}
#         for i in range(self.height):
#             for j in range(self.width):
#                 block = self.qcb[i][j]
#                 string += lookups[block.state]
#             string += '\n'
#         return string

#     def build(self, dag):

#         allocated_segments = []
#         unallocated_segments = [Segment(0, 0, self.width, self.height)]

#         for factory in dag.msfs:
#             if factory not in self.msfs:
#                 raise Exception("Magic State Factory {} Not Defined".format(factory))
#             if self.place(self.msfs[factory]) == False:
#                 raise Exception("No legal placement for MSFs")

#     def place_factory(self, unallocated_segments, factory):
#         for segment in unallocated_segments:
#             if segment.y_0 + factory.height < self.height:
#                 if segment.x_0 + factory.width < self.width:
#                     region_clear = True
#                     for i in range(segment.x_0, segment.x_0 + width):
#                         if self.qcb[i][segment.y_0].state is not None:
#                             region_clear = False
                    
#                     # Try next region
#                     if region_clear:
#                         new_segments = segment.split()


#             split_segments = segments[0].split(factory.height, factory.width)
#             segments.pop(0)
#             segments.append(split_segments[1:])
#             return split_segments[0]    

import test_tikz_helper2
#from test_tikz_helper2 import tikz_qcb, tikz_qcb_segment
