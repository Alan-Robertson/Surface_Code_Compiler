from scope import Scope
from symbol import Symbol
import unittest

class ScopeTest(unittest.TestCase):
    def test_scope_map(self):
        x = Symbol('x')
        y = Symbol('y')

        scope = Scope(x)
        scope = Scope(x, y)
        scope[x] = y

        assert(scope[x] == y)
        assert(x in scope)
        assert(y in scope)

    def test_scope_satisfies(self):

        x = Symbol('x')
        y = Symbol('y')

        f = Symbol('F', Symbol('b'), Symbol('c'))

        scope = Scope(x, y)
        subscope = Scope(Symbol('b'), Symbol('c'))

        assert(scope.satisfies(f, subscope) is False)
        subscope[Symbol('b')] = x
        assert(scope.satisfies(f, subscope) is False)
        subscope[Symbol('c')] = y
        assert(scope.satisfies(f, subscope) is True)

    def test_init(self):
        f = Symbol('INIT', Symbol('b'), Symbol('c'))

        b = f(Symbol('b'))
        c = f(Symbol('c'))

        scope = Scope()
        subscope = Scope({b:b, c:None})
        assert(scope.satisfies(f, subscope) is False)

        subscope = Scope({b:b, c:c})
        assert(scope.satisfies(f, subscope) is True)

    def test_inject(self):
        f = Symbol('CNOT', Symbol('b'), Symbol('c'))

        b = Symbol('b')
        c = Symbol('c')

        x = Symbol('x')
        y = Symbol('y')

        higher_scope = Scope({b:x, c:y})
        f.inject(higher_scope)
        assert(x in f.io)
        assert(y in f.io)
        assert(b not in f.io)
        assert(c not in f.io)

                
        
        
if __name__ == '__main__':
    unittest.main()

