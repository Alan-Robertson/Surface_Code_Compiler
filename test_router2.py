from dag2 import DAG
from qcb import QCB
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T, Toffoli
from scope import Scope
from extern_interface import ExternInterface

from pprint import pprint
from allocator import Allocator
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


graph = QCBPrune(qcb_base.segments)


from mapper2 import QCBMapper

mapper = QCBMapper(prune.grid_segments)
root = mapper.generate_mapping_tree()

# print_mapping_tree(root, file="mapper2_beforemap.tex")

mapper.map_all(g)

# print_mapping_tree(root, file="mapper2_aftermap.tex")



from router2 import QCBRouter

router = QCBRouter(qcb_base, g, mapper, allocator)

router.route_all()

# print_inst_locks2(qcb_base.segments, g.gates, 'main_frames.tex')

# for gate in g.gates:
#     print(gate, gate.start, gate.end, gate.anc, 'pred', gate.predicates)
#     if gate.is_extern():
#         print('\t', hex(id(gate)))
