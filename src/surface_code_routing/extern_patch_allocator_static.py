from surface_code_routing.bind import AddrBind
from surface_code_routing.constants import COULD_NOT_ALLOCATE  
from surface_code_routing.qcb import SCPatch 

from surface_code_routing.utils import debug_print


class ExternPatchAllocatorStatic():
   
    def __init__(self, mapper, verbose=False):
        self.mapper = mapper
        self.dag = self.mapper.dag
        self.verbose = verbose

        # Allocate segments appropriately
        for extern in self.mapper.dag.physical_externs: 
            if extern.symbol.predicate not in self.mapper.segment_maps:
                self.mapper.segment_maps[extern.symbol.predicate] = ExternSegmentMap(extern, self, verbose=self.verbose) 

        for symbol, extern in self.mapper.dag.externs.items():
            segment_map = self.mapper.segment_maps[symbol.predicate]
            if extern not in segment_map.segments:
                leaf = self.mapper.mapping_tree.alloc(symbol.predicate)
                segment = leaf.get_segment()
                segment_map.allocate_segment(extern, segment)
                segment_map.allocate_segment(symbol, segment)
            else:
                segment_map.allocate_segment(symbol, segment_map.segments[extern])
            self.mapper.map[symbol] = segment_map 

    def __getitem__(self, symbol):
        return self.mapper.segment_maps[symbol.predicate][symbol]

    def first_free_cycle(self, symbol):
        '''
            As part of a lock on a factory this determines how many cycles this extern has been idle for 
        '''
        return self.mapper.segment_maps[symbol.predicate].first_free_cycle(symbol)

    def alloc(self, symbol):
        '''
            This takes the unary symbol from the gate and uses the predicate to generalise to the symbol's unique instance
        '''
        dag_extern = self.dag.externs[symbol]
        return self.mapper.segment_maps[symbol.predicate].alloc(symbol, dag_extern, speculative=True)

    def lock(self, symbol):
        dag_extern = self.dag.externs[symbol]
        return self.mapper.segment_maps[symbol.predicate].alloc(symbol, dag_extern, speculative=False)

    def free(self, symbol):
        dag_extern = self.dag.externs[symbol]
        self.mapper.segment_maps[symbol.predicate].free(symbol, dag_extern)


class ExternSegmentMap():
    '''
        This handles placement for aliased externs
    '''
    def __init__(self, extern, static_allocator, verbose=False):
        self.segments = dict()
        self.locks = dict()
        self.__first_free_cycle = dict()
        self.map = extern.io
        self.extern = extern
        self.allocator = static_allocator
        self.n_unlocked_segments = 0
        self.verbose = verbose
        self.is_factory = self.extern.is_factory

    def debug_print(self, *args, **kwargs):
        debug_print(*args, **kwargs, debug=self.verbose)

    def allocate_segment(self, symbol, segment):
        '''
            Binds a symbol to a segment
        '''
        if symbol not in self.segments:
            self.segments[symbol] = segment
        if segment not in self.locks:            
            self.locks[segment] = None
            self.n_unlocked_segments += 1
            self.__first_free_cycle[segment] = 0
            self.debug_print(f"Added Lock: {segment}")

    def alloc(self, symbol, dag_extern, speculative=True):
        '''
            Attempts to allocate a segment for a symbol 
            If speculative then it does not perform a lock
        '''
        segment = self.segments.get(dag_extern, COULD_NOT_ALLOCATE)
        if segment is COULD_NOT_ALLOCATE:
            raise Exception(f"{symbol} has yet to be assigned a segment")

        lock_state = self.locks[segment]
        if lock_state is None:
            if speculative is False:
                self.n_unlocked_segments -= 1
                self.locks[segment] = symbol
                self.segments[symbol] = segment
                self.debug_print(f"\tLocked {segment} on {hex(id(symbol.predicate))}")

            return segment
        if lock_state == symbol:
            return segment
        return COULD_NOT_ALLOCATE 

    def first_free_cycle(self, symbol):
        segment = self.segments.get(symbol, None)
        if segment is None:
            raise Exception(f"{symbol} has not yet been allocated")
        return self.__first_free_cycle[segment]

    def lock_state(self, symbol, dag_extern):
        '''
            Probes the current lock state for a given symbol
        '''
        segment = self.segments.get(dag_extern, None)
        if segment is None:
            raise Exception(f"{symbol} has yet to be assigned a segment")
        lock_state = self.locks[segment]
        if lock_state is None or lock_state == symbol:
            return True
        return False

    def free(self, symbol, dag_extern):
        '''
            Frees the segment assocated with a symbol
        '''
        segment = self.segments.get(dag_extern, None)
        if self.locks[segment] == symbol: 
            self.n_unlocked_segments += 1
            self.locks[segment] = None

            # For rolling back gates
            self.__first_free_cycle[segment] = len(self.allocator.mapper.router.layers)
            return
        raise Exception(f"{symbol} has not been allocated and hence cannot be freed")
        

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
