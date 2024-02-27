for i in range(3, 5):
    x = arithmetic_operations.qmpa_addition(1 << i, 1 << i )
    dag = qmpa_to_sc.circ_to_dag(x, 'div')
    qcb = qmpa_to_sc.compile_qcb(dag, 64, 64, qmpa_to_sc.T_Factory())
    print(i, qcb.n_cycles())
