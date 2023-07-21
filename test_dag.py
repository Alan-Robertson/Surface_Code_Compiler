from dag2 import DAG
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T
from scope import Scope
from extern_interface import ExternInterface

factory = ExternInterface(ExternSymbol('T_Factory'), 17)

g = DAG(Symbol('tst'))
init = INIT('a', 'b', 'c', 'd')
g.add_gate(init)
g.add_gate(CNOT('a', 'b'))
#g.add_gate(CNOT('c', 'd'))
g.add_gate(T('a'))
#g.add_gate(T('a'))

out = g.compile(1, factory)



from pprint import pprint
pprint(out)