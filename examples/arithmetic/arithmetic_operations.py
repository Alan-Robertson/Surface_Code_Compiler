import numpy as np
from functools import reduce, partial

from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.lib_instructions import T_Factory, CSWAP

from surface_code_routing.compiled_qcb import compile_qcb

import qmpa
import qmpa_to_sc


def qmpa_in_place_operation(operation, readout_assert, *values, register_size = None):
    assert all(lambda x: type(x) is int for x in values)

    if register_size is None:
        register_size = int(np.ceil(np.log2(max(values))))

    circ = qmpa.circuit.Circuit()
    
    reg_carry = circ.register(1, 'carry')
    registers = [circ.register(register_size + i, 'reg_{}'.format(i), value) for i, value in enumerate(values)]
               
    reduce(partial(operation(circ), reg_carry=reg_carry), registers) 
    
    return circ


def qmpa_multiplication(*values, register_size = None):
    assert all(lambda x: type(x) is int for x in values)


    if register_size is None:
        register_size = int(np.ceil(np.log2(max(values)))) + 1

    circ = qmpa.circuit.Circuit()
    
    reg_carry = circ.register(1, 'carry')
    registers = [circ.register(register_size, 'reg_{}'.format(i), value) for  i, value in enumerate(values)]
              
    prev_reg = registers[0]
    for register in registers[1:]:
       prev_reg = circ.multiply(prev_reg, register) 
    
    assert reduce(lambda x, y: x * y, values) == circ.readout(prev_reg)[0] 
    return circ


qmpa_addition = partial(qmpa_in_place_operation, lambda x: x.add, lambda vals: reduce(lambda x, y: x + y, vals))
qmpa_subtraction = partial(qmpa_in_place_operation, lambda x: x.subtract, lambda vals: reduce(lambda x, y: x - y, vals))

def qmpa_division(*values, register_sizes = None):
    assert all(lambda x: type(x) is int for x in values)


    if register_sizes is None:
        register_sizes = [int(np.ceil(np.log2(i))) + 1 for i in values]

    circ = qmpa.circuit.Circuit()
    
    reg_carry = circ.register(1, 'carry')
    registers = [circ.register(register_size, 'reg_{}'.format(i), value) for  i, (value, register_size) in enumerate(zip(values, register_sizes))]
              
    prev_reg = registers[0]
    for register in registers[1:]:
       prev_reg = circ.divide(prev_reg, register) 
    
    return circ


qmpa_addition = partial(qmpa_in_place_operation, lambda x: x.add, lambda vals: reduce(lambda x, y: x + y, vals))
qmpa_subtraction = partial(qmpa_in_place_operation, lambda x: x.subtract, lambda vals: reduce(lambda x, y: x - y, vals))
