import math as maths
from surface_code_routing.qcb import SCPatch
from surface_code_routing.tree_slots import TreeSlots
from surface_code_routing.tikz_utils import tikz_mapper

class QCBMapper():
    def __init__(self, dag, mapping_tree):
        self.dag = dag
        self.mapping_tree = mapping_tree
        
        self.map = dict()
        self.segment_maps = dict()
        
        for symbol in dag.lookup():
            if not symbol.is_extern():
                self.map[symbol] = None

        self.construct_map()
           
    def construct_map(self):
        for symbol in self.map:
            if symbol in self.dag.io():
                leaf = self.mapping_tree.alloc(SCPatch.IO)
                self.map[symbol] = IOSegmentMap(self.dag.symbol, leaf.get_segment())
            else:
                leaf = self.mapping_tree.alloc(SCPatch.REG)
                segment = leaf.get_segment()
                if (segment_map := self.segment_maps.get(segment, False)) is False:
                   segment_map = RegSegmentMap(segment) 
                   self.segment_maps[segment] = segment_map
                segment_map.alloc(symbol)

                self.map[symbol] = segment_map

            if leaf == TreeSlots.NO_CHILDREN_ERROR:
                raise Exception(f"Could not allocate {symbol}")

        # Handle Externs
        for extern in self.dag.physical_externs: 
            self.segment_maps[extern.symbol.predicate] = ExternSegmentMap(extern) 

        for symbol, extern in self.dag.externs.items():
            segment_map = self.segment_maps[symbol.predicate]
            if extern not in segment_map.segments:
                leaf = self.mapping_tree.alloc(symbol.predicate)
                segment = leaf.get_segment
                segment_map.alloc(extern, leaf.get_segment())
                segment_map.alloc(symbol, leaf.get_segment())
            else:
                segment_map.alloc(symbol, segment_map.segments[extern])
            self.map[symbol] = segment_map 

    def dag_node_to_symbol_map(self, dag_node):
        for symbol in dag_node.scope:
            yield symbol, self.dag_symbol_to_coordinates(symbol)

    def dag_symbol_to_segment(self, symbol):
        return self.map[symbol].get_segment()

    def dag_symbol_to_coordinates(self, symbol):
        segment_map = self.map[symbol]
        if segment_map.get_state() == SCPatch.EXTERN:
            return segment_map[symbol]
        elif symbol.io_element is not None:
            offset = segment.get_slot().io[node.io_element]
            return (segment.y_1, segment.x_0 + offset)
        else:
            return segment_map[symbol]

    def dag_node_to_coordinates(self, dag_node):
        return [self.dag_symbol_to_coordinates(symbol) for symbol in dag_node.scope]
            
    def __getitem__(self, dag_node):
        return self.dag_node_to_coordinates(dag_node)

    def __call__(self, dag_node):
        return self.__getitem__(dag_node)

    def __tikz__(self):
        return tikz_mapper(self)


class RegSegmentMap():
    '''
        This handles placement within registers
    '''
    ALLOC_FAILED = object()
    def __init__(self, segment):
        self.segment = segment
        self.map = dict()
        self.map_rev = dict()
        self.n_slots = segment.width
        self.n_slots_full = 0
        self.allocator_position = 0

    def alloc(self, symbol):
        if self.n_slots_full == self.n_slots:
            raise Exception("REGISTER SEGMENT FULL")
        index = self.placement_strategy()
        self.map[symbol] = index
        self.map_rev[index] = symbol
        self.n_slots_full += 1

    def range(self):
        for offset in self.map_rev:
            yield self.segment.y_1, self.segment.x_0 + offset

    def get_state(self):
        return self.segment.get_state()

    def get_slot(self):
        return SCPatch.REG

    def __getitem__(self, symbol):
        return self.segment.y_1, self.segment.x_0 + self.map[symbol]

    def __hash__(self):
        return self.segment.__hash__()

    def __eq__(self, other):
        return self.segment == other.segment

    def __repr__(self):
        return self.map.__repr__()

    def placement_strategy(self):
        if self.n_slots <= 4:
            # A reasonable hash function for small segments
            return int((self.n_slots_full * 7 + self.n_slots) % self.n_slots)
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

class IOSegmentMap():
    '''
        This handles placement within registers
    '''
    def __init__(self, symbol, segment):
        self.segment = segment
        self.map = symbol.io

    def range(self):
        for offset in self.map.values():
            yield  self.segment.y_1, self.segment.x_0 + offset

    def get_state(self):
        return self.segment.get_state()

    def get_slot(self):
        return SCPatch.IO

    def __getitem__(self, symbol):
        return self.segment.y_1, self.segment.x_0 + self.map[symbol]

    def __hash__(self):
        return self.segment.__hash__()

    def __eq__(self, other):
        return self.segment == other.segment

    def __repr__(self):
        return self.map.__repr__()

class ExternSegmentMap():
    '''
        This handles placement within registers
    '''
    def __init__(self, extern):
        self.segments = dict()
        self.map = extern.io

    def alloc(self, symbol, segment):
        if segment not in self.segments:
            self.segments[symbol] = segment

    def range(self):
        for segment in self.segments.values():
            for coordinate in segment.range():
                yield coordinate

    def get_state(self):
        return SCPatch.EXTERN

    def get_slot(self):
        return SCPatch.EXTERN

    def __getitem__(self, symbol):
        segment = self.segments[symbol]
        offset = self.map.get(symbol.io_element, 0)
        return segment.y_1, segment.x_0 + offset

    def __hash__(self):
        return self.segment.__hash__()

    def __eq__(self, other):
        return self.segment == other.segment

    def __repr__(self):
        return self.map.__repr__()

    def __in__(self, other):
        return other in self.segments
