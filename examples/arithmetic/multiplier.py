import qmpa
import qmpa_to_sc
import arithmetic_operations
from surface_code_routing.lib_instructions import Toffoli
from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from itertools import chain
from surface_code_routing.compiled_qcb import compile_qcb
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard, SWAP


def adder(height, width, n_bits, *externs, **compiler_arguments):
    x = arithmetic_operations.qmpa_addition(1 << n_bits, 1 << n_bits)
    registers = ['reg_{}'.format(i) for i in range(n_bits * 2 - 1)]
    symbol = Symbol(f'ADD_{n_bits}', registers, registers)
    dag = qmpa_to_sc.circ_to_dag(x, symbol)

    return compile_qcb(dag, height, width, *externs, **compiler_arguments)



def multiply(height, width, n_bits, adder_qcb, *externs, **compiler_arguments):
    
    def adder(reg_a, reg_b):
        dag = adder_qcb.instruction(args = reg_a + reg_b, targs=reg_a + reg_b)
        return dag

    reg_a = ['a_{i}'.format(i=i) for i in range(n_bits)]
    reg_b = ['b_{i}'.format(i=i) for i in range(n_bits)]
    reg_target = ['targ_{i}'.format(i=i) for i in range(2 * n_bits + 1)]
    reg_cpy = ['cpy_{i}'.format(i=i) for i in range(2 * n_bits + 1)]

    dag = DAG(Symbol('mul'))

    for r in chain(reg_a, reg_b, reg_target, reg_cpy):
        dag.add_gate(INIT(r))

    for i in range(n_bits):
        
        # CPY
        for j in range(n_bits):
            dag.add_gate(Toffoli(f'a_{i}', f'b_{j}', f'cpy_{j}'))

        # Shift and ADD
        dag.add_gate(adder(['cpy_{}'.format(j) for j in range(n_bits)], ['targ_{}'.format(j) for j in range(i, n_bits + i)]))

        # CPY
        for j in range(n_bits):
            dag.add_gate(Toffoli(f'a_{i}', f'b_{j}', f'cpy_{j}'))

    return compile_qcb(dag, height, width, adder_qcb,  *externs, **compiler_arguments)


    
