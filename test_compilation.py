from dag import DAG
from instructions import INIT, CNOT, T, Toffoli, PREP, MEAS, X
from symbol import Symbol, ExternSymbol

from allocator import Allocator
from qcb import QCB
from mapper import QCBMapper
from qcb_graph import QCBGraph
from qcb_tree import QCBTree

from compiled_qcb import CompiledQCB

from router import QCBRouter
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

        qcb = QCB(5, 9, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb, dag, mapper)

        compiled_t_factory = CompiledQCB(qcb, router, dag) 


    def test_single_dag(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))

        qcb_base = QCB(4, 4, dag)
        allocator = Allocator(qcb_base)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
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

        qcb = QCB(height, width, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb, dag, mapper)

        compiled_t_factory = CompiledQCB(qcb, router, dag) 


        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb_base, dag, mapper)

        sym = ExternSymbol('T_Factory', 'factory_out')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, factory_impl)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb_base, dag, mapper)

    def test_io(self):
        dag_a = DAG(Symbol('T_Factory', 'factory_out'))
        dag_a.add_gate(INIT('a')) 
        dag_a.add_gate(CNOT('factory_out', 'a'))

        qcb_base = QCB(4, 4, dag_a)
        allocator = Allocator(qcb_base)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag_a, tree)
        router = QCBRouter(qcb_base, dag_a, mapper)
    
        dag_b = DAG(Symbol('Test 2'))
        dag_b.add_gate(INIT('x', 'y', 'z'))
        dag_b.add_gate(T('x'))


    def test_compiled_qcb(self):
        # Dummy T Factory
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))

        qcb = QCB(4, 4, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb, dag, mapper)

        t_factory = CompiledQCB(qcb, router, dag)
        
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a'))
        dag.add_gate(T('a'))

        qcb_base = QCB(6, 6, dag)  
        allocator = Allocator(qcb_base, t_factory)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb_base, dag, mapper)


if __name__ == '__main__':
    unittest.main()
 
