import math as maths
from surface_code_routing.qcb import SCPatch
from surface_code_routing.tree_slots import TreeSlots
from surface_code_routing.tikz_utils import tikz_mapper
from surface_code_routing.extern_patch_allocator_dynamic import ExternPatchAllocatorDynamic
from surface_code_routing.extern_patch_allocator_static import ExternPatchAllocatorStatic 
from surface_code_routing.extern_patch_allocator_sized import ExternPatchAllocatorSized

from surface_code_routing.constants import COULD_NOT_ALLOCATE

class QCBMapper():
    def __init__(self, dag, mapping_tree, extern_allocation_method='dynamic'):
        self.dag = dag
        self.mapping_tree = mapping_tree
        self.qcb = mapping_tree.graph.qcb
        
        self.map = dict()
        self.segment_maps = dict()
        
        self.router = None

        for symbol in dag.lookup():
            if not symbol.is_extern():
                self.map[symbol] = None

        self.construct_register_map()

        self.extern_allocation_method = extern_allocation_method
        self.extern_allocator = {
            'static': ExternPatchAllocatorStatic, 
            'dynamic': ExternPatchAllocatorDynamic,
            'sized': ExternPatchAllocatorSized
        }.get(extern_allocation_method, None)(self) 

    def alloc_extern(self, symbol):
        return self.extern_allocator.alloc(symbol)

    def flush(self):
        self.extern_allocator.flush()

    def free(self, gate):
        self.extern_allocator.free(gate.get_unary_symbol())

    def first_free_cycle(self, gate):
        return self.extern_allocator.first_free_cycle(gate.get_unary_symbol())

    def get_extern_coordinate(self, symbol):
        return self.extern_allocator[symbol]

    def construct_register_map(self):
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

    def dag_node_to_symbol_map(self, dag_node, rollback=False):
        for symbol in dag_node.scope:
            coords, rollback =  self.dag_symbol_to_coordinates(symbol)
            if rollback:
                yield symbol, coords, rollback 
            else:
                yield symbol, coords
    def dag_symbol_to_segment(self, symbol):
        return self.map[symbol].get_segment()

    def dag_symbol_to_coordinates(self, symbol):
        if symbol.is_extern():
            # Allocator triggered here
            allocation_result, rollback = self.alloc_extern(symbol)
            if allocation_result is COULD_NOT_ALLOCATE:
                return COULD_NOT_ALLOCATE, None
            else:
                return self.get_extern_coordinate(symbol), rollback

        segment_map = self.map[symbol]
        if symbol.io_element is not None:
            offset = segment.get_slot().io[node.io_element]
            return (segment.y_1, segment.x_0 + offset), None
        else:
            return segment_map[symbol], None

    def dag_node_to_coordinates(self, dag_node):
        coordinates = list()
        rollback_alloc = list()
        for symbol in dag_node.scope:
            coordinate, rollback = self.dag_symbol_to_coordinates(symbol) 
            if rollback is not None:
                rollback_alloc.append(rollback)
            if coordinate is COULD_NOT_ALLOCATE:
                for rollback in rollback_alloc:
                    rollback()
                return COULD_NOT_ALLOCATE
            coordinates.append(coordinate)

        # Bind the extern
        if dag_node.is_extern():
            dag_node.bind_extern(self.dag.externs[symbol])
        return coordinates 

    def lock_externs(self, dag_node):
        # Two stage attempt to acquire and rollback 
        # Problem dealing with partial locking
        for symbol in dag_node.scope:
            coordinate = self.dag_symbol_to_coordinates(symbol) 
            if coordinate is COULD_NOT_ALLOCATE:
                return COULD_NOT_ALLOCATE
            coordinates.append(coordinate)

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

    def get_segment(self):
        return self.segment

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
        # TODO, ensure that the last allocations are at the ends of the segment
        if self.n_slots <= 4:
            # A reasonable hash function for small segments
            return int((self.n_slots_full * 7 + self.n_slots) % self.n_slots)
        else:
            # A better hash function for larger placements
            # Double check this one, chance of duplication, could lead to slowdowns
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
        This handles placement for the IO
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

    def get_segment(self):
        return self.segment

    def __getitem__(self, symbol):
        return self.segment.y_1, self.segment.x_0 + self.map[symbol]

    def __hash__(self):
        return self.segment.__hash__()

    def __eq__(self, other):
        return self.segment == other.segment

    def __repr__(self):
        return self.map.__repr__()


