import arithmetic_operations
import multiplier
import qmpa_to_sc

qcb_size = 32 
for i in range(1, 3):
    adder = multiplier.adder(24, 24, i, qmpa_to_sc.T_Factory()) 

    x = arithmetic_operations.qmpa_multiplication(1 << i, 1 << i)
    dag = qmpa_to_sc.circ_to_dag(x, 'mul')
    #try:
    qcb = multiplier.multiply(dag, qcb_size, qcb_size, adder, qmpa_to_sc.T_Factory())
    print(qcb_size, i, qcb.n_cycles(), qcb.space_time_volume())
    #except:
    #    pass
