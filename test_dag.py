from dag2 import DAG
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T
from scope import Scope
from extern_interface import ExternInterface

n_factories = 2
n_channels = 2 

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

out = g.compile(n_channels, *[ExternInterface(ExternSymbol('T_Factory'), 17) for _ in range(n_factories)])



# from pprint import pprint
# pprint(out)