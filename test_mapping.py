
import allocator
import dag
import msf

from test_tikz_helper import *

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

try:
    qcb.map_to_grid()
    qcb.generate_mapping_tree()
except Exception as e:
    traceback.print_exc()

print_qcb(qcb.grid_segments, 'allocatorb.tex')
print_mapping_tree(next(iter(qcb.mapping_forest)), 'graph.tex')

def _validate(self):
    all_segs = set.union(*map(lambda s: set.union(*s.edges().values()), self.segments))
    return len(all_segs - self.segments) == 0
print(_validate(qcb))
