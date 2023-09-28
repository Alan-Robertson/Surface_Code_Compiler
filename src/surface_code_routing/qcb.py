import copy
from typing import *

from surface_code_routing.bind import AddrBind
from surface_code_routing.symbol import Symbol

# Purely for namespacing
class SCEdge:
    ABOVE = AddrBind('above')
    BELOW = AddrBind('below')
    RIGHT = AddrBind('right')
    LEFT = AddrBind('left')

    @staticmethod
    def flip(edge):
        match edge:
            case SCEdge.ABOVE:
                return SCEdge.BELOW
            case SCEdge.BELOW:
                return SCEdge.ABOVE
            case SCEdge.RIGHT:
                return SCEdge.LEFT
            case SCEdge.LEFT:
                return SCEdge.RIGHT
        raise Exception("NOT AN EDGE")

# Can't be instantiated with SCEdge
SCEdge.VERTICAL_EDGES = {SCEdge.ABOVE, SCEdge.BELOW}
SCEdge.HORIZONTAL_EDGES = {SCEdge.RIGHT, SCEdge.LEFT}
SCEdge.EDGES = {SCEdge.ABOVE, SCEdge.RIGHT, SCEdge.BELOW, SCEdge.LEFT}

    
class QCB():
    '''
        Closure object
        Contains both a QCB memory layout and a DAG execution description
    '''
    def __init__(self, height, width, operations: 'DAG', io=None):
        self.segments: Set[Segment] = {Segment(0, 0, height - 1, width - 1)}
        self.mappable_segments = set()
        self.operations = operations
        self.cycles = 69 
        self.symbol = operations.get_symbol()
        self.predicate = self.symbol.predicate
        self.prewarm = 0
        self.extern_templates = dict()
        
        self.allocator = None

        if io is None:
            # Placeholder
            #self.io = {key.io_element:index for index, key in enumerate(self.operations.io())}
            self.io = {key:index for key, index in self.operations.io().items()}
        else:
            self.io = io

        self.slack = float('inf')

        self.width = width
        self.height = height
        self.shape = (self.height, self.width)

        self.externs = operations.externs

        self.compiled_layers: list[Bind|ExternBind] = []
        #self.io = self.symbol.io

    # ExternInterface impls
    def n_cycles(self):
        return self.cycles 

    def __iter__(self):
        return self.segments.__iter__()

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

    def is_extern(self):
        return self.symbol.is_extern()

    def __tikz__(self):
        return tikz_utils.tikz_qcb(self)

    def get_slot_name(self):
        return self.symbol.predicate


class SCPatch():
    # Singletons
    EXTERN = Symbol('EXTERN') # Allocated for external dependencies
    REG = Symbol('REGISTER')  # Memory in current scope
    ROUTE = Symbol('ROUTE')   # Routing Lanes
    LOCAL_ROUTE = Symbol('LOCAL') # Non-globally connected routing lanes, do not use for routing
    IO = Symbol('IO') # IO elements
    INTERMEDIARY = Symbol('INTERMEDIARY') # Virtual placements
    NONE = Symbol('NONE') # Unallocated

    def __init__(self, qcb: 'None|QCB' = None):
        if qcb is None:
            self.state = self.NONE
            qcb = self.NONE
        elif qcb is not None and qcb.is_extern(): # not in [self.REG, self.ROUTE, self.IO, self.NONE]:
            self.state = self.EXTERN    
        else:
            self.state = qcb
        self.slot = qcb

    def get_symbol(self):
        if self.state == self.EXTERN:
            return self.slot.get_symbol()
        return self.state.get_symbol()

    def get_slot(self):
        return self.slot

    def get_patch(self):
        return self

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def get_slot_name(self):
        return self.slot.predicate

    def is_extern(self):
        return self.state is SCPatch.EXTERN

    def __eq__(self, other):
        if self.is_extern(): # All externs are equal
            return other.is_extern()
        else:
            return other.state is self.state

    def test_edge_rules(self, edge):
        '''
            Test validity of patch to edge comparison
        '''
        if self.state is SCPatch.ROUTE:
            return True
        if self.state is SCPatch.REG:
            return edge in SCEdge.VERTICAL_EDGES
        if self.state is SCPatch.EXTERN:
            return edge is SCEdge.ABOVE
        return False

    def valid_edge(self, other_patch, edge):
        if not ((self.state is SCPatch.ROUTE) or (other_patch.state is SCPatch.Route)):
            return False

        if self.state is not SCPatch.ROUTE:
            return self.test_rules(edge)
        else:
            return other_patch.test_rules(SCEdge.flip(edge))

    def satisfies(self, other):
        if not self.is_extern():
            return self == other
        return self.slot.satisfies(other)

class Segment():
    edge_labels = [SCEdge.ABOVE, SCEdge.RIGHT, SCEdge.BELOW, SCEdge.LEFT]
    seg_alignments = {
        SCEdge.ABOVE:lambda a, b: a.y_0 - 1 == b.y_1,
        #  b b
        #  a a
        SCEdge.RIGHT:lambda b, a: a.x_0 - 1 == b.x_1,
        #  b a
        #  b a
        SCEdge.BELOW:lambda a, b: a.y_1 + 1 == b.y_0,
        #  a a
        #  b b
        SCEdge.LEFT :lambda b, a: a.x_1 + 1 == b.x_0,
        #  a b
        #  a b
        }
    seg_capture = {
        SCEdge.ABOVE:(lambda a, b: ((a.x_0 <= b.x_0 and a.x_1 >= b.x_0) or (a.x_0 <= b.x_1 and a.x_1 >= b.x_1))),
        #  * a *     OR     * a *
        #    b * *        * * b
        SCEdge.RIGHT:(lambda a, b: ((a.y_0 <= b.y_0 and a.y_1 >= b.y_0) or (a.y_0 <= b.y_1 and a.y_1 >= b.y_1))),
        #  *             *
        #  a b    OR   * *
        #  * *         a b
        #    *         *
        SCEdge.BELOW:(lambda a, b: ((a.x_0 <= b.x_0 and a.x_1 >= b.x_0) or (a.x_0 <= b.x_1 and a.x_1 >= b.x_1))),
        # Same as above
        SCEdge.LEFT :(lambda a, b: ((a.y_0 <= b.y_0 and a.y_1 >= b.y_0) or (a.y_0 <= b.y_1 and a.y_1 >= b.y_1)))
        # Same as right
        }

    seg_adjacent = lambda self, a, b, label: self.seg_alignments[label](a, b) and (
            self.seg_capture[label](a, b) or self.seg_capture[label](b, a)) 

    # Join a.<label> with b reciprocally
    seg_join = {
        SCEdge.ABOVE:lambda a, b: [a.above.add(b), b.below.add(a)], 
        SCEdge.RIGHT:lambda a, b: [a.right.add(b), b.left.add(a)],
        SCEdge.BELOW:lambda a, b: [a.below.add(b), b.above.add(a)],
        SCEdge.LEFT :lambda a, b: [a.left.add(b),  b.right.add(a)]
        } 

    # TODO Pls no properties
    width = property(lambda self: self.x_1 - self.x_0 + 1)
    height = property(lambda self: self.y_1 - self.y_0 + 1)

    def __init__(self, y_0: int, x_0: int, y_1: int, x_1: int):
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

    def allocate(self):
        self.allocated = True

    def deallocate(self):
        self.allocated = False
    
    def get_symbol(self):
        return self.state.get_symbol()

    def set_state(self, state):
        return self.state.set_state(state)

    def get_slot(self):
        return self.state.get_slot()

    def get_state(self):
        return self.state.get_state()

    def get_slot_name(self):
        return self.state.get_slot_name()

    def range(self):
        for x in range(self.x_0, self.x_1 + 1):
            for y in range(self.y_0, self.y_1 + 1):
                yield y, x

    def get_n_slots(self):
        # How many distinct elements are in this patch
        if self.get_state() == SCPatch.EXTERN:
            return 1
        if self.get_state() in {SCPatch.REG, SCPatch.IO}:
            return self.width * self.height
        return 0
        return self.state.get_n_slots()

    # Useful for finding relative ordering of segments
    @classmethod
    def find_max_segment(cls, segments, key=None):
        curr_max = float('-inf')
        curr_seg = None
        for segment in segments:
            if (val := key(segment)) > curr_max:
                curr_seg = segment
                curr_max = val
        return curr_seg

    @classmethod 
    def topmost_segment(cls, segments):
        return cls.find_max_segment(segments, key = lambda x: -x.y_0) 
    @classmethod 
    def bottommost_segment(cls, segments):
        return cls.find_max_segment(segments, key = lambda x: x.y_1) 
    @classmethod 
    def leftmost_segment(cls, segments):
        return cls.find_max_segment(segments, key = lambda x: -x.x_0) 
    @classmethod
    def rightmost_segment(cls, segments):
        return cls.find_max_segment(segments, key = lambda x: x.x_1) 



    def is_extern(self):
        return self.get_symbol().is_extern()

    def get_adjacent(self):
        return self.above | self.below | self.left | self.right

    def __tikz__(self):
        return tikz_utils.tikz_qcb_segment(self)

    def y_position(self):
        return (self.y_0, self.x_0)

    def edges(self, labels=None):
        if labels is None:
            labels = self.edge_labels
        edge_dict = {
            SCEdge.ABOVE:self.above,
            SCEdge.RIGHT:self.right,
            SCEdge.BELOW: self.below,
            SCEdge.LEFT: self.left}
        return {label:edge_dict[label] for label in labels}

    def __repr__(self):
        return f"Segment({[self.y_0, self.x_0, self.y_1, self.x_1]})"

    def __str__(self):
        return self.__repr__()

    def alloc(self, height: int, width: int) -> 'Tuple[None, None]|Tuple[List[Segment], Callable[[],]]':
        if width > self.width or height > self.height:
            return None, None

        confirm, chunks = self.split(self.y_0, self.x_0, height, width)
        if not confirm:
            return None, None
        
        chunks[0].allocated = True

        return confirm, chunks

    def split_top(self, height, max_width=float('inf')):
        width = min(max_width, self.width)
        return self.split(self.y_0, self.x_0, height, width)

    def split_left(self, width, max_height=float('inf')):
        height = min(max_height, self.height)
        return self.split(self.y_0, self.x_0, height, width)

    def split_right(self, width, max_height=float('inf')):
        height = min(max_height, self.height)
        return self.split(self.y_1 - width, self.x_0, height, width)


    def split_top_left(self, height, width):
        return self.split(self.y_0, self.x_0, height, width)

    def split(self, y: int, x: int, height:int, width: int) -> \
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
                segment = Segment(y_start, x_start, y_end, x_end)
                segment.right = self._filter_mutual_neighbours(segment, SCEdge.RIGHT)
                segment.left = self._filter_mutual_neighbours(segment, SCEdge.LEFT)
                segment.above = self._filter_mutual_neighbours(segment, SCEdge.ABOVE)
                segment.below = self._filter_mutual_neighbours(segment, SCEdge.BELOW)
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
        
        return confirm, segments

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

            merged_segment = Segment(left.y_0, left.x_0, right.y_1, right.x_1) # y_0 == y_1 here
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

        return confirm, merged_segment


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

            merged_segment = Segment(above.y_0, above.x_0, below.y_1, below.x_1)
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

        return confirm, merged_segment

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
            SCEdge.LEFT: self.right,
            SCEdge.RIGHT: self.left,
            SCEdge.ABOVE: self.below,
            SCEdge.BELOW: self.above,
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
            return lambda s: None, (self,) 

        splits = {self.y_0, self.y_1 + 1}

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
                    above_seg = Segment(edge.y_0, edge.x_0, self.y_0 - 1, edge.x_1)
                    above_seg.above = edge.above # Fine since edge is destroyed
                    above_seg.below = set()
                    above_seg.right = edge._filter_mutual_neighbours(above_seg, SCEdge.RIGHT)
                    above_seg.left = edge._filter_mutual_neighbours(above_seg, SCEdge.LEFT)
                if self.y_1 < edge.y_1:
                    below_seg = Segment(self.y_1 + 1, edge.x_0, edge.y_1, edge.x_1)
                    below_seg.above = set()
                    below_seg.below = edge.below # Fine since edge is destroyed
                    below_seg.right = edge._filter_mutual_neighbours(below_seg, SCEdge.RIGHT)
                    below_seg.left = edge._filter_mutual_neighbours(below_seg, SCEdge.LEFT)

        splits = sorted(splits)
        segments = []

        # Process all internal blocks
        for y_start, y_end in zip(splits[:-1], map(lambda h: h-1, splits[1:])):
            segment = Segment(y_start, self.x_0, y_end, self.x_1)
            segment.left = self._filter_mutual_neighbours(segment, SCEdge.LEFT)
            segment.right = self._filter_mutual_neighbours(segment, SCEdge.RIGHT)
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
            segment.right = right._filter_mutual_neighbours(segment, SCEdge.RIGHT)
            # We need to discard destroyed segments as they are subsumed into these splits 
            segment.above.update(right._filter_mutual_neighbours(segment, SCEdge.ABOVE).difference(merged_segments))
            segment.below.update(right._filter_mutual_neighbours(segment, SCEdge.BELOW).difference(merged_segments))
        
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

        return confirm, segments

    # # merge cell into below neighbours
    # #   a a a        F C B
    # # d d c b b -> D F C B E
    # #       b b          B E
    def top_merge(self) -> 'Tuple[None, None]|Tuple[List[Segment], Callable[[Set[Segment]],]]':
        
        if self.allocated:
            return None, None
        elif all(map(lambda s:s.allocated, self.below)):
            return lambda s: None, (self,) 

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
                    left_seg = Segment(edge.y_0, edge.x_0, edge.y_1, self.x_0 - 1)
                    left_seg.left = edge.left # Fine since edge is destroyed
                    left_seg.right = set()
                    left_seg.below = edge._filter_mutual_neighbours(left_seg, SCEdge.BELOW)
                    left_seg.above = edge._filter_mutual_neighbours(left_seg, SCEdge.ABOVE)
                if self.x_1 < edge.x_1:
                    right_seg = Segment(edge.y_0, self.x_1 + 1, edge.y_1, edge.x_1)
                    right_seg.left = set()
                    right_seg.right = edge.right # Fine since edge is destroyed
                    right_seg.below = edge._filter_mutual_neighbours(right_seg, SCEdge.BELOW)
                    right_seg.above = edge._filter_mutual_neighbours(right_seg, SCEdge.ABOVE)

        splits = sorted(splits)
        segments = []

        # Process all internal blocks
        for x_start, x_end in zip(splits[:-1], map(lambda x: x-1, splits[1:])):
            segment = Segment(self.y_0, x_start, self.y_1, x_end)
            segment.above = self._filter_mutual_neighbours(segment, SCEdge.ABOVE)
            segment.below = self._filter_mutual_neighbours(segment, SCEdge.BELOW)
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
            segment.below = below._filter_mutual_neighbours(segment, SCEdge.BELOW)
            # We need to discard destroyed segments as they are subsumed into these splits 
            segment.left.update(below._filter_mutual_neighbours(segment, SCEdge.LEFT).difference(merged_segments))
            segment.right.update(below._filter_mutual_neighbours(segment, SCEdge.RIGHT).difference(merged_segments))
        
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

        return confirm, segments
    def _filter_mutual_neighbours(self, other: 'Segment', label: str):
        edge_dict = {
            SCEdge.ABOVE:self.above,
            SCEdge.RIGHT:self.right,
            SCEdge.BELOW: self.below,
            SCEdge.LEFT: self.left
        }
        return set(e for e in edge_dict[label] if self.seg_adjacent(other, e, label))

    def split_contains_below(self, segment, height):
        """
            Returns if an adjacent segment is contained by this segment from above
        """
        if segment not in self.below:
            raise Exception("Segments not adjacent")
        x_0 = max(self.x_0, segment.x_0)
        x_1 = min(self.x_1, segment.x_1)
        if x_0 != segment.x_0 or x_1 != segment.x_1:
            confirm, segments = segment.split(segment.y_0, x_0, height, x_1 - x_0 + 1)
            for seg in segments: # Maximum of 6 segments
                if seg.y_0 == segment.y_0 and seg.x_0 == x_0:
                    return confirm, seg
        return None, None

    def split_contains_right(self, segment, height):
        """
            Returns if an adjacent segment is contained by this segment from above
        """
        if segment not in self.below:
            raise Exception("Segments not adjacent")
        x_0 = max(self.x_0, segment.x_0)
        x_1 = min(self.x_1, segment.x_1)
        if x_0 != segment.x_0 or x_1 != segment.x_1:
            confirm, segments = segment.split(segment.y_0, x_0, height, x_1 - x_0 + 1)
            for seg in segments: # Maximum of 6 segments
                if seg.y_0 == segment.y_0 and seg.x_0 == x_0:
                    return confirm, seg
        return None, None

    def route_edge(self, edge, reverse=True):
        """ 
        Search left edge, True implies bottom to top, False implies top to bottom.
        """
        if len(edge) == 0:
            # Nothing on this edge
            return False, None

        route_segments = []
        for segment in sorted(edge, key=lambda x: x.y_0, reverse=reverse):
            if segment.get_state() is SCPatch.NONE:
                # Unallocated, may be used for routing
                confirm, routing_segments = segment.split_right(1)
                routing_lane = next(seg in routing_segments if seg.x_0 == segment.x_1)
                route_segments.append(segment)
            elif segment.get_state() is SCPatch.ROUTE:
                # Route, we've found the end
                return True, route_segments
            else:
                # Non-routable element found, terminate
                return False, None
        # Reached top of object without finding routing node. Take a leap 
        above_probe = next(iter(segment.above), None)
        if above_probe is not None and above_probe.get_state() is SCPatch.ROUTE:
            # Found a route above, join to it
            return True, route_segments
        # No route found, give up
        return False, None


from surface_code_routing.dag import DAG
from surface_code_routing.bind import Bind, ExternBind
from surface_code_routing import tikz_utils
