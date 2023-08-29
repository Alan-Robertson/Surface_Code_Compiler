from dag import DAG
from instructions import INIT, CNOT, T, Toffoli
from symbol import Symbol, ExternSymbol

from allocator import Allocator
from qcb import QCB
from mapper import QCBMapper
from qcb_graph import QCBGraph
from qcb_tree import QCBTree

from router import QCBRouter
import unittest

class CompilerTests(unittest.TestCase):
      
    def test_single_dag(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))

        qcb_base = QCB(4, 4, dag)
        allocator = Allocator(qcb_base)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)

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


if __name__ == '__main__':
    unittest.main()
 
