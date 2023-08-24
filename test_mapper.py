from functools import reduce
from utils import consume
from qcb import SCPatch
import unittest
from mapper import QCBMapper

class MapperTest(unittest.TestCase):
  
    def test_extern_qcb(self):
        from instructions import INIT, T
        from dag import DAG
        from symbol import Symbol, ExternSymbol
        from mapper import QCBMapper
        from qcb_graph import QCBGraph
        from qcb_tree import QCBTree
        from allocator import Allocator
        from qcb import QCB
        
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(T('a'))

        sym = ExternSymbol('T_Factory', 'factory_out')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, factory_impl)
        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)
 
        gate = dag.gates[-2]
        args = gate.get_symbol()
       
        assert mapper.dag_symbol_to_segment(args[0]).get_symbol().predicate == Symbol('T_Factory')
        assert mapper.dag_symbol_to_segment(args[1]).get_symbol() == SCPatch.REG 

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

        sym = ExternSymbol('T_Factory', 'factory_out')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, factory_impl)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
    
        mapper = QCBMapper(dag, tree)

        for dag_node in dag.gates:
            coordinates = mapper[dag_node]
            assert len(coordinates) > 0
            assert all(
                    map(lambda x: (type(x) is tuple 
                      and all(map(lambda y: type(y) is int, x))),
                    coordinates)
                    )

if __name__ == '__main__':
    unittest.main()
