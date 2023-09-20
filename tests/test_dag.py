from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol

from surface_code_routing.instructions import INIT, CNOT
from surface_code_routing.lib_instructions import T, T_Factory
from surface_code_routing.scope import Scope


from surface_code_routing.scope import Scope
from surface_code_routing.symbol import Symbol, ExternSymbol
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

        assert(ExternSymbol('T_Factory') not in g.externs)
        assert(g.externs.contains(ExternSymbol('T_Factory')))
        
    def test_externs_more(self):
        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c')
        
        g.add_gate(init)
        g.add_gate(T('a'))
        g.add_gate(T('a'))
        g.add_gate(T('a'))


        assert(ExternSymbol('T_Factory') not in g.externs)
        assert(g.externs.contains(ExternSymbol('T_Factory')))


    def test_extern_fungibility(self):
        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c')
        
        g.add_gate(init)

        
        g.add_gate(T('a'))
        t_1 = g.gates[-3].symbol

        g.add_gate(T('a'))
        t_2 = g.gates[-3].symbol

        extern_symbols = list(g.externs.keys())

        assert(extern_symbols[0] == t_1)
        assert(extern_symbols[0] is t_1)
        assert(extern_symbols[1] == t_2)
        assert(extern_symbols[1] is t_2)

        assert(extern_symbols[1].satisfies(t_1))
        assert(extern_symbols[1] != t_1)
        assert(extern_symbols[0].satisfies(t_2))
        assert(extern_symbols[0] !=  t_2)

        
if __name__ == '__main__':
    unittest.main()
