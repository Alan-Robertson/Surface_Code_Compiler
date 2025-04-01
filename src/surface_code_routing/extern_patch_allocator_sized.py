from surface_code_routing.bind import AddrBind
from surface_code_routing.constants import COULD_NOT_ALLOCATE  
from surface_code_routing.qcb import SCPatch 

from surface_code_routing.utils import debug_print
from surface_code_routing.bind import AddrBind 

from functools import partial

class ExternPatchAllocatorSized():
   
    def __init__(self, mapper, verbose=False):
        self.mapper = mapper
        self.dag = self.mapper.dag
        self.verbose = verbose

        extern_templates = {}

        self.allocatable = {extern.symbol.predicate: extern for extern in self.mapper.dag.physical_externs}

        self.segment_map = ExternSegmentMapSized(self, self.allocatable)

        # Extract extern regions 
        for extern in self.allocatable: 
            leaf = self.mapper.mapping_tree.alloc(extern) 
            segment = leaf.get_segment()
            self.segment_map.allocate_segment(segment)

            self.mapper.segment_maps[extern] = self.segment_map

        return

    def debug_print(self, *args, **kwargs):
        debug_print(*args, **kwargs, debug=self.verbose)


    def __getitem__(self, symbol):
        return self.segment_map[symbol]

    def first_free_cycle(self, symbol):
        '''
            As part of a lock on a factory this determines how many cycles this extern has been idle for 
        '''
        return self.mapper.segment_maps[symbol.predicate].first_free_cycle(symbol)

    def alloc(self, symbol):
        '''
            This takes the unary symbol from the gate and uses the predicate to generalise to the symbol's unique instance
        '''
        return self.segment_map.alloc(symbol)

    def lock(self, symbol):
        return self.mapper.segment_maps[symbol.predicate].alloc(symbol)

    def free(self, symbol):
        self.mapper.segment_maps[symbol.predicate].free(symbol)


class ExternSegmentMapSized():
    
    NO_SEGMENT_ALLOCATED = AddrBind("No Segment Allocated")
    '''
        This handles placement for aliased externs
    '''
    def __init__(self, allocator, allocatable: dict):


        self.allocator = allocator
        self.allocatable = allocatable

        self.segments = dict()
        self.locks = dict()
        self.__first_free_cycle = dict()

        self.map = {} 
        self.extern = {} 

        self.idle_segments = list() 

        self.is_factory = None 

    def add_segment(self, extern): 
        raise Exception

    def allocate_segment(self, segment):
        '''
            Binds a symbol to a segment
        '''
        if segment not in self.locks:            
            self.locks[segment] = None
            self.idle_segments.append(segment)
            self.__first_free_cycle[segment] = 0
        else:
            raise Exception(f"Segment {segment} allocated in duplicate")

    def get_physical_segments(self):
        return tuple(self.locks.keys()) 

    def alloc(self, symbol):
        '''
            Attempts to allocate a segment for a symbol 
        '''
        segment = self.segments.get(symbol, self.NO_SEGMENT_ALLOCATED)
        if segment is self.NO_SEGMENT_ALLOCATED:

            # No free segments
            if len(self.idle_segments) == 0:
                return COULD_NOT_ALLOCATE, None
            
            alloc_target = self.allocatable[symbol.predicate]

            # Get a segment of the correct size
            # This could be a sorted search... 
            for seg in self.idle_segments:
                if seg.height >= alloc_target.height and seg.width >= alloc_target.width: 
                    segment = seg
                    break
            # Else on the for loop
            else:
                return COULD_NOT_ALLOCATE, None

        lock_state = self.locks[segment]
        if lock_state is None:
            self.locks[segment] = symbol
            self.segments[symbol] = segment
            
            rollback = partial(self.free, symbol) 
            self.idle_segments.remove(segment)

            return segment, rollback

        if lock_state == symbol:
            return segment, None
        return COULD_NOT_ALLOCATE, None 

    def first_free_cycle(self, symbol):
        segment = self.segments.get(symbol, None)
        if segment is None:
            raise Exception(f"{symbol} has not yet been allocated")
        return self.__first_free_cycle[segment]

    def lock_state(self, symbol, dag_extern):
        '''
            Probes the current lock state for a given symbol
        '''
        segment = self.segments.get(symbol, None)
        if segment is None:
            raise Exception(f"{symbol} has yet to be assigned a segment")
        lock_state = self.locks[segment]
        if lock_state is None or lock_state == symbol:
            return True
        return False

    def free(self, symbol):
        '''
            Frees the segment assocated with a symbol
        '''
        segment = self.segments.get(symbol, None)
        if self.locks[segment] == symbol: 
            self.idle_segments.append(segment)
            self.locks[segment] = None

            # For rolling back gates
            self.__first_free_cycle[segment] = len(self.allocator.mapper.router.layers)
            return
        raise Exception(f"{symbol} has not been allocated and hence cannot be freed")
        
    def range(self):
        for segment in self.get_physical_segments():
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
