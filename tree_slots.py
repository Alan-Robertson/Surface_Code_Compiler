import bisect

from qcb import SCPatch

class TreeSlots():
    '''
        Allocator object
    '''
    NO_CHILDREN_ERROR = object()

    def __init__(self, tree_node):
        self.tree_node = tree_node
        self.slots = {}

    def distribute(self, symbol, child):
        if symbol not in self.slots:
            self.slots[symbol] = TreeSlot(symbol)
        self.slots[symbol].distribute(child)

    def alloc(self, symbol): 
        if symbol not in self.slots:
            return self.NO_CHILDREN_ERROR
        return self.slots[symbol].alloc()
    
    def get_weight(self, symbol):
        return self.slots[symbol].get_weight()

    def exhausted(self, symbol):
        return self.slots[symbol].exhausted()

class TreeSlot():
    '''
        Slot for a single symbol instance
    '''
    def __init__(self, symbol, initial_value=0):
        self.symbol = symbol
        self.value = initial_value
        self.children = set()
        self.ordering = []
        
        self.weight_updated = False
        self.last_weight = 0

    def distribute(self, child):
        if child not in self.children:
            self.children.add(child)
            bisect.insort(self.ordering, child, key = lambda x: x.get_weight(self.symbol))
        else:
            self.ordering.sort()
        self.last_weight = self.ordering[-1].get_weight(self.symbol)

    def get_weight(self):
        # Faster to manually track this in the ordering
        if self.weight_updated:
            self.last_weight = max((x.get_weight(self.symbol) for x in self.ordering), default=0)
            self.weight_updated = False
        return self.last_weight

    def alloc(self):
        binding = TreeSlots.NO_CHILDREN_ERROR
        while binding == TreeSlots.NO_CHILDREN_ERROR:
            if self.exhausted():
                return TreeSlots.NO_CHILDREN_ERROR
            allocated = self.ordering.pop()
            binding = allocated.alloc(self.symbol)
        
        # Round robin, re-insert at the start
        if not allocated.exhausted(self.symbol):
            self.ordering.insert(0, allocated)
        self.weight_updated = True
        return binding 

    def exhausted(self):
        return len(self.ordering) == 0

class SegmentSlot():
    def __init__(self, leaf):
        self.symbol = leaf.get_symbol()
        self.weight = leaf.slots[SCPatch.ROUTE]
        self.n_slots = leaf.get_segment().get_slots()
    
    def get_weight(self, symbol):
        return self.weight

    def alloc(self, symbol):
        if self.symbol != symbol:
            return TreeSlots.NO_CHILDREN_ERROR
        if self.slots == 0:
            return TreeSlots.NO_CHILDREN_ERROR
        else:
            self.slots -= 1
            return self

    def exhausted(self, symbol):
        return self.slots == 0

    def __repr__(self):
        return f"[{self.symbol}: {self.weight}, {self.slots}]"

    def n_slots(self):
        return self.slots


