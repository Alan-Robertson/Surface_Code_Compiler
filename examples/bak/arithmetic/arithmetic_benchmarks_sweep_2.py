import sys
import arithmetic_operations
import qmpa_to_sc

from surface_code_routing.lib_instructions import T_gate, T_Factory


print("Register Size, Height, Width, Cycles, Volume, Factories")

# These may be big
sys.setrecursionlimit(int(10e5))


# Eps = 1e-3 
fact_zero = T_Factory(height=5, width=8)
gate_zero = T_gate(factory=fact_zero)


# Eps = 1e-9
fact_one_min_footprint = T_Factory(fact_zero, height=10, width=8, t_gate=gate_zero)
#gate_one_min_footprint = T_gate(factory=fact_one_min_vol)

#fact_one_min_sv = T_Factory(fact_zero, height=10, width=28, t_gate=gate_zero)
#gate_one_min_sv = T_gate(factory=fact_one_min_sv)

#fact_one_min_cycles = T_Factory(fact_zero, height=22, width=30, t_gate=gate_zero) 
#gate_one_min_cycles = T_gate(factory=fact_one_min_cycles)

## Eps = 1e-27
#fact_two_min_footprint = T_Factory(fact_one_min_cycles, height=28, width=32, t_gate=gate_one_min_cycles) 
#gate_two_min_footprint = T_gate(factory=fact_two_min_footprint)
#
#fact_two_min_cycles = T_Factory(fact_one_min_cycles, height=48, width=64, t_gate=gate_one_min_cycles) 
#gate_two_min_cycles = T_gate(factory=fact_two_min_footprint)

print("ADDER")

fact = fact_one_min_footprint
gate = T_gate(factory=fact)

for height in [16, 24, 32, 48, 56, 64]:
    for width in range(16, 64, 2):
        x = arithmetic_operations.qmpa_addition(1 << 31, 1 << 31)
        dag = qmpa_to_sc.circ_to_dag(x, 'add', T=gate)
        #try:
        qcb = qmpa_to_sc.compile_qcb(dag, height, width, fact)
        print(32, height, width, qcb.n_cycles(), qcb.space_time_volume(), len(qcb.dag.physical_externs))
        #except:
        #    print("FAILED")
        #    break
