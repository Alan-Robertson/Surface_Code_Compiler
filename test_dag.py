from dag2 import DAG
from symbol import Symbol
import msf

from instructions import INIT, CNOT, T
from scope import Scope

g = DAG(Symbol('tst'))
init = INIT('a', 'b', 'c')
scope = Scope({init['a']:g['x'], init['b']:g['y'], init['c']:g['z']})
higher_scope = Scope({Symbol('x'):None, Symbol('y'):None})
g.add_gate(init, scope=scope)
assert(Symbol('x') in g.scope)
assert(Symbol('y') in g.scope)

cnot = CNOT('x', 'y')
g.add_gate(cnot)
g.add_gate(T('x'))


# gg = DAG(Symbol('gg'))
# gg.add_gate(g, scope={g['x']:gg['a'], g['y']:gg['b']})

# assert(Symbol('a') in gg.scope)
# assert(Symbol('b') in gg.scope)

# ggg = DAG(Symbol('ggg'))
# ggg.add_gate(gg, scope={gg['a']:ggg['x'], gg['b']:ggg['y']})
