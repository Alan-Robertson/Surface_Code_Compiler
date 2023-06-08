
from qcb import Segment, SCPatch
from typing import *



# debug_count = 0
class RegNode():
    def __init__(self, seg: 'Segment|None', children: 'Set[RegNode]|None'=None):
        assert seg or children
        # global debug_count
        # self.debug = debug_count
        # debug_count += 1
        if seg:
            self.seg = seg
            self.slots = seg.width * seg.height
            self.weight = 0
            self.children = {}
            self.visited = {seg}
            self.fringe = {seg}
            self.parent = self
        else:
            self.seg = None
            self.slots = sum(c.slots for c in children)
            self.weight = max(c.weight for c in children)
            self.children = {c: c.slots for c in children}
            self.visited = set.union(*(c.visited for c in children))
            self.fringe = set.union(*(c.fringe for c in children))
            self.parent = self
            for c in children:
                c.parent = self

    def root(self):
        curr = self
        while curr.parent != curr:
            curr = curr.parent
        return curr

    def distribute(self, value):
        if self.children:
            for c in self.children:
                c.distribute(value / len(self.children))
            self.weight += value / len(self.children)
        else:
            self.weight += value

    def get_mapping_neighbours(self) -> Set[Segment]:
        neighbours = set()
        for s in self.fringe:
            neighbours.update(s.above | s.below | s.left | s.right)
        neighbours.difference_update(self.visited)
        return neighbours
    # def __repr__(self):
    #     return f'RegNode({self.debug})'
    # def __str__(self):
    #     return repr(self)
    # def print(self): 
    #     if self.seg:
    #         print(f'Block {str(self.seg)} {self.weight=}')
    #     else:
    #         print(f'Begin {id(self)}')
    #         for c in self.children:
    #             c.print()
    #         print(f'End {id(self)}')




class QCBMapper:
    def __init__(self, grid_segments):
        self.grid_segments = grid_segments


        # mapping tree variables
        self.mapping_forest: Set[RegNode] = set()
        self.mapping: 'Dict[Segment, RegNode]' = {}

    def generate_mapping_tree(self):
        for s in self.grid_segments:
            if s.state.state == SCPatch.REG:
                n = RegNode(seg=s)
                self.mapping_forest.add(n)
                self.mapping[s] = n

        # self.grow_mapping_forest()
        # self.grow_mapping_forest(debug=True)

        # maxiter = 1000
        # i = 0
        # while len(self.mapping) < len(self.grid_segments) and i < maxiter:
        #     self.grow_mapping_forest()
        #     i+=1
        
        # print(len(self.grid_segments))
        # while len(self.mapping) < len(self.grid_segments):
        while len(self.mapping_forest) > 1:
            self.grow_mapping_forest()
        # for s in self.mapping_forest:
        #     s.print()

        return next(iter(self.mapping_forest))
        

    

    def grow_mapping_forest(self, debug=False):
        new_fringes = {r: set() for r in self.mapping_forest}
        merge = {}
        to_process = {}
        for r in self.mapping_forest:
            for seg in r.get_mapping_neighbours():
                if seg not in self.mapping:
                    new_fringes[r].add(seg)
                    to_process[seg] = to_process.get(seg, set()) | {r}
                else:
                    merge[r] = merge.get(r, {r}) | {self.mapping[seg].root()}
    
        
        for seg, rootset in to_process.items():
            self.mapping[seg] = next(iter(rootset))
            for r in rootset:
                r.distribute(1 / len(rootset))
                merge[r] = merge.get(r, {r}) | rootset
        
        if debug:
            print(merge)

        for r, new_fringe in new_fringes.items():
            r.fringe = new_fringe

        assignment = {}
        numbered_groups = {}
        max_assignment = 0

        for r, group in merge.items():
            max_assignment += 1
            assignment[r] = max_assignment
            numbered_groups[max_assignment] = {r}
            for r2 in group:
                if r2 not in assignment:
                    assignment[r2] = max_assignment
                    numbered_groups[max_assignment].add(r2)
                elif assignment[r2] != max_assignment:
                    old_number = assignment[r2]
                    for r3 in numbered_groups[old_number]:
                        assignment[r3] = max_assignment
                        numbered_groups[max_assignment].add(r3)
                    del numbered_groups[old_number]

        for r in self.mapping_forest:
            if r not in assignment:
                max_assignment += 1
                assignment[r] = max_assignment
                numbered_groups[max_assignment] = {r}

        new_forest = set()
        for group in numbered_groups.values():
            if len(group) == 1:
                new_forest.add(group.pop())
            else:
                new_forest.add(RegNode(None, children=group))
        self.mapping_forest = new_forest



            

