from functools import reduce
from utils import consume
from qcb import SCPatch
import unittest
from mapper import QCBMapper
from symbol import Symbol, ExternSymbol
from scope import Scope
from dag import DAG

from tikz_utils import tex

def ExternInjector(extern_name):
    sym = Symbol(extern_name)

    extern = ExternSymbol(extern_name)
    scope = Scope({extern:extern})

    dag = DAG(sym, scope=scope)
    dag.add_node(extern, n_cycles=1)
    return dag

class AllocatorTest(unittest.TestCase):
    def test_original(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c', 'd')
        g.add_gate(init)
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(T('a'))
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(Toffoli('a', 'b', 'c'))
        g.add_gate(T('a'))
        g.add_gate(T('a'))
        g.add_gate(T('c'))
        g.add_gate(T('d'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))
        g.add_gate(T('a'))
        g.add_gate(T('c'))
        g.add_gate(Toffoli('a', 'b', 'c'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))


        sym = ExternSymbol('T_Factory', 'factory_out')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(15, 10, g)

        allocator = Allocator(qcb_base, factory_impl)

    def test_simple_extern(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        g = DAG(Symbol('tst'))
        g.add_gate(INIT('a', 'b', 'c', 'd'))
        g.add_gate(T('a'))



        sym = ExternSymbol('T_Factory', 'factory_out')
        factory_impl = QCB(1, 4, DAG(symbol=sym, scope={sym:sym}))

        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(3, 5, g)

        allocator = Allocator(qcb_base, factory_impl)

    
    def test_only_extern(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        g = DAG(Symbol('tst'))
        g.add_gate(ExternInjector('A'))
        g.add_gate(ExternInjector('B'))
        g.add_gate(ExternInjector('C'))
        

        syms = [ExternSymbol(c, 'out') for c in 'ABC']
        factory_impls = [QCB(1, i+1, DAG(symbol=s, scope={s:s})) for i, s in enumerate(syms)]




        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(3, 4, g)

        allocator = Allocator(qcb_base, *factory_impls)
        print(tex(qcb_base), file=open("test.tex", "w"))

    def test_3x2(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT


        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c', 'd')
        g.add_gate(init)
      
        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(2, 3, g)

        allocator = Allocator(qcb_base)
    
    

    def test_2x2(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT


        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c', 'd')
        g.add_gate(init)
      
        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(2, 2, g)

        try:
            allocator = Allocator(qcb_base)
        except:
            return
        
        assert False, "This should fail."


if __name__ == '__main__':
    unittest.main()
