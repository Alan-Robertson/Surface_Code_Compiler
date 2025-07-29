import sys
import arithmetic_operations
import qmpa_to_sc

from surface_code_routing.lib_instructions import T_gate, T_Factory, T


print("QCB Size, Cycles, Volume")

# These may be big
sys.setrecursionlimit(int(10e5))

# Eps = 1e-3 
fact_zero = T_Factory(height=5, width=8)
gate_zero = T_gate(factory=fact_zero)

# Eps = 1e-9
fact_one_min_footprint = T_Factory(fact_zero, height=10, width=8, t_gate=gate_zero)
gate_one_min_footprint = T_gate(factory=fact_one_min_footprint)

print("ADDER")

fact = fact_one_min_footprint
gate = T_gate(factory=fact)

qcb_size = max(fact.height + 2, fact.width + 2) 
x = arithmetic_operations.qmpa_addition(2, 2)
dag = qmpa_to_sc.circ_to_dag(x, 'add', T=gate)
qcb = qmpa_to_sc.compile_qcb(dag, qcb_size, qcb_size, fact)
print(qcb_size, qcb.n_cycles(), qcb.space_time_volume(), len(qcb.dag.physical_externs))
