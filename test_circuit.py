import dag
import msf

height = 10
width = 10
io = 3

t_fact = msf.MSF('T', (5, 3), 19)
q_fact = msf.MSF('Q', (4, 4), 15)


msf_templates = [t_fact, q_fact]

g = dag.DAG(20)

import random
random.seed(0)

for i in range(200):
    gate_type = random.choice(["CNOT"] * 60 + ["T", "Q"] +  ["Z"] * 10)
    if gate_type == "CNOT":
        g.add_gate(targs=random.choices(range(20), k=2), data="CNOT")
    elif gate_type == "Z":
        g.add_gate(random.choice(range(20)), "Z")
    else:
        g.add_gate(random.choice(range(20)), gate_type, magic_state=True)


# Old test
# g.add_gate(2, 'T', magic_state=True)
# g.add_gate(3, 'T', magic_state=True)
# g.add_gate(0, 'Q', magic_state=True)
# g.add_gate(0, 'Z')
# for i in range(10):
#     g.add_gate([0, 1], 'CNOT')
#     g.add_gate([0, 1], 'CNOT')
#     g.add_gate([0, 1], 'CNOT')
#     g.add_gate([0, 1], 'CNOT')
#     g.add_gate(1, 'Z')
#     g.add_gate([0, 1], 'CNOT')
#     g.add_gate(2, 'Z')
#     g.add_gate(2, 'Z')
#     g.add_gate(2, 'Z')
#     g.add_gate([2, 3], 'CNOT')
#     g.add_gate([0, 2], 'CNOT')
#     g.add_gate(1, 'Z')
#     g.add_gate([0, 2], 'CNOT')
#     g.add_gate([2, 3], 'CNOT')
# g.add_gate(2, 'T', magic_state=True)
# g.add_gate(3, 'T', magic_state=True)
# g.add_gate(0, 'Q', magic_state=True)
# #g.add_gate(1, 'Z')
# g.add_gate([0, 1], 'CNOT')