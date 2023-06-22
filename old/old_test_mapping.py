
import allocator
import dag
import msf

from test_tikz_helper import *

t_fact = msf.MSF('T', (5, 3), 19)
q_fact = msf.MSF('Q', (4, 4), 15)


g = dag.DAG(40)
g.add_gate(2, 'T', magic_state=True)
g.add_gate(3, 'T', magic_state=True)
g.add_gate(0, 'Q', magic_state=True)
g.add_gate(0, 'Z')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')
g.add_gate(2, 'Z')
g.add_gate(2, 'Z')
g.add_gate(2, 'Z')
#g.add_gate([2, 3], 'CNOT')
g.add_gate([0, 2], 'CNOT')
#g.add_gate(1, 'Z')
g.add_gate([0, 2], 'CNOT')
g.add_gate([2, 3], 'CNOT')
g.add_gate(2, 'T', magic_state=True)
g.add_gate(3, 'T', magic_state=True)
g.add_gate(0, 'Q', magic_state=True)
#g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')


qcb = allocator.QCB(15, 20, 16, g.n_blocks, t_fact, q_fact)
import traceback


try:
    qcb.allocate()
    print("Allocate success")
    try:
        qcb.optimise(g)
    except Exception as e:
        traceback.print_exc()

    print("Optimise success")
except Exception as e:
    traceback.print_exc()

print_qcb(qcb.segments, 'mapper.tex')


from graph_prune import QCBPrune
from mapper import QCBMapper
try:
    prune = QCBPrune(qcb.segments)
    prune.map_to_grid()
    mapper = QCBMapper(prune.grid_segments)
    root = mapper.generate_mapping_tree()
except Exception as e:
    traceback.print_exc()

print_connectivity_graph(prune.grid_segments, 'mapperc.tex')
print_mapping_tree(root, 'graph.tex')


conj, m_conj, minv_conj = g.calculate_conjestion()
prox, m_prox, minv_prox = g.calculate_proximity()

assert m_conj == m_prox
assert minv_conj == minv_prox

mapper.map_qubits(conj, prox, m_conj, minv_conj)

print_mapping_tree(root, 'graph.tex')

# print(mapper.qubit_mapping)
