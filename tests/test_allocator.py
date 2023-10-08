import numpy as np
import unittest
from functools import reduce

from surface_code_routing.utils import consume
from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.symbol import Symbol, ExternSymbol
from surface_code_routing.scope import Scope
from surface_code_routing.dag import DAG
from surface_code_routing.allocator import Allocator, AllocatorError

from surface_code_routing.instructions import INIT, CNOT, Hadamard

from test_utils import CompiledQCBInterface


from surface_code_routing.qcb import QCB, Segment, SCPatch

class SegmentTest(unittest.TestCase):
    def test_segments(self):

        segment = Segment(0, 0, 4, 4)
        finalised_segments = {segment}

        confirm, segments = segment.split(0, 0, 1, 1)

        assert (len(finalised_segments) == 1)
        assert (len(segments) == 4)

        confirm(finalised_segments)
        assert (len(finalised_segments) == 4)

        seg_tl = next((i for i in finalised_segments if i.x_0 == 0 and i.y_0 == 0), None)
        seg_tr = next((i for i in finalised_segments if i.x_0 == 1 and i.y_0 == 0), None)
        assert (len(seg_tl.below) == 1 and len(seg_tl.left) == 0 and len(seg_tl.right) == 1 and len(seg_tl.above) == 0) 
        assert (len(seg_tr.below) == 1 and len(seg_tr.left) == 1 and len(seg_tr.right) == 0 and len(seg_tr.above) == 0) 
        
        seg_bl = next(iter(seg_tl.below))
        seg_br = next(iter(seg_tr.below))

        assert (seg_tl in seg_tr.left) and (seg_br in seg_tr.below)
        assert (seg_tr in seg_tl.right) and (seg_bl in seg_tl.below)
        assert (seg_bl in seg_br.left) and (seg_tr in seg_br.above)
        assert (seg_br in seg_bl.right) and (seg_tl in seg_bl.above)

        assert (seg_br.horizontal_merge(seg_bl)[1] == seg_bl.horizontal_merge(seg_br)[1])
        assert (seg_tr.horizontal_merge(seg_tl)[1] == seg_tl.horizontal_merge(seg_tr)[1])
        assert (seg_tr.vertical_merge(seg_br)[1] == seg_br.vertical_merge(seg_tr)[1])
        assert (seg_tl.vertical_merge(seg_bl)[1] == seg_bl.vertical_merge(seg_tl)[1])

        confirm, seg_bottom = seg_bl.horizontal_merge(seg_br)
        confirm(finalised_segments)
        assert(len(finalised_segments) == 3)
        assert(seg_bottom in finalised_segments)
  
        error_uncaught = False
        try: # Too tall
            seg_bottom.split(1, 1, 5, 1)
            error_uncaught = True
        except AssertionError:
            pass
    
        try: # Too short
            seg_bottom.split(1, 1, 0, 1)
            error_uncaught = True
        except AssertionError:
            pass

        try: # Y Coord out of bounds up
            seg_bottom.split(0, 1, 4, 1)
            error_uncaught = True
        except AssertionError:
            pass

        try: # Y Coord out of bounds down
            seg_bottom.split(5, -1, 4, 1)
            error_uncaught = True
        except AssertionError:
            pass

        try: # Too long
            seg_bottom.split(1, 1, 1, 5)
            error_uncaught = True
        except AssertionError:
            pass
    
        try: # Too narrow
            seg_bottom.split(1, 1, 1, 0)
            error_uncaught = True
        except AssertionError:
            pass

        try: # X Coord out of bounds left
            seg_bottom.split(1, -1, 4, 1)
            error_uncaught = True
        except AssertionError:
            pass

        try: # X Coord out of bounds right
            seg_bottom.split(1, 5, 4, 1)
            error_uncaught = True
        except AssertionError:
            pass

        assert error_uncaught is False


class AllocatorTest(unittest.TestCase):
    def test_top_alloc(self):

        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(5)]))

        qcb_base = QCB(5, 5, g)

        allocator = Allocator(qcb_base)


    def test_two_reg_row_alloc(self):

        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(6)]))

        qcb_base = QCB(5, 5, g)

        allocator = Allocator(qcb_base)


    def test_three_reg_row_alloc(self):

        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(11)]))

        qcb_base = QCB(5, 5, g)

        allocator = Allocator(qcb_base)

    def test_four_reg_row_alloc(self):

        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(14)]))

        qcb_base = QCB(6, 5, g)

        allocator = Allocator(qcb_base)

    def test_five_reg_row_alloc(self):

        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(16)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base)

    def test_single_extern(self):
        extern = CompiledQCBInterface("TST", 3, 3)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(5)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern)

    def test_two_externs(self):
        extern_a = CompiledQCBInterface("TST", 2, 2)
        extern_b = CompiledQCBInterface("TST", 2, 2)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(5)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)

    def test_two_externs_more_reg(self):
        extern_a = CompiledQCBInterface("TST", 2, 2)
        extern_b = CompiledQCBInterface("TST", 2, 2)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(8)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)

    def test_extern_right_drop_up(self):
        extern_a = CompiledQCBInterface("TST", 2, 3)
        extern_b = CompiledQCBInterface("TST", 2, 3)
        g = DAG(Symbol('tst'))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)
    
    def test_extern_right_drop_up_registers(self):
        extern_a = CompiledQCBInterface("TST", 2, 3)
        extern_b = CompiledQCBInterface("TST", 2, 3)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(7)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)

    def test_extern_right_drop(self):
        extern_a = CompiledQCBInterface("TST", 1, 3)
        extern_b = CompiledQCBInterface("TST", 2, 2)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(7)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)

    def test_extern_right_drop_down(self):
        extern_a = CompiledQCBInterface("TST", 1, 2)
        extern_b = CompiledQCBInterface("TST", 3, 3)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(5)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)

    def test_extern_right_drop_top_registers(self):
        extern_a = CompiledQCBInterface("TST", 1, 3)
        extern_b = CompiledQCBInterface("TST", 2, 2)
        g = DAG(Symbol('tst'))
        g.add_gate(INIT(*[f'q_{i}' for i in range(7)]))

        qcb_base = QCB(7, 5, g)

        allocator = Allocator(qcb_base, extern_a, extern_b)



    def test_random_externs(self):
        for i in range(10):
            rand_int = lambda: np.random.randint(1, 5)
            rand_size = lambda: np.random.randint(7, 10)
            extern_a = CompiledQCBInterface("TST", rand_int(), rand_int())
            extern_b = CompiledQCBInterface("TST", rand_int(), rand_int())
            g = DAG(Symbol('tst'))
            g.add_gate(INIT(*[f'q_{i}' for i in range(5)]))
            qcb_base = QCB(
                    min(rand_size(), extern_a.height + extern_b.height + 2), 
                    min(rand_size(), extern_a.width + extern_b.width + 1),
                    g)

            try:
                allocator = Allocator(qcb_base, extern_a, extern_b)
            except AllocatorError:
                pass

if __name__ == '__main__':
    unittest.main()
