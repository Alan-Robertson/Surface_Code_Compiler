from functools import reduce
from utils import consume
from qcb import SCPatch
import unittest
from mapper import QCBMapper

from lib_instructions import T_Factory
from instructions import INIT, T, CNOT, MEAS, X
from dag import DAG
from symbol import Symbol, ExternSymbol
from mapper import QCBMapper
from qcb_graph import QCBGraph
from qcb_tree import QCBTree
from allocator import Allocator
from qcb import QCB
     
class MapperTest(unittest.TestCase):

    def test_t_factory(self):
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(4)]))
        dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in range(11)]))
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

        qcb = QCB(5, 9, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        for gate in dag.gates:
            assert(len(mapper[gate]) > 0)

    def test_extern_qcb(self):

        t_fact = T_Factory()
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(t_fact.instruction((), ('a')))
        dag.add_gate(t_fact.instruction((), ('a')))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, t_fact)
        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)
 
        gate = dag.gates[-3]
        args = gate.get_symbol()
      
        assert gate.get_symbol().predicate == Symbol('T_Factory')
        for gate in dag.gates:
            assert(len(mapper[gate]) > 0)


    def test_reg_mapping(self):
        from qcb_graph import QCBGraph
        from qcb_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB
        from dag import DAG
        from instructions import INIT, CNOT, T, Toffoli
        from symbol import Symbol, ExternSymbol

        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(T('a'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(Toffoli('a', 'b', 'c'))
        dag.add_gate(T('a'))
        dag.add_gate(T('a'))
        dag.add_gate(T('c'))
        dag.add_gate(T('d'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('c', 'a'))
        dag.add_gate(CNOT('b', 'd'))
        dag.add_gate(T('a'))
        dag.add_gate(T('c'))
        dag.add_gate(Toffoli('a', 'b', 'c'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('c', 'a'))
        dag.add_gate(CNOT('b', 'd'))

        t_fact = T_Factory()
        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, t_fact)
        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)
        for gate in dag.gates:
            assert(len(mapper[gate]) > 0)

if __name__ == '__main__':
    unittest.main()
