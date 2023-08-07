from tree_slots import TreeSlots, TreeSlot
import unittest


class DummyObj():
    def __init__(self, symbol, weight, slots):
        self.symbol = symbol
        self.weight = weight
        self.slots = slots
    
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

class SlotTest(unittest.TestCase):

    def test_no_slots(self):
        s = TreeSlots(None)
        assert s.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR

    def test_one_alloc(self):
        s = TreeSlots(None)
        obj = DummyObj('TST', 2, 1)
        s.distribute('TST', obj)
        assert s.get_weight('TST') == 2
        assert s.alloc('TST').n_slots() == 0
        assert s.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR

    def test_two_allocs(self):
        s = TreeSlots(None)
        obj = DummyObj('TST', 2, 2)
        s.distribute('TST', obj)
        assert s.get_weight('TST') == 2
        assert s.alloc('TST').n_slots() == 1
        assert s.alloc('TST').n_slots() == 0
        assert s.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR

    def test_two_slots(self):
        s = TreeSlots(None)
        obj_a = DummyObj('TST', 3, 1)
        obj_b = DummyObj('TST', 2, 2)
        s.distribute('TST', obj_a)
        s.distribute('TST', obj_b)

        assert s.get_weight('TST') == 3
        assert s.alloc('TST').n_slots() == 0
        assert(len(s.slots['TST'].ordering) == 1)
        # Slot exhausted
        assert s.get_weight('TST') == 2

    def test_nested(self):
        s = TreeSlots(None)
        top = TreeSlots(None)
        obj_a = DummyObj('TST', 3, 1)
        obj_b = DummyObj('TST', 2, 2)
        s.distribute('TST', obj_a)
        s.distribute('TST', obj_b)
        top.distribute('TST', s)
        assert (len(s.slots['TST'].ordering) == 2)
        assert top.get_weight('TST') == 3
        assert top.alloc('TST') == obj_a
        assert(len(s.slots['TST'].ordering) == 1)
        assert top.get_weight('TST') == 2
        assert top.alloc('TST') == obj_b
        assert top.alloc('TST') == obj_b
        assert top.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR
        assert top.get_weight('TST') == 0 
 


if __name__ == '__main__':
    unittest.main()
