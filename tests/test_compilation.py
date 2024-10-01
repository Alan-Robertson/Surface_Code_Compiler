from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, PREP, MEAS, X
from surface_code_routing.lib_instructions import T, T_Factory,  Toffoli
from surface_code_routing.symbol import Symbol, ExternSymbol

from surface_code_routing.compiled_qcb import CompiledQCB, compile_qcb

import unittest

class CompilerTests(unittest.TestCase):
     
    def test_t_factory(self, height=5, width=9):
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(4)]))
        dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in range(11)]))
        dag.add_gate(PREP('factory_out'))
        dag.add_gate(CNOT('q_3', *['a_{i}'.format(i=i) for i in range(1, 8)]))
        dag.add_gate(CNOT('q_2', *['a_{i}'.format(i=i) for i in (0, 2, 3, 4, 5, 8, 9)]))
        dag.add_gate(CNOT('q_1', *['a_{i}'.format(i=i) for i in (0, 1, 3, 4, 6, 8, 10)]))
        dag.add_gate(CNOT('q_0', *['a_{i}'.format(i=i) for i in (0, 1, 2, 4, 7, 9, 10)]))
        dag.add_gate(CNOT('factory_out', *('a_{i}'.format(i=i) for i in range(10, 3, -1))))
        dag.add_gate(MEAS(
            *['q_{i}'.format(i=i) for i in range(4)], 
            *['a_{i}'.format(i=i) for i in range(11)],
            'factory_out'))
        dag.add_gate(X('factory_out'))

        qcb = compile_qcb(dag, height, width)

    def test_range_t_factories(self):
        for height in range(5, 50, 7):
            for width in range(9, 50, 7):
                self.test_t_factory(height, width)


    def test_io(self):
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT('a')) 
        dag.add_gate(CNOT('factory_out', 'a'))
        
        for i in range(9, 50, 7):
            qcb = compile_qcb(dag, i, i)


    def test_compiled_qcb(self, small_qcb=4, large_qcb=6):
        # Dummy T Factory
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        t_factory = compile_qcb(dag, small_qcb, small_qcb)
        
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a'))
        dag.add_gate(T('a'))

        qcb_comp = compile_qcb(dag, large_qcb, large_qcb, t_factory)
    
    def test_qcb_sizes(self):

        for small_qcb in range(4, 40, 7):
            for large_qcb in range(6, 40, 7):
                if large_qcb < small_qcb:
                    try:
                        self.test_compiled_qcb(small_qcb, large_qcb)
                        passed = True
                    except:
                        passed = False 
                    assert(not passed)
                else:
                    self.test_compiled_qcb(small_qcb, large_qcb)

if __name__ == '__main__':
    unittest.main()
