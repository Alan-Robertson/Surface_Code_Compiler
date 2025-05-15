from surface_code_routing.lib_instructions import T_gate, T_Factory


# Eps = 1e-3 
# Constant cycle count
# Space time volume minima at height 5, width=8 
#for height in range(5, 10):
#    for width in range(5, 10):
#        try:
#            fact = T_Factory(height=height, width=width)
#            t_gate = T_gate(factory=fact)
#            print(height, width, fact.space_time_volume(), fact.n_cycles())
#        except:
#            pass

## Eps = 1e-3
fact_zero = T_Factory(height=5, width=8)
gate_zero = T_gate(factory=fact_zero)


#for height in range(10, 33, 2):
#    for width in range(10, 33, 2):
#        try:
#            fact = T_Factory(fact_zero, height=height, width=width, t_gate=gate_zero)
#            #t_gate = T_gate(factory=fact)
#            if fact.n_cycles() < 45:
#                print(height, width, height * width, fact.space_time_volume(), fact.n_cycles())
#        except:
#            pass


## Eps = 1e-9
fact_one_min_sv = T_Factory(fact_zero, height=10, width=28, t_gate=gate_zero)
gate_one_min_sv = T_gate(factory=fact_one_min_sv)

fact_one_min_cycles = T_Factory(fact_zero, height=22, width=30, t_gate=gate_zero) 
gate_one_min_cycles = T_gate(factory=fact_one_min_cycles)

## Eps = 1e-27
for height in range(24, 65, 4):
    for width in range(32, 65, 4):
        try:
            fact = T_Factory(fact_one_min_cycles, height=height, width=width, t_gate=gate_one_min_cycles)
            print(height, width, height * width, fact.space_time_volume(), fact.n_cycles())
        except:
            pass

fact_two_min_footprint = T_Factory(fact_one_min_cycles, height=28, width=32, t_gate=gate_one_min_cycles) 
gate_two_min_footprint = T_gate(factory=fact_two_min_footprint)





#
## Using the nested T gate
#facts = [T_Factory(height=14, width=4), T_Factory(), T_Factory(height=6, width=6)]
#t_gate = T_gate(factory=fact)
#

#for f, fact in enumerate(facts):
#    t_gate = T_gate(factory=fact)
#    for i in range(8, 32, 2):
#        for j in range(8, 32, 2):
#            try:
#                fact_nest_one = T_Factory(fact, height=i, width=j, t_gate=t_gate)
#                print(f, i, j, fact_nest_one.n_cycles(), file=file)
#            except:
#                pass
#
#print("Nest One")
#
#facts = [T_Factory(height=i, width=j) for (i, j) in [(3, 15), (4, 9), (5, 6), (6, 5), (8, 4), (14, 3)]]
#t_gates = list(T_gate(factory=f) for f in facts)
# 
#for f, fact in enumerate(facts):
#    t_gate = T_gate(factory=fact)
#    for i in range(8, 33, 4):
#        print(i, end=' ', flush=True)
#        for j in range(8, 33, 4):
#            try:
#                fact_nest_one = T_Factory(fact, height=i, width=j, t_gate=t_gates[f])
#                print(f, i, j, fact_nest_one.n_cycles(), file=file)
#            except:
#                pass
