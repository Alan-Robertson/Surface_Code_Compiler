from dag2 import DAG
from symbol import Symbol, ExternSymbol, symbol_map

from instructions import INIT, CNOT, T
from scope import Scope

# g = DAG(Symbol('tst'))
# init = INIT('a', 'b', 'c', 'd')
# g.add_gate(init)
# g.add_gate(CNOT('a', 'b'))
# g.add_gate(CNOT('c', 'd'))
# g.add_gate(T('a'))


targ = 'x'
targ = symbol_map(targ)
sym = Symbol('T', 'targ')

factory = ExternSymbol('T_Factory')

scope = Scope({factory:factory, sym('targ'):targ})

dag = DAG(sym, scope=scope)
dag.add_gate(INIT('x'))
dag.add_gate(T('x'))