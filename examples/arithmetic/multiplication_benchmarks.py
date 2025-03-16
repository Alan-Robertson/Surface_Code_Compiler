import arithmetic_operations
import qmpa_to_sc

print("QCB Size, Register Size, Cycles, Volume")

for qcb_size in [32, 64]:
    for i in range(1, 5):
        x = arithmetic_operations.qmpa_multiplication(1 << i, 1 << i)
        dag = qmpa_to_sc.circ_to_dag(x, 'mul')
        qcb = qmpa_to_sc.compile_qcb(dag, qcb_size, qcb_size, qmpa_to_sc.T_Factory())
        print(qcb_size, i, qcb.n_cycles(), qcb.space_time_volume(), qcb.router.delays)
