from functools import reduce
from utils import consume
from tree_slots import TreeSlots, TreeSlot, SegmentSlot
from qcb_tree import RegNode, RouteNode
from qcb import SCPatch
import unittest

from test_utils import TreeNodeInterface, GraphNodeInterface 
from symbol import Symbol, ExternSymbol

class SlotTest(unittest.TestCase):

    TST = Symbol('TST')
    QWOP = Symbol('QWOP')

    def test_no_slots(self):
        s = TreeSlots(None)
        assert s.alloc(self.TST) == TreeSlots.NO_CHILDREN_ERROR

    def test_one_alloc(self):
        s = TreeSlots(None)
        obj = TreeNodeInterface(self.TST, 2, 1)
        s.distribute(self.TST, obj)
        assert s.get_weight(self.TST) == 2
        assert s.alloc(self.TST).n_slots() == 0
        assert s.alloc(self.TST) == TreeSlots.NO_CHILDREN_ERROR

    def test_two_allocs(self):
        s = TreeSlots(None)
        obj = TreeNodeInterface(self.TST, 2, 2)
        s.distribute(self.TST, obj)
        assert s.get_weight(self.TST) == 2
        assert s.alloc(self.TST).n_slots() == 1
        assert s.alloc(self.TST).n_slots() == 0
        assert s.alloc(self.TST) == TreeSlots.NO_CHILDREN_ERROR

    def test_two_slots(self):
        s = TreeSlots(None)
        obj_a = TreeNodeInterface(self.TST, 3, 1)
        obj_b = TreeNodeInterface(self.TST, 2, 2)
        s.distribute(self.TST, obj_a)
        s.distribute(self.TST, obj_b)

        assert s.get_weight(self.TST) == 3
        assert s.alloc(self.TST).n_slots() == 0
        assert(len(s.slots[self.TST].ordering) == 1)
        # Slot exhausted
        assert s.get_weight(self.TST) == 2

    def test_nested(self):
        s = TreeSlots(None)
        top = TreeSlots(None)

        # Segments
        segment_a = GraphNodeInterface(SCPatch.REG, n_slots=2) 
        segment_b = GraphNodeInterface(SCPatch.REG, n_slots=2) 

        # Associated with leaves on the tree
        obj_a = TreeNodeInterface(SCPatch.REG, 3, 1, segment=segment_a)
        obj_b = TreeNodeInterface(SCPatch.REG, 2, 1, segment=segment_b)
       
        # Associated with slots
        slot_a = SegmentSlot(obj_a)
        slot_b = SegmentSlot(obj_b)

        # Bound to other slots
        s.bind_slot(slot_a)
        s.bind_slot(slot_b)
        
        # Bound to other slots
        top.distribute_slots(s)

        # And allocated from the root
        assert top.alloc(SCPatch.REG) == obj_a
        assert top.alloc(SCPatch.REG) == obj_b
        assert top.alloc(SCPatch.REG) == obj_a
        assert top.alloc(SCPatch.REG) == obj_b
        assert top.alloc(SCPatch.REG) == TreeSlots.NO_CHILDREN_ERROR 

    def test_segment_slot(self):
        segment_a = GraphNodeInterface(SCPatch.REG)
        segment_b = GraphNodeInterface(SCPatch.REG)
        obj_a = SegmentSlot(TreeNodeInterface(self.TST, 3, 1, segment=segment_a))
        obj_b = SegmentSlot(TreeNodeInterface(self.TST, 2, 2, segment=segment_b))
 
        s = TreeSlots(None)
        top = TreeSlots(None)
        s.bind_slot(obj_a)
        s.bind_slot(obj_b)
        top.distribute_slots(s)

    def test_nested_distribute(self):
        s = TreeSlots(None)
        top = TreeSlots(None)
        obj_a = TreeNodeInterface(self.TST, 3, 1)
        obj_b = TreeNodeInterface(self.TST, 2, 2)
        obj_c = TreeNodeInterface(self.QWOP, 1, 1)
        s.distribute(self.TST, obj_a)
        s.distribute(self.TST, obj_b)
        s.distribute(self.QWOP, obj_c)
        top.distribute_slots(s)
        assert (len(s.slots[self.TST].ordering) == 2)
        assert top.get_weight(self.TST) == 3
        assert top.alloc(self.TST) == obj_a
        assert(len(s.slots[self.TST].ordering) == 1)
        assert top.get_weight(self.TST) == 2
        assert top.alloc(self.TST) == obj_b
        assert top.alloc(self.TST) == obj_b
        assert top.alloc(self.TST) == TreeSlots.NO_CHILDREN_ERROR
        assert top.get_weight(self.TST) == 0 
        assert top.alloc(self.QWOP) == obj_c
    
    def test_nested_distribute(self):
        a = TreeSlots(None)
        b = TreeSlots(None)

        top = TreeSlots(None)
        obj_a = TreeNodeInterface(self.TST, 3, 1)
        obj_b = TreeNodeInterface(self.TST, 2, 2)
        obj_c = TreeNodeInterface(self.QWOP, 4, 1)
        obj_d = TreeNodeInterface(self.QWOP, 3, 1)
        obj_e = TreeNodeInterface(self.QWOP, 2, 1)
        obj_f = TreeNodeInterface(self.QWOP, 1, 1)

        a.distribute(self.TST, obj_a)
        a.distribute(self.TST, obj_c)
        a.distribute(self.TST, obj_d)
        b.distribute(self.TST, obj_b)
        b.distribute(self.TST, obj_e)
        b.distribute(self.TST, obj_f)

        top.distribute_slots(a)
        top.distribute_slots(b)

        assert a in top.slots[self.TST].children
        assert b in top.slots[self.TST].children

        assert obj_a is top.alloc(self.TST)


    
    def test_slot_merger(self):
        '''
            Build all the way from the graph
        '''
        a = RegNode(GraphNodeInterface(SCPatch.REG))
        b = RegNode(GraphNodeInterface(SCPatch.REG))
        c = RegNode(GraphNodeInterface(SCPatch.REG))
        d = RegNode(GraphNodeInterface(SCPatch.REG))
        route_a = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_b = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_b_one = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_b_two = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_c = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_c_one = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_d = RouteNode(GraphNodeInterface(SCPatch.ROUTE))
        route_e = RouteNode(GraphNodeInterface(SCPatch.ROUTE))

        a.neighbours = {route_a}
        b.neighbours = {route_b, route_b_one}
        c.neighbours = {route_c, route_c_one}
        d.neighbours = {route_d}
        route_a.neighbours = {a, route_e}
        route_b.neighbours = {b, route_e}
        route_b_one.neighbours = {b, route_b_two}
        route_b_two.neighbours = {route_b_one}
        route_c.neighbours = {c, route_e}
        route_c_one.neighbours = {c}
        route_d.neighbours = {d, route_e}
        route_e.neighbours = {route_a, route_b, route_c, route_d}

        fringe = {a, b, c, d}
        parents = fringe

        while len(parents) > 1: 

            joint_nodes = set()
            starter = fringe
            fringe = reduce(lambda a, b: a | b, 
                       map(lambda x: set(
                           i for i in x.get_adjacent() if i.get_parent() != x.get_parent()),
                           starter)
                       )

            for node in starter:
                 for adjacent_node in node.get_adjacent():
                     parent = node.get_parent()
                     adj_parent = adjacent_node.get_parent()
                     if parent in joint_nodes:
                         joint_nodes.remove(parent)
                     if adj_parent in joint_nodes:
                         joint_nodes.remove(adj_parent)
                     joint_nodes.add(adj_parent.merge(parent))

            consume(map(lambda x: x.distribute(), fringe))
            consume(map(lambda x: x.bind(), joint_nodes))
            consume(map(lambda x: x.bind(), fringe))

            parents = set(map(lambda x : x.parent, fringe))

        layer = {a, b, c, d}
        while len(layer) > 1:
            consume(map(lambda x: x.distribute_slots(), layer))
            layer = set(map(lambda x: x.get_parent(), layer))

        root = next(iter(layer))
        leaves = {a, b, c, d}
        for i in range(4):
            assert(root.alloc(SCPatch.REG) in leaves)
        assert(root.alloc(SCPatch.REG) is TreeSlots.NO_CHILDREN_ERROR)

    def test_compiler_chain(self):
        from qcb_graph import QCBGraph
        from qcb_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB
        from dag import DAG
        from instructions import INIT, CNOT, T, Toffoli
        from symbol import Symbol, ExternSymbol

        g = DAG(Symbol('Test'))
        g.add_gate(INIT('a', 'b', 'c', 'd'))
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(T('a'))
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(Toffoli('a', 'b', 'c'))
        g.add_gate(T('a'))
        g.add_gate(T('a'))
        g.add_gate(T('c'))
        g.add_gate(T('d'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))
        g.add_gate(T('a'))
        g.add_gate(T('c'))
        g.add_gate(Toffoli('a', 'b', 'c'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))

        sym = ExternSymbol('T_Factory')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, g)
        allocator = Allocator(qcb_base, factory_impl)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
    
        assert(len(tree.root.slots.slots) > 0)

        N_REGISTERS = 33
        N_EXTERNS = 4
        for i in range(N_REGISTERS):
            assert tree.alloc(SCPatch.REG) is not TreeSlots.NO_CHILDREN_ERROR
        assert tree.alloc(SCPatch.REG) is TreeSlots.NO_CHILDREN_ERROR

        for i in range(N_EXTERNS):
            assert tree.alloc(sym.predicate) is not TreeSlots.NO_CHILDREN_ERROR
        assert tree.alloc(sym.predicate) is TreeSlots.NO_CHILDREN_ERROR

if __name__ == '__main__':
    unittest.main()
