import dag
import msf

t_fact = msf.MSF('T', (5, 3), 5)

g = dag.DAG(4)
g.add_gate(2, 'T', magic_state=True)
g.add_gate(3, 'T', magic_state=True)
g.add_gate(0, 'Z')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')
g.add_gate(2, 'Z')
g.add_gate(2, 'Z')
g.add_gate(2, 'Z')
#g.add_gate([2, 3], 'CNOT')
g.add_gate([0, 2], 'CNOT')
#g.add_gate(1, 'Z')
g.add_gate([0, 2], 'CNOT')
g.add_gate([2, 3], 'CNOT')
#g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')

