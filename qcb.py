import numpy as np 

class SCPatch():
    def __init__(self):
        self.state = None

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
    seg_clear = {
        'above':lambda a, b: b.below.discard(a),
        'right':lambda a, b: b.left.discard(a),
        'below':lambda a, b: b.above.discard(a),
        'left' :lambda a, b: b.right.discard(a)
        }

    def __init__(self, x_0, y_0, x_1, y_1):
        assert(x_0 <= x_1)
        assert(y_0 <= y_1)
        self.x_0 = x_0
        self.y_0 = y_0
        self.x_1 = x_1
        self.y_1 = y_1

        self.right = set()
        self.left = set()
        self.below = set()
        self.above = set()

        self.allocated = False
        self.test = ""

    def apply_state(self, qcb, state):
        for x in range(self.x_0, x_1):
            for y in range(self.y_0, y_1):
                qcb[x, y].state = state

    def edges(self, label=None):
        if label is None:
            label = self.edge_labels
        edge_dict = {
            'above':self.above,
            'right':self.right,
            'below': self.below,
            'left': self.left}
        return {label:edge_dict[label] for label in self.edge_labels}

    def __repr__(self):
        return f"Segment({[self.x_0, self.y_0, self.x_1, self.y_1]})"

    def __str__(self):
        return self.__repr__()

    def alloc(self, width, height):
        chunks = self.split(self.x_0, self.y_0, width, height)
        chunks[0].allocated = True
        return chunks

    def confirm_split(self, segments):
        for edges in self.edges().values():
            self.link_edges(segments, edges)

        # Avoid multi-deletes
        for label in self.edge_labels:
            for segment in self.edges()[label]:
                self.seg_clear[label](self, segment)
        return segments

    def split(self, x, y, width, height):
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
        return segments

    # link edges between sets seg_a and seg_b
    # (seg_b is seg_a if not specified)
    def link_edges(self, seg_a, seg_b=None):
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
    def horizontal_merge(self, segment):
        # Alignment
        if self.y_0 == segment.y_0 and self.y_1 == segment.y_1:
            if self.x_1 + 1 == segment.x_0: # Self on the left
                left = self
                right = segment
            elif segment.x_1 + 1 == self.x_0: # Self on the right
                left = segment
                right = self
            else: # Cannot merge
                return None

            merged_segment = Segment(left.x_0, left.y_0, right.x_1, right.y_1) # y_0 == y_1 here
            merged_segment.left = left.left
            merged_segment.right = right.right
            merged_segment.above = left.above.union(right.above)
            merged_segment.below = left.below.union(right.below)
        else: # Cannot merge
            return None

        for edge in merged_segment.edges().values():
            for block in edge:
                block.replace(self, merged_segment)
                block.replace(segment, merged_segment)
        return merged_segment


    # Merge two blocks vertically that share a horizontal boundary
    #   a a a  ->  c c c
    #   b b b      c c c
    def vertical_merge(self, segment):
        # Alignment
        if self.x_0 == segment.x_0 and self.x_1 == segment.x_1:
            if self.y_1 + 1 == segment.y_0: # Self above
                above = self
                below = segment
            elif segment.y_1 + 1 == self.y_0: # Self below
                above = segment
                below = self
            else: # Cannot merge
                return None

            merged_segment = Segment(above.x_0, above.y_0, below.x_1, below.y_1)
            merged_segment.left = above.left.union(below.left)
            merged_segment.right = above.right.union(below.right)
            merged_segment.above = above.above
            merged_segment.below = below.below
        else: # Cannot merge
            return None

        for edge in merged_segment.edges().values():
            for block in edge:
                block.replace(self, merged_segment)
                block.replace(segment, merged_segment)
                
        return merged_segment

    # Replace all occurrences of seg_a with seg_b in neighbour sets
    def replace(self, seg_a, seg_b):
        for edge in (self.left, self.right, self.above, self.below):
            if seg_a in edge:
                edge.remove(seg_a)
                edge.add(seg_b)
        return
    
    # Discard all occurrences of elements of others in neighbour sets
    def discard(self, others):
        for edge in (self.left, self.right, self.above, self.below):
            edge.difference_update(others)
        return
    
    # Get nodes that are neighbours in the relation node.<label>(self)
    def inverse(self, label):
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
    def left_merge(self):
        # TODO Check what if no right neighbour for a cell?
        segments = []

        for edge in self.right:
            merged_segment = Segment(self.x_0, max(self.y_0, edge.y_0), edge.x_1, min(self.y_1, edge.y_1))

            if edge.y_0 < self.y_0 <= edge.y_1: # above overlap
                above_segment = Segment(edge.x_0, edge.y_0, edge.x_1, self.y_0 - 1)
                above_segment.above = edge.above
                above_segment.below = set()
                above_segment.right = edge.merge_neighbours(above_segment, ['right'])['right']
                above_segment.left = edge.merge_neighbours(above_segment, ['left'])['left']
                segments.append(above_segment)
            
            if edge.y_0 <= self.y_1 < edge.y_1: # below overlap
                below_segment = Segment(edge.x_0, self.y_1 + 1, edge.x_1, edge.y_1)
                below_segment.above = set()
                below_segment.below = edge.below
                below_segment.right = edge.merge_neighbours(below_segment, ['right'])['right']
                below_segment.left = edge.merge_neighbours(below_segment, ['left'])['left']
                segments.append(below_segment)

            merged_segment.right = edge.merge_neighbours(merged_segment, ['right'])['right']
            merged_segment.left = self.merge_neighbours(merged_segment, ['left'])['left']

            if merged_segment.y_0 == self.y_0:
                merged_segment.above = self.merge_neighbours(merged_segment, ['above'])['above']
            else:
                merged_segment.above = set()

            if merged_segment.y_1 == self.y_1:
                merged_segment.below = self.merge_neighbours(merged_segment, ['below'])['below']
            else:
                merged_segment.below = set()

            segments.append(merged_segment)
        
        old = {self} | self.right
  
        # Remove occurrences of old blocks and add new blocks to make mutual link
        # TODO make not O(n^2)
        for s in segments:
            for label, edge in s.edges().items():
                for block in edge:
                    block.discard(old)
                    block.inverse(label).add(s)

        self.link_edges(segments)

        return segments

    def merge_neighbours(self, other, label=None):
        if label is None:
            label = self.edge_labels
        edge_dict = {
            'above':self.above,
            'right':self.right,
            'below': self.below,
            'left': self.left
        }
        return {
            label: set(e for e in edge_dict[label] if self.seg_adjacent(other, e, label))
        for label in self.edge_labels}



class QCB():
    def __init__(self, height, width, **msfs_templates):
        self.msfs = {i.symbol:i for i in msfs_templates}
        self.height = height
        self.width = width
        self.qcb = np.array([[SCPatch() for _ in range(width)] for _ in range(height)], SCPatch)

        self.open_segments = np.array([[0, 0]])

        self.factories = {}

    def __getitem__(self, x, y):
        return self.qcb[x][y]

    def __repr__(self):
        string = ''
        lookups = {None:'_', "MSF":"@", "Routing":"~", "Data":"#"}
        for i in range(self.height):
            for j in range(self.width):
                block = self.qcb[i][j]
                string += lookups[block.state]
            string += '\n'
        return string

    def build(self, dag):

        allocated_segments = []
        unallocated_segments = [Segment(0, 0, self.width, self.height)]

        for factory in dag.msfs:
            if factory not in self.msfs:
                raise Exception("Magic State Factory {} Not Defined".format(factory))
            if self.place(self.msfs[factory]) == False:
                raise Exception("No legal placement for MSFs")

    def place_factory(self, unallocated_segments, factory):
        for segment in unallocated_segments:
            if segment.y_0 + factory.height < self.height:
                if segment.x_0 + factory.width < self.width:
                    region_clear = True
                    for i in range(segment.x_0, segment.x_0 + width):
                        if self.qcb[i][segment.y_0].state is not None:
                            region_clear = False
                    
                    # Try next region
                    if region_clear:
                        new_segments = segment.split()


            split_segments = segments[0].split(factory.height, factory.width)
            segments.pop(0)
            segments.append(split_segments[1:])
            return split_segments[0]    