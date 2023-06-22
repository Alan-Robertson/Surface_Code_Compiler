
    # # merge cell into right neighbours
    # #   b b      E E
    # # a b b    B B B
    # # a c   -> C C
    # # a d      F F
    # #   d        D
    # def left_merge(self):
    #     if self.allocated:
    #         return None
    #     segments = []

    #     for edge in self.right:
    #         merged_segment = Segment(self.x_0, max(self.y_0, edge.y_0), edge.x_1, min(self.y_1, edge.y_1))

    #         if edge.y_0 < self.y_0 <= edge.y_1: # above overlap
    #             above_segment = Segment(edge.x_0, edge.y_0, edge.x_1, self.y_0 - 1)
    #             above_segment.above = edge.above
    #             above_segment.below = set()
    #             above_segment.right = edge.merge_neighbours(above_segment, ['right'])['right']
    #             above_segment.left = edge.merge_neighbours(above_segment, ['left'])['left']
    #             segments.append(above_segment)
            
    #         if edge.y_0 <= self.y_1 < edge.y_1: # below overlap
    #             below_segment = Segment(edge.x_0, self.y_1 + 1, edge.x_1, edge.y_1)
    #             below_segment.above = set()
    #             below_segment.below = edge.below
    #             below_segment.right = edge.merge_neighbours(below_segment, ['right'])['right']
    #             below_segment.left = edge.merge_neighbours(below_segment, ['left'])['left']
    #             segments.append(below_segment)

    #         merged_segment.right = edge.merge_neighbours(merged_segment, ['right'])['right']
    #         merged_segment.left = self.merge_neighbours(merged_segment, ['left'])['left']

    #         if merged_segment.y_0 == self.y_0:
    #             merged_segment.above = self.merge_neighbours(merged_segment, ['above'])['above']
    #         else:
    #             merged_segment.above = set()

    #         if merged_segment.y_1 == self.y_1:
    #             merged_segment.below = self.merge_neighbours(merged_segment, ['below'])['below']
    #         else:
    #             merged_segment.below = set()

    #         segments.append(merged_segment)
        
    #     old = {self} | self.right
  
    #     # Remove occurrences of old blocks and add new blocks to make mutual link
    #     # TODO make not O(n^2)
    #     for s in segments:
    #         for label, edge in s.edges().items():
    #             for block in edge:
    #                 block.discard(old)
    #                 block.inverse(label).add(s)

    #     self.link_edges(segments)

    #     return segments
    
    # # merge cell into top neighbours
    # #   a a a        F C B
    # # d d c b b -> D F C B E
    # #       b b          B E
    # def top_merge(self):
    #     segments = []

    #     for edge in self.below:
    #         # merged_segment = Segment(self.x_0, max(self.y_0, edge.y_0), edge.x_1, min(self.y_1, edge.y_1))
    #         merged_segment = Segment(max(self.x_0, edge.x_0), self.y_0, min(self.x_1, edge.x_1), edge.y_1)
            

    #         if edge.x_0 < self.x_0 <= edge.x_1: # left overlap
    #             left_segment = Segment(edge.x_0, edge.y_0, self.x_0 - 1, edge.y_1)
    #             left_segment.left = edge.left
    #             left_segment.right = set()
    #             left_segment.above = edge.merge_neighbours(left_segment, ['above'])['above']
    #             left_segment.below = edge.merge_neighbours(left_segment, ['below'])['below']
    #             segments.append(left_segment)

    #         if edge.x_0 <= self.x_1 < edge.x_1: # right overlap
    #             right_segment = Segment(self.x_1 + 1, edge.y_0, edge.x_1, edge.y_1)
    #             right_segment.left = set()
    #             right_segment.right = edge.right
    #             right_segment.above = edge.merge_neighbours(right_segment, ['above'])['above']
    #             right_segment.below = edge.merge_neighbours(right_segment, ['below'])['below']
    #             segments.append(right_segment)

    #         merged_segment.below = edge.merge_neighbours(merged_segment, ['below'])['below']
    #         merged_segment.above = self.merge_neighbours(merged_segment, ['above'])['above']

    #         if merged_segment.x_0 == self.x_0:
    #             merged_segment.left = self.merge_neighbours(merged_segment, ['left'])['left']
    #         else:
    #             merged_segment.left = set()

    #         if merged_segment.x_1 == self.x_1:
    #             merged_segment.right = self.merge_neighbours(merged_segment, ['right'])['right']
    #         else:
    #             merged_segment.right = set()

    #         segments.append(merged_segment)
        
    #     old = {self} | self.below
  
    #     # Remove occurrences of old blocks and add new blocks to make mutual link
    #     # TODO make not O(n^2)
    #     for s in segments:
    #         for label, edge in s.edges().items():
    #             for block in edge:
    #                 block.discard(old)
    #                 block.inverse(label).add(s)

    #     self.link_edges(segments)

    #     return segments


    # def merge_neighbours(self, other, label=None):
    #     if label is None:
    #         label = self.edge_labels
    #     edge_dict = {
    #         'above':self.above,
    #         'right':self.right,
    #         'below': self.below,
    #         'left': self.left
    #     }
    #     return {
    #         label: set(e for e in edge_dict[label] if self.seg_adjacent(other, e, label))
    #     for label in self.edge_labels}