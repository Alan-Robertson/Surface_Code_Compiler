import unittest
from functools import reduce

from surface_code_routing.utils import consume
from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.symbol import Symbol, ExternSymbol
from surface_code_routing.scope import Scope
from surface_code_routing.dag import DAG
from surface_code_routing.allocator import Allocator

from surface_code_routing.instructions import INIT, CNOT

def ExternInjector(extern_name):
    sym = Symbol(extern_name)

    extern = ExternSymbol(extern_name)
    scope = Scope({extern:extern})

    dag = DAG(sym, scope=scope)
    dag.add_node(extern, n_cycles=1)
    return dag

class AllocatorTest(unittest.TestCase):
    def test_original(self):

        g = DAG(Symbol('tst'))
        init = INIT('a', 'b', 'c', 'd')
        g.add_gate(init)
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))

        qcb_base = QCB(5, 5, g)

        allocator = Allocator(qcb_base, factory_impl)

    def test_simple_extern(self):
        from surface_code_routing.lib_instructions import T, T_Factory
        g = DAG(Symbol('tst'))
        g.add_gate(INIT('a', 'b', 'c', 'd'))
        g.add_gate(T('a'))

        qcb_base = QCB(7, 7, g)

        allocator = Allocator(qcb_base, T_Factory())

    def test_io_extern_collision(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        dag_symbol = ExternSymbol('tst', 'out')
        g = DAG(dag_symbol, scope={dag_symbol:dag_symbol})
        g.add_gate(ExternInjector('A'))
        
        sym = ExternSymbol('A', 'out')
        factory_impl = QCB(1, 2, DAG(symbol=sym, scope={sym:sym}))

        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(3, 3, g)

        allocator = Allocator(qcb_base, factory_impl)

    def test_io_reg_collision(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        g = DAG(Symbol('tst', 'out'))
        g.add_gate(INIT('a', 'b', 'c', 'd'))


        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(4, 4, g)

        allocator = Allocator(qcb_base)

    def test_io_extern_collision_fail(self):
        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        dag_symbol = ExternSymbol('tst', 'out')
        g = DAG(dag_symbol, scope={dag_symbol:dag_symbol})
        g.add_gate(ExternInjector('A'))

        
        sym = ExternSymbol('A', 'out')
        factory_impl = QCB(1, 2, DAG(symbol=sym, scope={sym:sym}))

        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(3, 3, g)

        try:
            allocator = Allocator(qcb_base, factory_impl)
        except:
            return

        assert False, "This should fail."


    def test_extern_io_conflict_drop(self):

        from dag import DAG
        from qcb import QCB
        from symbol import Symbol, ExternSymbol, symbol_map

        from instructions import INIT, CNOT, T, Toffoli
        from scope import Scope
        from extern_interface import ExternInterface

        # factory = ExternInterface(ExternSymbol('T_Factory'), 17)

        dag_symbol = ExternSymbol('tst', 'out')
        g = DAG(dag_symbol, scope={dag_symbol:dag_symbol})
        g.add_gate(INIT('a', 'b'))
        g.add_gate(ExternInjector('A'))
        g.add_gate(ExternInjector('B'))

        
        sym_a = ExternSymbol('A', 'out')
        factory_a = QCB(2, 4, DAG(symbol=sym_a, scope={sym_a:sym_a}))

        sym_b = ExternSymbol('B', 'out')
        factory_b = QCB(1, 1, DAG(symbol=sym_b, scope={sym_b:sym_b}))

        from allocator import Allocator
        from qcb import QCB
        qcb_base = QCB(4, 5, g)

        try:
            allocator = Allocator(qcb_base, factory_a, factory_b)
        except AssertionError as e:
            raise e
        
  

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

        allocator = Allocator(qcb_base, *(factory_impls))

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
    
   
    def test_reproducibility(self):
        '''
            Run the same inputs a few times to see if we get the same allocation
        '''
        def dag_fn(n_qubits, width, height): 
             dag = DAG(f'qft_{n_qubits}_height')
             for i in range(n_qubits):
                 dag.add_gate(Hadamard(f'q_{i}'))
                 for j in range(i + 1, n_qubits):
                     dag.add_gate(CNOT(f'q_{j}', f'q_{i}'))
             return dag

        height = 5
        width = 5
        n_qubits = 6
        qcb_base = QCB(height, width, (dag_fn(n_qubits, height, width)))
        Allocator(qcb_base)
        segs_base = list(qcb_base.segments)
        segs_base.sort(key = lambda seg:  seg.x_0 * height + seg.y_0)
        for i in range(20): 
            qcb = QCB(height, width, (qft(n_qubits, height, width)))
            allocator = Allocator(qcb)
            segs = list(qcb.segments)
            segs.sort(key=lambda   seg.x_0 * height + seg.y_0)
            for seg, seg_b in zip(segs, segs_base): 
                 assert(seg.state.state == seg_b.state.state)

    def test_2x2(se 

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
