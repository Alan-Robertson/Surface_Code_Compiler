from surface_code_routing.lib_instructions import T_gate, T_Factory
import qft

fact = T_Factory(height=5, width=8)
t_gate = T_gate(factory=fact)
fact_nest_one = T_Factory(fact, height=10, width=29, t_gate=t_gate)
gate_nest_one = T_gate(factory=fact_nest_one)
x = qft.qft(3, 20, 10, precision=3, extern_allocation_method='static', gates={'T':gate_nest_one}, t_factory=fact_nest_one, verbose=False)
