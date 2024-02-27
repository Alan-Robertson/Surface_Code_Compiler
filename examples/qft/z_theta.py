from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import CPHASE_theta, Z_theta
from surface_code_routing.compiled_qcb import compile_qcb

j = 512
for i in range(1, j // 2):
    dag = DAG('')
    dag.add_gate(INIT('x'))
    dag.add_gate(Z_theta(i, j, precision=int(np.log2(j) + 1))('x'))
    qcb = compile_qcb(dag, 8, 8, fact)
    print(i, qcb.n_cycles(), len(qcb.dag.physical_externs), file=file)
