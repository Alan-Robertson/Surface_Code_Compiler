from dag2 import DAG
from qcb import QCB
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T
from scope import Scope
from extern_interface import ExternInterface

factory = ExternInterface(ExternSymbol('T_Factory'), 17)

g = DAG(Symbol('tst'))
init = INIT('a', 'b', 'c', 'd')
g.add_gate(init)
g.add_gate(CNOT('a', 'b'))
g.add_gate(CNOT('c', 'd'))
g.add_gate(T('a'))
g.add_gate(CNOT('a', 'b'))
g.add_gate(T('a'))
g.add_gate(T('a'))
g.add_gate(T('c'))
g.add_gate(T('d'))
g.add_gate(CNOT('c', 'd'))
g.add_gate(CNOT('c', 'a'))
g.add_gate(CNOT('b', 'd'))
g.add_gate(T('a'))
g.add_gate(T('c'))
g.add_gate(CNOT('c', 'd'))
g.add_gate(CNOT('c', 'a'))
g.add_gate(CNOT('b', 'd'))

out = g.compile(1, factory)

sym = ExternSymbol('T_Factory')
factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

print()

from pprint import pprint
pprint(out)

print()

from allocator2 import Allocator
from qcb import QCB
qcb_base = QCB(15, 10, g)

allocator = Allocator(qcb_base, factory_impl)

print()


allocator.allocate()

print()

allocator.optimise()

print()

from test_tikz_helper import *
print_qcb(allocator.qcb.segments, "allocator2.tex")
print(allocator.msfs)
