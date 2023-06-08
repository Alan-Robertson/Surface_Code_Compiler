
from test_tikz_helper import *


import allocator
from msf import MSF
import dag
import msf

t_fact = msf.MSF('T', (5, 3), 19)
q_fact = msf.MSF('Q', (4, 4), 15)


g = dag.DAG(50)
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

print_qcb(qcb.segments, 'allocatora.tex')


def _validate(self):
    all_segs = set.union(*map(lambda s: set.union(*s.edges().values()), self.segments))
    return len(all_segs - self.segments) == 0


from graph_prune import QCBPrune
prune = QCBPrune(qcb.segments)

try:
    prune.map_to_grid()
except Exception as e:
    traceback.print_exc()

print_qcb(prune.grid_segments, 'allocatorb.tex')
print_connectivity_graph(prune.grid_segments, 'graph.tex')


print("validation", _validate(qcb))