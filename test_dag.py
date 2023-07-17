from dag2 import DAG
from symbol import Symbol

from instructions import INIT, CNOT, T
from scope import Scope

g = DAG(Symbol('tst'))
init = INIT('a', 'b', 'c', 'd')
g.add_gate(init)
g.add_gate(CNOT('a', 'b'))
g.add_gate(CNOT('c', 'd'))
g.add_gate(T('a'))


#g.add_gate(T('x'))

# gg = DAG(Symbol('gg'))
# gg.add_gate(g, scope={g['x']:gg['a'], g['y']:gg['b']})

# assert(Symbol('a') in gg.scope)
# assert(Symbol('b') in gg.scope)

# ggg = DAG(Symbol('ggg'))
# ggg.add_gate(gg, scope={gg['a']:ggg['x'], gg['b']:ggg['y']})
