from dag2 import DAG
from qcb import QCB
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T, Toffoli
from scope import Scope

from pprint import pprint
from allocator2 import Allocator
from qcb import QCB
from graph_prune import QCBGraph
from test_tikz_helper2 import *

g = DAG(Symbol('tst'))
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

from mapping_tree import QCBTree
x = QCBTree(graph)



#print(tikz_partial_tree(*x.nodes))

# from mapper2 import QCBMapper

# mapper = QCBMapper(prune.segments)
# root = mapper.generate_mapping_tree()

# print_mapping_tree(root, file="mapper2_beforemap.tex")

# mapper.map_all(g)

# print_mapping_tree(root, file="mapper2_aftermap.tex")
