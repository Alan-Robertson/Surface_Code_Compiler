import traceback

from test_tikz_helper import *
from test_circuit import *

from allocator import QCB
from graph_prune import QCBPrune
from mapper import QCBMapper

qcb = QCB(height, width, io, g.n_blocks, *msf_templates)

# Allocate pass
try:
    qcb.allocate()
    print("Allocate success")
except Exception as e:
    traceback.print_exc()
    print("Allocation failed, aborting.")
    exit()

print_qcb(qcb.segments, "main_allocated.tex")

# Optimise pass
try:
    qcb.optimise(g)
    print("Optimise success")
except Exception as e:
    traceback.print_exc()
    print("Allocation failed, aborting.")
    exit()

print_qcb(qcb.segments, 'main_optimised.tex')

# Generating connectivity graph
try:
    prune = QCBPrune(qcb.segments)
    prune.map_to_grid()
except Exception as e:
    traceback.print_exc()
    print("Pruning connectivity graph failed, aborting")
    exit()

print_connectivity_graph(prune.grid_segments, 'main_connectivity.tex')


try:
    mapper = QCBMapper(prune.grid_segments)
    root = mapper.generate_mapping_tree()
except Exception as e:
    traceback.print_exc()
    print("Mapping tree generation failed, aborting")
    exit()

print_mapping_tree(root, 'main_mapping_tree.tex')



try:
    mapper.map_all(g, qcb)
except Exception as e:
    traceback.print_exc()
    print("Qubit/msf mapping failed, aborting")
    exit()

print_mapping_tree(root, 'main_qubit_mapping.tex')



from router import QCBRouter
router = QCBRouter(qcb, g, mapper.generate_mapping_dict(), m=mapper.labels)

try:
    router.route_all()
except Exception as e:
    traceback.print_exc()
    print("Routing phase failed, aborting")
    exit()

# router.debug()
# print(router.active.queue)
# print(router.finished)
# print(router.waiting)
# print_inst_locks(qcb.segments, g.layers)

from test_tikz_helper2 import print_inst_locks2
print_inst_locks2(qcb.segments, g.gates, 'main_frames.tex')
