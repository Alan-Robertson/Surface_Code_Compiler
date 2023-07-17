from symbol import Symbol, ExternSymbol
from scope import Scope
import unittest

class SymbolTest(unittest.TestCase):
    def test_str_cmp(self):
        x = Symbol('x')
        
        # Names must be unique
        y = Symbol('x')
        assert(y.satisfies(x))

        
    def test_satisfies(self):
        x = Symbol('x', io_in=Symbol('y'))
        y_factory = Symbol('y')
        
        y = x[0]
        assert(y.satisfies(y_factory))

        elements = {x}
        assert(y not in elements)
        assert(y.get_parent() in elements)

    def test_inject(self):
        sym = Symbol('x', 'y', 'z')
        sym_2 = list(map(Symbol, ['a', 'b']))
        mapping = Scope({sym('y'):sym_2[0], sym('z'):sym_2[1]})

    def test_externs(self):
        factory = ExternSymbol('T')
        another_factory = ExternSymbol('T')
        factory_scope = factory('test')

        sym = ExternSymbol(factory, 'x')
        sym_2 = ExternSymbol(factory, 'y')
        sym_3 = ExternSymbol(another_factory, 'x')

        assert(sym == sym_2)
        assert(sym_3 != sym)
        assert(factory_scope == factory)
        
        assert(factory.satisfies(sym))
        assert(factory.satisfies(sym_2))
        assert(factory.satisfies(sym_3))
        assert(factory.satisfies(another_factory))
        
        

        

if __name__ == '__main__':
    unittest.main()
