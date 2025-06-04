from surface_code_routing.lib_instructions import T_Factory, T_gate

# Calls the default factory
t_factory_l1 = T_Factory()

# Construct level 2 from level 1
t_factory_l2 = T_Factory(t_factory_l1, height=8, width=10, t_gate=T_gate(t_factory_l1))
t_gate_l2 = T_gate(factory=t_factory_l2)

# Construct level 3 from level 2
t_factory_l3 = T_Factory(t_factory_l2, height=11, width=12, t_gate=T_gate(t_factory_l2))
t_gate_l3 = T_gate(factory=t_factory_l3)

# List of factories 
t_factories = (t_factory_l1, t_factory_l2, t_factory_l3)
