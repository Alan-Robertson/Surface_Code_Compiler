from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, PREP, MEAS, X
from surface_code_routing.lib_instructions import T, T_Factory,  Toffoli
from surface_code_routing.symbol import Symbol, ExternSymbol

from surface_code_routing.compiled_qcb import CompiledQCB, compile_qcb

import unittest

class CompilerTests(unittest.TestCase):
     
    def test_t_factory(self):
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

        qcb = compile_qcb(dag, 5, 9)


    def test_io(self):
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT('a')) 
        dag.add_gate(CNOT('factory_out', 'a'))

        qcb = compile_qcb(dag, 5, 9)


    def test_compiled_qcb(self):
        # Dummy T Factory
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        t_factory = compile_qcb(dag, 4, 4)
        
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a'))
        dag.add_gate(T('a'))

        qcb_comp = compile_qcb(dag, 6, 6, t_factory)

if __name__ == '__main__':
    unittest.main()
 
