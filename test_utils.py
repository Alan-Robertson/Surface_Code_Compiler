from tree_slots import TreeSlots, TreeSlot, SegmentSlot
from symbol import symbol_resolve

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
