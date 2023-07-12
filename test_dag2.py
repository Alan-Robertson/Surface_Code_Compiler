from dag2 import DAG
from symbol import Symbol

from instructions import INIT, CNOT, T
from scope import Scope




from scope import Scope
from symbol import Symbol
import unittest

class ScopeTest(unittest.TestCase):
    def test_unroll(self):
        g = DAG(Symbol('tst'))
        g.add_gate(INIT('a', 'b', 'c'))

        assert(Symbol('a') in g.scope)
        assert(Symbol('b') in g.scope)
        assert(Symbol('c') in g.scope)


    def test_scope(self):
        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c')
        scope = Scope({init['a']:g['x'], init['b']:g['y'], init['c']:g['z']})

        g.add_gate(init, scope=scope)

        assert(Symbol('x') in g.scope)
        assert(Symbol('y') in g.scope)

    def test_cnot(self):
        g = DAG(Symbol('tst'))
        g.add_gate(INIT('a', 'b', 'c'))

        cnot = CNOT('a', 'b')
        g.add_gate(cnot)
        assert(g.gates[-1].symbol == cnot.symbol)


    def test_dag_compose(self):
        g = DAG(Symbol('tst'))
        g.add_gate(INIT('a', 'b', 'c'))

        h = DAG(Symbol('tst'))
        h.add_gate(INIT('x', 'y', 'z'))

        g.add_gate(h)

        assert(Symbol('a') in g.scope)
        assert(Symbol('x') in g.scope)
        assert(Symbol('y') in g.scope)


    def test_externs(self):
        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c')
        
        g.add_gate(init)
        g.add_gate(T('a'))

        assert(Symbol('T_Factory') in g.externs)
        

    def test_extern_fungibility(self):
        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c')
        
        g.add_gate(init)

        
        g.add_gate(T('a'))
        t_1 = g.gates[-2]

        g.add_gate(T('a'))
        t_2 = g.gates[-2]

        assert(g.externs[0] == t_1.externs[0])
        assert(g.externs[0] is t_1.externs[0])
        assert(g.externs[1] == t_2.externs[0])
        assert(g.externs[1] is t_2.externs[0])

        assert(g.externs[1] == t_1.externs[0])
        assert(g.externs[1] is not t_1.externs[0])
        assert(g.externs[0] == t_2.externs[0])
        assert(g.externs[0] is not t_2.externs[0])

        
if __name__ == '__main__':
    unittest.main()



# gg = DAG(Symbol('gg'))
# gg.add_gate(g, scope={g['x']:gg['a'], g['y']:gg['b']})

# assert(Symbol('a') in gg.scope)
# assert(Symbol('b') in gg.scope)

# ggg = DAG(Symbol('ggg'))
# ggg.add_gate(gg, scope={gg['a']:ggg['x'], gg['b']:ggg['y']})
