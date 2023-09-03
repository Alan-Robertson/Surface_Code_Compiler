from functools import reduce
from utils import consume
from qcb import SCPatch
import unittest
from mapper import QCBMapper

from lib_instructions import T_Factory
from instructions import INIT, T, CNOT
from dag import DAG
from symbol import Symbol, ExternSymbol
from mapper import QCBMapper
from qcb_graph import QCBGraph
from qcb_tree import QCBTree
from allocator import Allocator
from qcb import QCB
     
class MapperTest(unittest.TestCase):
  
    def test_extern_qcb(self):

        t_fact = T_Factory()
        dag = DAG(Symbol('Test'))
        dag.add_gate(INIT('a', 'b', 'c', 'd'))
        dag.add_gate(t_fact.instruction((), ('a')))
        dag.add_gate(t_fact.instruction((), ('a')))

        #dag.add_gate(CNOT('a', 'b', 'c', 'd'))

        qcb_base = QCB(15, 10, dag)
        allocator = Allocator(qcb_base, t_fact)
        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)
        mapper = QCBMapper(dag, tree)
 
        gate = dag.gates[-2]
        args = gate.get_symbol()
      
        assert gate.get_symbol().predicate == Symbol('T_Factory')
        assert mapper.dag_symbol_to_segment(args[0]).get_symbol().predicate == Symbol('T_Factory')
        assert mapper.dag_symbol_to_segment(args[1]).get_symbol() == SCPatch.REG 

#    def test_reg_mapping(self):
#        from qcb_graph import QCBGraph
#        from qcb_tree import QCBTree
#        from allocator import Allocator
#        from qcb import QCB
#        from dag import DAG
#        from instructions import INIT, CNOT, T, Toffoli
#        from symbol import Symbol, ExternSymbol
#
#        dag = DAG(Symbol('Test'))
#        dag.add_gate(INIT('a', 'b', 'c', 'd'))
#        dag.add_gate(CNOT('a', 'b'))
#        dag.add_gate(CNOT('c', 'd'))
#        dag.add_gate(T('a'))
#        dag.add_gate(CNOT('a', 'b'))
#        dag.add_gate(Toffoli('a', 'b', 'c'))
#        dag.add_gate(T('a'))
#        dag.add_gate(T('a'))
#        dag.add_gate(T('c'))
#        dag.add_gate(T('d'))
#        dag.add_gate(CNOT('c', 'd'))
#        dag.add_gate(CNOT('c', 'a'))
#        dag.add_gate(CNOT('b', 'd'))
#        dag.add_gate(T('a'))
#        dag.add_gate(T('c'))
#        dag.add_gate(Toffoli('a', 'b', 'c'))
#        dag.add_gate(CNOT('c', 'd'))
#        dag.add_gate(CNOT('c', 'a'))
#        dag.add_gate(CNOT('b', 'd'))
#
#        sym = ExternSymbol('T_Factory', 'factory_out')
#        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}), io={sym('factory_out'):0})
#
#        qcb_base = QCB(15, 10, dag)
#        allocator = Allocator(qcb_base, factory_impl)
#
#        graph = QCBGraph(qcb_base)
#        tree = QCBTree(graph)
#    
#        mapper = QCBMapper(dag, tree)
#
##        for dag_node in dag.gates:
##            coordinates = mapper[dag_node]
##            assert len(coordinates) > 0
##            assert all(
##                    map(lambda x: (type(x) is tuple 
##                      and all(map(lambda y: type(y) is int, x))),
##                    coordinates)
##                    )
##
#    def test_io_simple(self):
#        from dag import DAG
#        from instructions import INIT, CNOT, T, Toffoli
#        from qcb import QCB
#        from allocator import Allocator
#        from qcb_graph import QCBGraph
#        from qcb_tree import QCBTree
#        from symbol import Symbol
#
#        # Dummy T Factory
#        dag = DAG(Symbol('T_Factory', 'factory_out'))
#        dag.add_gate(INIT('a', 'b', 'c', 'd'))
#
#        qcb = QCB(4, 5, dag)
#        allocator = Allocator(qcb)
#
#        graph = QCBGraph(qcb)
#        tree = QCBTree(graph)
#
#        mapper = QCBMapper(dag, tree)
#
#        for dag_node in dag.gates:
#            coordinates = mapper[dag_node]
#            assert len(coordinates) > 0
#            assert all(
#                    map(lambda x: (type(x) is tuple 
#                      and all(map(lambda y: type(y) is int, x))),
#                    coordinates)
#                    )
#
#
if __name__ == '__main__':
    unittest.main()
