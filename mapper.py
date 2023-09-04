import math as maths
from qcb import SCPatch
from tree_slots import TreeSlots
from tikz_utils import tikz_mapper

class QCBMapper():

    def __init__(self, dag, mapping_tree):
        self.dag = dag
        self.map = {symbol:None for symbol in dag.lookup()}
        self.mapping_tree = mapping_tree
        self.construct_map()

    def construct_map(self):
        for symbol in self.map:
            if symbol.is_extern():
                leaf = self.mapping_tree.alloc(symbol.predicate)
            else:
                if symbol in self.dag.io():
                    leaf = self.mapping_tree.alloc(SCPatch.IO)
                else:
                    leaf = self.mapping_tree.alloc(SCPatch.REG)
            if leaf == TreeSlots.NO_CHILDREN_ERROR:
                raise Exception(f"Could not allocate {symbol}")
            self.map[symbol] = leaf.get_segment()

    def dag_symbol_to_segment(self, symbol):
        if symbol.is_extern():
           symbol = self.dag.scope[symbol.get_parent()].symbol.get_parent() 
        return self.map[symbol] 

    def dag_node_to_segments(self, dag_node):
        return [self.dag_symbol_to_segment(symbol) for symbol in dag_node.get_symbol().io.keys()]

    def dag_node_to_coordinates(self, dag_node):
        segments = self.dag_node_to_segments(dag_node)
        coordinates = []
        for node, segment in zip(dag_node.scope, segments):
            if segment.get_state() != SCPatch.EXTERN:
                coordinates.append((segment.x_0, segment.y_0)) 
            elif node.io_element is not None:
                offset = segment.get_slot().io[node.io_element]
                coordinates.append((segment.x_0 + offset, segment.y_1))
            else:
                coordinates.append((segment.x_0, segment.y_1))
        return coordinates 

    def __getitem__(self, dag_node):
        return self.dag_node_to_coordinates(dag_node)

    def __call__(self, dag_node):
        return self.__getitem__(dag_node)

    def __tikz__(self):
        return tikz_mapper(self)


class SegmentMap():
    ALLOC_FAILED = object()
    def __init__(self, segment):
        self.segment = segment
        self.map = dict()
        self.map_rev = dict()
        self.n_slots = segment.width
        self.n_slots_full = 0
        self.allocator_position = 0

    def initial_alloc(self, symbol):
        self.map

    def alloc(self, symbol):
        if self.n_slots_full == self.n_slots:
            raise Exception("REGISTER SEGMENT FULL")
        index = self.placement_strategy()
        self.map[symbol] = index
        self.map_rev[index] = symbol
        self.n_slots_full += 1

    def __getitem__(self, symbol):
        pass

    def __hash__(self):
        return self.segment.__hash__()

    def __eq__(self, other):
        return self.segment == other.segment

    def placement_strategy(self):
        if self.n_slots <= 4:
            # A reasonable hash function for small segments
            return int((self.n_slots_full * 7 + (n_slots % self.n_slots)) % self.n_slots)
        else:
            # A better hash function for larger placements
            index = self.ALLOC_FAILED
            while index is self.ALLOC_FAILED:
                row_num = int(maths.floor(maths.log2(self.allocator_position + 1)) + 1) 
                divisor = 2 ** row_num 
                col_num = int(self.allocator_position + 1 - divisor // 2)
                dividend = (((divisor + (4 % divisor)) // 2 * col_num + 1)) % divisor
                position = maths.floor(self.n_slots * dividend / divisor)
                self.allocator_position += 1
                
                free_slot = self.map_rev.get(position, self.ALLOC_FAILED) 
                if free_slot is self.ALLOC_FAILED:
                    index = position
            return index


