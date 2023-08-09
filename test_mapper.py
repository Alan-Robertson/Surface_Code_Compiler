from graph_prune import QCBGraph
from mapping_tree import QCBTree
from allocator2 import Allocator
from qcb import QCB
from dag2 import DAG

from instructions import INIT, CNOT, T, Toffoli

from mapper import Mapper
from symbol import Symbol, ExternSymbol

import unittest

class MapperTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
allocator.allocate()
allocator.optimise()

graph = QCBGraph(qcb_base)
tree = QCBTree(graph)
