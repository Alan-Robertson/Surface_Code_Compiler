from functools import partial, cache
from surface_code_routing.symbol import Symbol, ExternSymbol, symbol_map, symbol_resolve
from surface_code_routing.scope import Scope
from surface_code_routing.dag import DAG, DAGNode

from surface_code_routing.qcb import QCB
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.allocator import Allocator
from surface_code_routing.compiled_qcb import CompiledQCB, compile_qcb

from surface_code_routing.instructions import INIT, RESET, CNOT, T_SLICE, Hadamard, Phase, local_Tdag, PREP, MEAS, X

from functools import partial
from surface_code_routing.lib_instructions import T_Factory, Toffoli, T_gate

toff_height = 14
toff_width = toff_height

qcb_size = 32

t_factory_l1 = T_Factory()
toffoli_gate = Toffoli

t_factory_l2 = T_Factory(t_factory_l1, height=8, width=10, t_gate=T_gate(t_factory_l1))
t_gate_l2 = T_gate(factory=t_factory_l2)

t_factory_l3 = T_Factory(t_factory_l2, height=11, width=12, t_gate=T_gate(t_factory_l2))
t_gate_l3 = T_gate(factory=t_factory_l3)



def T_Factory_DAG(*externs, t_gate=local_Tdag, **compiler_arguments):

        if 'router_kwargs' in compiler_arguments:
            if 'teleport' not in compiler_arguments:
                compiler_arguments['teleport'] = False
        else:
            router_kwargs = {'teleport': False}
            compiler_arguments['router_kwargs'] = router_kwargs 

        dag = DAG(Symbol('T_Factory', (), 'factory_out'))
        dag.add_gate(INIT(*['q_{i}'.format(i=i) for i in range(4)]))
        dag.add_gate(INIT(*['a_{i}'.format(i=i) for i in range(11)]))
        dag.add_gate(CNOT('q_3', *['a_{i}'.format(i=i) for i in range(1, 8)]))
        dag.add_gate(CNOT('q_2', *['a_{i}'.format(i=i) for i in (0, 2, 3, 4, 5, 8, 9)]))
        dag.add_gate(CNOT('q_1', *['a_{i}'.format(i=i) for i in (0, 1, 3, 4, 6, 8, 10)]))
        dag.add_gate(CNOT('q_0', *['a_{i}'.format(i=i) for i in (0, 1, 2, 4, 7, 9, 10)]))
        dag.add_gate(CNOT('factory_out', *('a_{i}'.format(i=i) for i in range(10, 3, -1))))

        for i in range(4):
            dag.add_gate(t_gate(f'q_{i}'))
            dag.add_gate(MEAS(f'q_{i}'))

        for i in range(11):
            dag.add_gate(t_gate(f'a_{i}'))
            dag.add_gate(MEAS(f'a_{i}'))

        dag.add_gate(X('factory_out'))
        return dag 

dag = T_Factory_DAG(t_factory_l1, t_gate=T_gate(t_factory_l1))
#dag.verbose = True
#print(dag.compile(1, *[t_factory_l1.instantiate() for _ in range(3)])[0])
