from dag import DAG
from instructions import INIT, CNOT, T, Toffoli
from symbol import Symbol, ExternSymbol

from qcb import SCPatch

from router import QCBRouter

import unittest

from test_utils import QCBInterface, QCBSegmentInterface 

class RouterTest(unittest.TestCase):

    def test_simple_route(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))

        mapper = {Symbol('a'):(0, 0),
                  Symbol('b'):(0, 2)}

        qcb = QCBInterface(
            1, 3,
            QCBSegmentInterface(0, 0, 0, 0, SCPatch.REG),
            QCBSegmentInterface(0, 1, 0, 1, SCPatch.ROUTE),
            QCBSegmentInterface(0, 2, 0, 2, SCPatch.REG)
            )

        router = QCBRouter(qcb, dag, mapper, auto_route=False)

        route_found, route = router.find_route(Symbol('gate'), [[0, 0], [0, 2]])
        assert route_found
        assert route == [router.graph[0, 0], router.graph[0, 1], router.graph[0, 2]]

    def test_two_routes(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))

        mapper = {Symbol('a'):(0, 0),
                  Symbol('b'):(0, 2),
                  Symbol('c'):(0, 0),
                  Symbol('d'):(0, 0)
                  }
                 
        qcb = QCBInterface(
            2, 3,
            QCBSegmentInterface(0, 0, 0, 0, SCPatch.REG),
            QCBSegmentInterface(0, 1, 0, 1, SCPatch.ROUTE),
            QCBSegmentInterface(0, 2, 0, 2, SCPatch.REG), 
            QCBSegmentInterface(1, 1, 1, 1, SCPatch.REG),
            QCBSegmentInterface(1, 1, 1, 1, SCPatch.ROUTE),
            QCBSegmentInterface(1, 2, 1, 2, SCPatch.REG)
            )

        router = QCBRouter(qcb, dag, mapper, auto_route=False)

        gate_a = Symbol('gate_a')
        route_found, route = router.find_route(gate_a, [[0, 0], [0, 2]])
        assert route_found
        assert route == [router.graph[0, 0], router.graph[0, 1], router.graph[0, 2]]
        router.active_gates.add(gate_a)

        gate_b = Symbol('gate_b')
        route_found, route = router.find_route(gate_b, [[1, 0], [1, 2]])
        assert route_found
        assert route == [router.graph[1, 0], router.graph[1, 1], router.graph[1, 2]]

    def test_lock_unlock(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))

        mapper = {Symbol('a'):(1, 0),
                  Symbol('b'):(1, 2),
                  Symbol('c'):(0, 1),
                  Symbol('d'):(2, 1)
                  }
                 
        qcb = QCBInterface(
            3, 3,
            QCBSegmentInterface(1, 0, 1, 0, SCPatch.REG),
            QCBSegmentInterface(1, 1, 1, 1, SCPatch.ROUTE),
            QCBSegmentInterface(1, 2, 1, 2, SCPatch.REG), 
            QCBSegmentInterface(0, 1, 0, 1, SCPatch.REG),
            QCBSegmentInterface(2, 1, 2, 1, SCPatch.REG)
            )

        router = QCBRouter(qcb, dag, mapper, auto_route=False)

        gate_a = Symbol('gate_a')
        route_found, route = router.find_route(gate_a, [[1, 0], [1, 2]])
        assert route_found
        assert route == [router.graph[1, 0], router.graph[1, 1], router.graph[1, 2]]
        router.active_gates.add(gate_a)

        gate_b = Symbol('gate_b')
        route_found, route = router.find_route(gate_b, [[0, 1], [2, 1]])
        assert not route_found
        
        # Unlock
        router.active_gates.remove(gate_a)

        gate_b = Symbol('gate_b')
        route_found, route = router.find_route(gate_b, [[0, 1], [2, 1]])
        assert route_found
        assert route == [router.graph[0, 1], router.graph[1, 1], router.graph[2, 1]]

    def test_from_dag(self):
        from mapper import QCBMapper
        from qcb_graph import QCBGraph
        from qcb_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB

        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b'))
        dag.add_gate(CNOT('a', 'b'))

        qcb = QCB(4, 4, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
 
        router = QCBRouter(qcb, dag, mapper)

    def test_larger_dag(self):
        from mapper import QCBMapper
        from qcb_graph import QCBGraph
        from qcb_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB

        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('a', 'd'))
        dag.add_gate(CNOT('b', 'c'))
        dag.add_gate(CNOT('d', 'b'))
        dag.add_gate(CNOT('c', 'a'))

        qcb = QCB(4, 4, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
 
        router = QCBRouter(qcb, dag, mapper)




    def test_complex_qcb(self):
        from mapper import QCBMapper
        from qcb_graph import QCBGraph
        from qcb_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB
        
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

        sym = ExternSymbol('T_Factory')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, factory_impl)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
    

if __name__ == '__main__':
    unittest.main()
