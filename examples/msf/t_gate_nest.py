from surface_code_routing.lib_instructions import T_gate, T_Factory

fact = T_Factory(height=5, width=8)
t_gate = T_gate(factory=fact)
fact_nest_one = T_Factory(fact, height=10, width=29, t_gate=t_gate)
gate_nest_one = T_gate(factory=fact_nest_one)

# Using the nested T gate


facts = [T_Factory(height=14, width=4), T_Factory(), T_Factory(height=6, width=6)]
t_gate = T_gate(factory=fact)


for f, fact in enumerate(facts):
    t_gate = T_gate(factory=fact)
    for i in range(8, 32, 2):
        for j in range(8, 32, 2):
            try:
                fact_nest_one = T_Factory(fact, height=i, width=j, t_gate=t_gate)
                print(f, i, j, fact_nest_one.n_cycles(), file=file)
            except:
                pass

print("Nest One")

facts = [T_Factory(height=i, width=j) for (i, j) in [(3, 15), (4, 9), (5, 6), (6, 5), (8, 4), (14, 3)]]
t_gates = list(T_gate(factory=f) for f in facts)
 
for f, fact in enumerate(facts):
    t_gate = T_gate(factory=fact)
    for i in range(8, 33, 4):
        print(i, end=' ', flush=True)
        for j in range(8, 33, 4):
            try:
                fact_nest_one = T_Factory(fact, height=i, width=j, t_gate=t_gates[f])
                print(f, i, j, fact_nest_one.n_cycles(), file=file)
            except:
                pass
