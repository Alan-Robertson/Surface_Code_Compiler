from surface_code_routing.lib_instructions import T_gate, T_Factory
import qft
import sys

# These may be big
sys.setrecursionlimit(int(10e5))

fact = T_Factory()
t_gate = T_gate(factory=fact)


# Nest One
for i in range(10, 120):
    fact_nest = T_Factory(fact, height=i, width=i, t_gate=t_gate)
    gate_nest = T_gate(factory=fact_nest)

    route_delay = 0
    if 'ROUTE' in fact_nest.delays():
        route_delay = fact_nest.delays()['ROUTE']
    
    fact_delay = 0
    if 'T_Factory' in fact_nest.delays(): 
        fact_delay = fact_nest.delays()['T_Factory']

    print(i, fact_nest.space_time_volume(), fact_nest.n_cycles(), route_delay, fact_delay) 



print("##########")

opt_one = 19 

fact = T_Factory(fact, height=opt_one, width=opt_one, t_gate=t_gate)
t_gate = T_gate(factory=fact)

for i in range(22, 120, 2):
    fact_nest = T_Factory(fact, height=i, width=i, t_gate=t_gate)
    gate_nest = T_gate(factory=fact_nest)

    route_delay = 0
    if 'ROUTE' in fact_nest.delays():
        route_delay = fact_nest.delays()['ROUTE']
    
    fact_delay = 0
    if 'T_Factory' in fact_nest.delays(): 
        fact_delay = fact_nest.delays()['T_Factory']

    print(i, fact_nest.space_time_volume(), fact_nest.n_cycles(), route_delay, fact_delay) 


print("##########")

opt_two = 30 

fact = T_Factory(fact, height=opt_two, width=opt_two, t_gate=t_gate)
t_gate = T_gate(factory=fact)

for i in range(opt_two + 2, 120, 2):
    try:
        fact_nest = T_Factory(fact, height=i, width=i, t_gate=t_gate)
        gate_nest = T_gate(factory=fact_nest)

        route_delay = 0
        if 'ROUTE' in fact_nest.delays():
            route_delay = fact_nest.delays()['ROUTE']
        
        fact_delay = 0
        if 'T_Factory' in fact_nest.delays(): 
            fact_delay = fact_nest.delays()['T_Factory']

        print(i, fact_nest.space_time_volume(), fact_nest.n_cycles(), route_delay, fact_delay) 

    except:
        pass
