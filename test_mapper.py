from functools import reduce
from utils import consume
from tree_slots import TreeSlots, TreeSlot, SegmentSlot
from mapping_tree import RegNode, RouteNode
from qcb import SCPatch
import unittest

from test_utils import TreeNodeInterface, GraphNodeInterface 


class MapperTest(unittest.TestCase):

    def test_reg_mapping(self):
        from graph_prune import QCBGraph
        from mapping_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB
        from dag import DAG
        from instructions import INIT, CNOT, T, Toffoli
        from symbol import Symbol, ExternSymbol

        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(T('a'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(Toffoli('a', 'b', 'c'))
        dag.add_gate(T('a'))
        dag.add_gate(T('a'))
        dag.add_gate(T('c'))
        dag.add_gate(T('d'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('c', 'a'))
        dag.add_gate(CNOT('b', 'd'))
        dag.add_gate(T('a'))
        dag.add_gate(T('c'))
        dag.add_gate(Toffoli('a', 'b', 'c'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('c', 'a'))
        dag.add_gate(CNOT('b', 'd'))

        sym = ExternSymbol('T_Factory')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, factory_impl)
        allocator.allocate()
        allocator.optimise()

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
    
        mapper = QCBMapper(qcb_base, tree)

        


if __name__ == '__main__':
    unittest.main()
