from surface_code_routing.bind import AddrBind
from surface_code_routing.constants import COULD_NOT_ALLOCATE  
from surface_code_routing.qcb import SCPatch 

class ExternPatchAllocatorStatic():
   
    def __init__(self, mapper):
        self.mapper = mapper

        for extern in self.mapper.dag.physical_externs: 
            if extern.symbol.predicate not in self.mapper.segment_maps:
                self.mapper.segment_maps[extern.symbol.predicate] = ExternSegmentMap(extern, self) 

        for symbol, extern in self.mapper.dag.externs.items():
            segment_map = self.mapper.segment_maps[symbol.predicate]
            if extern not in segment_map.segments:
                leaf = self.mapper.mapping_tree.alloc(symbol.predicate)
                segment = leaf.get_segment
                segment_map.alloc(extern, leaf.get_segment())
                segment_map.alloc(symbol, leaf.get_segment())
            else:
                segment_map.alloc(symbol, segment_map.segments[extern])
            self.mapper.map[symbol] = segment_map 


    def free(self, symbol):
        self.mapper.segment_maps[symbol.predicate].free(symbol)


class ExternSegmentMap():
    '''
        This handles placement for aliased externs
    '''
    def __init__(self, extern, static_allocator):
        self.segments = dict()
        self.locks = dict()
        self.map = extern.io
        self.extern = extern
        self.allocator = static_allocator

    def alloc(self, symbol, segment):
        if segment not in self.segments:
            self.segments[symbol] = segment

    def free(self, symbol):
        self.locks[symbol] = None

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
        return self.extern.__hash__()

    def __eq__(self, other):
        return self.segment == other.segment

    def __repr__(self):
        return self.map.__repr__()

    def __in__(self, other):
        return other in self.segments
