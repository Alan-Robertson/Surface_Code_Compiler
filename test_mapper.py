from dag2 import DAG
from qcb import QCB
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T, Toffoli
from scope import Scope
from extern_interface import ExternInterface

from pprint import pprint
from allocator2 import Allocator
from qcb import QCB
from graph_prune import QCBPrune
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


prune = QCBPrune(qcb_base.segments)
prune.map_to_grid()

print_connectivity_graph(prune.grid_segments, 'main_connectivity.tex')
