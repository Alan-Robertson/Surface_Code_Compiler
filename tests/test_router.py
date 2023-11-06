from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.symbol import Symbol, ExternSymbol

from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.allocator import Allocator
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.circuit_model import PatchGraph
from surface_code_routing.inject_rotations import RotationInjector

from surface_code_routing.bind import RouteBind

from surface_code_routing.lib_instructions import T_Factory, T, Toffoli

import unittest

from test_utils import QCBInterface, QCBSegmentInterface, MapperInterface, GateInterface

class RouterTest(unittest.TestCase):

    def test_simple_route(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b'))
        dag.add_gate(CNOT('a', 'b'))

        qcb = QCB(4, 4, dag)
        allocator = Allocator(qcb)
        qcb.allocator = allocator

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)

        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)
        router = QCBRouter(qcb, dag, mapper, graph=circuit_model, auto_route=False)
    
        for gate in dag.gates:
            bound_gate = RouteBind(gate, mapper[gate])
            address = mapper[gate]
            route_found, route = router.find_route(bound_gate, address)
            assert route_found

    def test_two_routes(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(CNOT('a', 'c'))
        dag.add_gate(CNOT('a', 'd'))
        dag.add_gate(CNOT('b', 'c'))
        dag.add_gate(CNOT('b', 'd'))
        dag.add_gate(CNOT('c', 'd'))
       
        qcb = QCB(3, 3, dag)
        allocator = Allocator(qcb)
        qcb.allocator = allocator

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)

        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)
        router = QCBRouter(qcb, dag, mapper, graph=circuit_model, auto_route=False)
    
        for gate in dag.gates:
            bound_gate = RouteBind(gate, mapper[gate])
            address = mapper[gate]
            route_found, route = router.find_route(bound_gate, address)
            if gate.rotates():
                router.rotate(gate, router.mapper[gate])

            assert route_found

#    def test_lock_unlock(self):
#        dag = DAG(Symbol('Test'))
#        dag.add_gate(INIT('a', 'b', 'c', 'd'))
#        dag.add_gate(CNOT('a', 'b'))
#
#        qcb = QCB(3, 3, dag)
#        allocator = Allocator(qcb)
#        qcb.allocator = allocator
#
#        graph = QCBGraph(qcb)
#        tree = QCBTree(graph)
#        mapper = QCBMapper(dag, tree)
#
#        circuit_model = PatchGraph(qcb.shape, mapper, None)
#        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)
#        router = QCBRouter(qcb, dag, mapper, graph=circuit_model, auto_route=False)
#    
#        for gate in dag.gates:
#            bound_gate = RouteBind(gate, mapper[gate])
#            address = mapper[gate]
#            route_found, route = router.find_route(bound_gate, address)
#            if gate.rotates():
#                router.rotate(gate, router.mapper[gate])
#
#            assert route_found
#
#
#        gate_a = GateInterface(Symbol('gate_a'))
#        route_found, route = router.find_route(gate_a, [[0, 0], [0, 2]])
#        assert route_found
#        assert route == [router.graph[0, 0], router.graph[0, 1], router.graph[0, 2]]
#        router.active_gates.add(gate_a)
#
#        gate_b = GateInterface(Symbol('gate_b'))
#        route_found, route = router.find_route(gate_b, [[1, 0], [1, 2]])
#        assert route_found
#        assert route == [router.graph[1, 0], router.graph[1, 1], router.graph[1, 2]]
#
#        gate_a = GateInterface(Symbol('gate_a'))
#        route_found, route = router.find_route(gate_a, [[1, 0], [1, 2]])
#        assert route_found
#        assert route == [router.graph[1, 0], router.graph[1, 1], router.graph[1, 2]]
#        router.active_gates.add(gate_a)
#
#        gate_b = GateInterface(Symbol('gate_b'))
#        route_found, route = router.find_route(gate_b, [[0, 1], [2, 1]])
#        assert not route_found
#        
#        # Unlock
#        router.active_gates.remove(gate_a)
#
#        gate_b = GateInterface(Symbol('gate_b'))
#        route_found, route = router.find_route(gate_b, [[0, 1], [2, 1]])
#        assert route_found
#        assert route == [router.graph[0, 1], router.graph[1, 1], router.graph[2, 1]]
#
#
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
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)

        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)



    def test_larger_dag(self):
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
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)

        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)


    def test_extern_qcb(self):
        
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(T('a'))
        dag.add_gate(CNOT('a', 'b'))

        qcb = QCB(15, 10, dag)
        allocator = Allocator(qcb, T_Factory())

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)

        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)


    def test_complex_no_extern(self):
        
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('c', 'a'))
        dag.add_gate(CNOT('b', 'd'))
        dag.add_gate(CNOT('c', 'd'))
        dag.add_gate(CNOT('c', 'a'))
        dag.add_gate(CNOT('b', 'd'))

        qcb = QCB(15, 15, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)
        router = QCBRouter(qcb, dag, mapper)

    def test_ancillae(self):
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(Hadamard('c'))
        dag.add_gate(Hadamard('d'))
        dag.add_gate(CNOT('a', 'b'))
        dag.add_gate(Hadamard('a'))
        dag.add_gate(Hadamard('b'))
        dag.add_gate(CNOT('c', 'd'))

        qcb = QCB(3, 4, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)

        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)


    def test_complex_qcb(self):
        
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

        qcb = QCB(16, 16, dag)
        allocator = Allocator(qcb, T_Factory())

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)

        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)

    def test_io_simple(self):
        # Dummy T Factory
        dag = DAG(Symbol('T_Factory', 'factory_out'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(CNOT('a', 'factory_out'))

        qcb = QCB(4, 5, dag)
        allocator = Allocator(qcb)

        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)

        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)


if __name__ == '__main__':
    unittest.main()
