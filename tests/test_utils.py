from surface_code_routing.tree_slots import TreeSlots, TreeSlot, SegmentSlot
from surface_code_routing.symbol import symbol_resolve

class TreeNodeInterface():
    def __init__(self, symbol, weight, slots, segment=None):
        self.symbol = symbol_resolve(symbol)
        self.weight = weight
        self.slots = slots
        self.segment = segment
    
    def get_weight(self, *symbol):
        return self.weight

    def alloc(self, symbol):
        if self.symbol != symbol:
            return TreeSlots.NO_CHILDREN_ERROR
        if self.slots == 0:
            return TreeSlots.NO_CHILDREN_ERROR
        else:
            self.slots -= 1
            return self

    def get_symbol(self):
        return self.symbol

    def get_slot(self):
        return self.symbol

    def get_slot_name(self):
        return self.symbol


    def get_state(self):
        return self.symbol

    def get_segment(self):
        return self.segment

    def exhausted(self, symbol):
        return self.slots == 0

    def __repr__(self):
        return f"[{self.symbol}: {self.weight}, {self.slots}]"

    def n_slots(self):
        return self.slots

class GraphNodeInterface:
    '''
        A dummy interface that implements the required functions for the test
    '''
    def __init__(self, symbol, n_slots=1):
        self.symbol = symbol
        self.n_slots = n_slots

    def get_symbol(self):
        return self.symbol

    def get_segment(self):
        return self

    def get_slot(self):
        return self.symbol
    
    def get_state(self):
        return self.symbol

    def get_slot_name(self):
        return self.symbol

    def get_n_slots(self):
        return self.n_slots


class ExternInterface():
    def __init__(self, symbol, n_cycles, n_prewarm=0):
        self.symbol = symbol_resolve(symbol)
        self.__n_cycles = n_cycles
        self.__n_prewarm = n_prewarm
        self.slack = float('inf')

    def n_cycles(self):
        return self.__n_cycles 

    def n_pre_warm_cycles(self):
        return self.__n_prewarm

    def get_symbol(self):
        return self.symbol

    def __repr__(self):
        return self.symbol.__repr__()

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)

    def satisfies(self, other):
        return self.symbol.satisfies(other)

    def get_obj(self):
        return self


class QCBInterface():
    def __init__(self, width, height, *segments):
        self.width = width
        self.height = height
        self.segments = segments

class QCBSegmentInterface():
    def __init__(self, x_0, y_0, x_1, y_1, slot):
        self.x_0 = x_0
        self.y_0 = y_0
        self.x_1 = x_1
        self.y_1 = y_1
        self.slot = slot

    def get_slot(self):
        return self.slot

    def range(self):
        for x in range(self.x_0, self.x_1):
            for y in range(self.y_0, self.y_1):
                yield x, y
        

class GateInterface():
    def __init__(self, symbol, n_ancillae=0):
        self.symbol = symbol
        self.__n_ancillae = n_ancillae

    def n_ancillae(self):
        return self.__n_ancillae


class MapperInterface():
    def __init__(self, mapping_dict):
        self.map = mapping_dict

    def __getitem__(self, key):
        return self.map[key]
