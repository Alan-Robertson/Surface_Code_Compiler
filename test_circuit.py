import dag
import msf

height = 15
width = 20
io = 16

t_fact = msf.MSF('T', (5, 3), 19)
q_fact = msf.MSF('Q', (4, 4), 15)


msf_templates = [t_fact, q_fact]

g = dag.DAG(20)
g.add_gate(2, 'T', magic_state=True)
g.add_gate(3, 'T', magic_state=True)
g.add_gate(0, 'Q', magic_state=True)
g.add_gate(0, 'Z')
for i in range(10):
    g.add_gate([0, 1], 'CNOT')
    g.add_gate([0, 1], 'CNOT')
    g.add_gate([0, 1], 'CNOT')
    g.add_gate([0, 1], 'CNOT')
    g.add_gate(1, 'Z')
    g.add_gate([0, 1], 'CNOT')
    g.add_gate(2, 'Z')
    g.add_gate(2, 'Z')
    g.add_gate(2, 'Z')
    g.add_gate([2, 3], 'CNOT')
    g.add_gate([0, 2], 'CNOT')
    g.add_gate(1, 'Z')
    g.add_gate([0, 2], 'CNOT')
    g.add_gate([2, 3], 'CNOT')
g.add_gate(2, 'T', magic_state=True)
g.add_gate(3, 'T', magic_state=True)
g.add_gate(0, 'Q', magic_state=True)
#g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')