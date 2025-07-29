from surface_code_routing.lib_instructions import T_gate, T_Factory

# Eps = 1e-3 
fact = T_Factory()
t_gate = T_gate(factory=fact)

print("1e-3:")  

# Eps = 1e-9
fact_nest_one = T_Factory(fact, height=10, width=29, t_gate=t_gate)
gate_nest_one = T_gate(factory=fact_nest_one)


