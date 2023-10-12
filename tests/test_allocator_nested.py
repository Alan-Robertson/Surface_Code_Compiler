import numpy as np
import unittest
from functools import reduce

from surface_code_routing.utils import consume

from surface_code_routing.qcb import QCB, Segment, SCPatch
from surface_code_routing.symbol import Symbol, ExternSymbol
from surface_code_routing.scope import Scope
from surface_code_routing.dag import DAG
from surface_code_routing.allocator import Allocator, AllocatorError

from surface_code_routing.instructions import INIT, CNOT, Hadamard, PREP, MEAS, X
from surface_code_routing.lib_instructions import T, T_Factory


from surface_code_routing.dag import DAG
from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.allocator import Allocator
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.circuit_model import PatchGraph
from surface_code_routing.inject_rotations import RotationInjector

from surface_code_routing.compiled_qcb import CompiledQCB

from test_utils import CompiledQCBInterface


class SegmentTest(unittest.TestCase):

    def random_gates(self, dag):
        gate_chance = lambda x: (np.random.randint(1, x) == 1)

        for i in range(20):
            if gate_chance(10):
                targ = np.random.randint(0, n_registers)
                dag.add_gate(T(f"reg_{i}"))

            if gate_chance(10):
                targ = np.random.randint(0, io_width)
                dag.add_gate(T(f"io_{i}"))

            if gate_chance(5):
                targ = np.random.randint(0, io_width)
                dag.add_gate(Hadamard(f"io_{i}"))

            if gate_chance(5):
                targ = np.random.randint(0, n_registers)
                dag.add_gate(Hadamard(f"reg_{i}"))

            if gate_chance(8):
                ctrl = np.random.randint(0, n_registers)
                targ = np.random.randint(0, io_width)
                dag.add_gate(CNOT(ctrl, targ))

            if gate_chance(8):
                ctrl = np.random.randint(0, n_registers)
                targ = np.random.randint(0, n_registers)
                dag.add_gate(CNOT(ctrl, targ))

            if gate_chance(8):
                ctrl = np.random.randint(0, io_width)
                targ = np.random.randint(0, io_width)
                dag.add_gate(CNOT(ctrl, targ))



    def test_construct_T(self):
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


    def test_compile_T(self):
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

        qcb = QCB(5, 7, dag)
        allocator = Allocator(qcb)
        graph = QCBGraph(qcb)
        tree = QCBTree(graph)

        mapper = QCBMapper(dag, tree)
        circuit_model = PatchGraph(qcb.shape, mapper, None)
        rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)
        router = QCBRouter(qcb, dag, mapper, graph=circuit_model)
        compiled_qcb = CompiledQCB(qcb, router, dag)


    def test_extern_below_route(self):
        extern_sizes = [(2, 2), (3, 3), (1, 3), (2, 1), (4, 3), (4, 1), (3, 1), (4, 2), (1, 3), (4, 4)]
        n_registers = 1
        io_width = 4
        qcb_shape = [46, 45]


        factory = T_Factory(height=5, width=7)
        externs = [CompiledQCBInterface(f"TST_{i}", *extern_size) for extern_size in extern_sizes]

        g = DAG(Symbol('tst', list(f"io_{i}" for i in range(io_width))))
        g.add_gate(INIT(*[f'reg_{i}' for i in range(n_registers)]))
        self.random_gates(g)
        qcb = QCB(*qcb_shape, g)
        allocator = Allocator(qcb, factory, *externs)


    def test_extern_u_route(self):
        extern_sizes = [(3, 1), (1, 3), (1, 2), (4, 3), (2, 4), (3, 1), (2, 1), (3, 3), (2, 1), (4, 2)]
        n_registers = 26
        io_width = 1
        qcb_shape = [48, 53]

        factory = T_Factory(height=5, width=7)
        externs = [CompiledQCBInterface(f"TST_{i}", *extern_size) for extern_size in extern_sizes]

        g = DAG(Symbol('tst', list(f"io_{i}" for i in range(io_width))))
        g.add_gate(INIT(*[f'reg_{i}' for i in range(n_registers)]))
        self.random_gates(g)
        qcb = QCB(*qcb_shape, g)
        allocator = Allocator(qcb, factory, *externs)



    def test_random_externs(self): 
        
        for i in range(10):
            height = np.random.randint(6, 12)
            width = np.random.randint(6, 12)
            factory = T_Factory()

            rand_int = lambda: np.random.randint(1, 5)
            rand_size = lambda: np.random.randint(45, 60)
            
            
            io_width = rand_int()
            n_registers = np.random.randint(1, 30)

            n_externs = 10
            # These are junk testing externs
            externs = [CompiledQCBInterface(f"TST_{i}", rand_int(), rand_int()) for i in range(n_externs)]

            # Random size of IO channel
            g = DAG(Symbol('tst', list(f"io_{i}" for i in range(io_width))))
            g.add_gate(INIT(*[f'reg_{i}' for i in range(n_registers)]))
            self.random_gates(g)
            qcb_base = QCB(
                    rand_size(),
                    rand_size(),
                    g)
            try:
                allocator = Allocator(qcb_base, factory, *externs)
            except AllocatorError:
                pass
   


if __name__ == '__main__':
    unittest.main()
