import numpy as np
from functools import reduce, partial
from surface_code_routing.scope import Scope

from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Z, Hadamard, Phase, CZ, SWAP
from surface_code_routing.synth_instructions import CPHASE_theta, Z_theta
from surface_code_routing.lib_instructions import T_Factory, CSWAP, Toffoli

from surface_code_routing.compiled_qcb import compile_qcb
import time
import qmpa

def LU(inst_0, inst_1, inst_2, target, inv):
    inst_0, inst_1, inst_2, target, inv = map(Symbol, [inst_0, inst_1, inst_2, target, inv])

    sym = Symbol('Unitary', (inst_0, inst_1, inst_2, target, inv))
    scope = Scope({sym(i):i  for i in [inst_0, inst_1, inst_2, target, inv]})
    dag = DAG(sym, scope=scope)

    cz16 = Z_theta(1, 16)
    cz16d = Z_theta(-1, 16)
    
    dag.add_gate(INIT(inst_0, inst_1, inst_2, target, inv))

    dag.add_gate(CNOT(inst_0, target))
    dag.add_gate(AND(target, inst_0, inst_2))

    dag.add_gate(X(inst_1))

    dag.add_gate(Phase(target))
    dag.add_gate(Hadamard(target))
    dag.add_gate(Phase(target))
    dag.add_gate(Hadamard(target))
    dag.add_gate(Phase(target))
    dag.add_gate(Z(target))

    dag.add_gate(Hadamard(target))
    dag.add_gate(AND(target, inst_0, inst_2))
    dag.add_gate(Hadamard(target))

    dag.add_gate(Z(target))
    dag.add_gate(Phase(target))
    dag.add_gate(Hadamard(target))
    dag.add_gate(Phase(target))
    dag.add_gate(Hadamard(target))
    dag.add_gate(Phase(target))

    dag.add_gate(X(inst_1))

    dag.add_gate(CZ(inst_1, target))

    dag.add_gate(T(inst_2))
    dag.add_gate(T(inst_1))
    dag.add_gate(T(target))
    dag.add_gate(AND(target, inst_1, inst_2))
    dag.add_gate(T(target)) # Same cost as Td
    dag.add_gate(AND(target, inst_1, inst_2))

    dag.add_gate(CZ(inv, inst_1, inst_2, target))

    dag.add_gate(cz16(inst_0))
    dag.add_gate(cz16(inst_1))
    dag.add_gate(cz16(inst_2))
    dag.add_gate(cz16(target))
    dag.add_gate(AND(target, inst_0, inst_1, inst_2))
    dag.add_gate(cz16d(target))
    dag.add_gate(AND(target, inst_0, inst_1, inst_2))

    dag.add_gate(T(inst_2))
    dag.add_gate(T(inst_1))
    dag.add_gate(T(inst_0))
    dag.add_gate(T(target))
    dag.add_gate(T(inv))
    dag.add_gate(AND(target, inst_0, inst_1, inst_2, inv))
    dag.add_gate(T(inv)) # Same cost as Td
    dag.add_gate(AND(target, inst_0, inst_1, inst_2, inv))

    return dag

def AND(target, *registers, anc_tag=None, init=False):
    if anc_tag is None:
        anc_tag = str(time.time())[-5:]
   
    assert len(registers) > 1
    
    target = Symbol(target)
    registers = tuple(map(Symbol, registers))
    ancillae = tuple(map(Symbol, ['anc_{i}_{tag}'.format(i=i, tag=anc_tag) for i in range(len(registers) - 2)])) 
    sym = Symbol('AND', registers, target)
    scope = Scope({sym(target):target} | {sym(reg):reg for reg in registers})
    dag = DAG(sym, scope=scope)

    if init is True:
        for reg in registers:
            dag.add_gate(INIT(reg))

    for anc in ancillae:
        dag.add_gate(INIT(anc))

    if len(ancillae) == 0:
        dag.add_gate(Toffoli(registers[0], registers[1], target)) 
        return dag

    dag.add_gate(Toffoli(registers[0], registers[1], ancillae[0])) 
   
    for i in range(1, len(registers) - 2):
        dag.add_gate(Toffoli(registers[i + 1], ancillae[i - 1], ancillae[i])) 

    dag.add_gate(Toffoli(registers[-1], ancillae[-1], target)) 

    for i in range(len(registers) - 3, 0, -1):
        dag.add_gate(Toffoli(registers[i + 1], ancillae[i - 1], ancillae[i])) 

    dag.add_gate(Toffoli(registers[0], registers[1], ancillae[0])) 

    return dag

def BB(*externs, height=32, width=8, **compiler_arguments):
    registers = ('ctrl', 'route', 'targ_0', 'targ_1')
    dag = DAG(Symbol('BB', registers, registers))

    dag.add_gate(X(f'ctrl'))
    dag.add_gate(CSWAP(f'ctrl', f'route', f'targ_0'))
    dag.add_gate(X(f'ctrl'))
    dag.add_gate(CSWAP(f'ctrl', f'route', f'targ_1'))

    return compile_qcb(dag, height, width, *externs, **compiler_arguments)

def bucket_brigade_gadget(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, compile=True, BB=None, **compiler_args):
 
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()
   
    if BB is None:
        BB = BB(t_factory) 

    def bb(*args):
        dag = BB.instruction(args=args, targs=args)
        return dag


    dag = DAG(Symbol('qram_bucket_brigade', ['query_{i}'.format(i=i) for i in range(address_size)] , ['readout_{i}'.format(i=i) for i in range(line_width)]))

    int_to_bin = lambda x: bin(x)[2:]


    print("FANOUT")
    for target_anc in range(line_width):
        anc = int_to_bin(target_anc)
        dag.add_gate(INIT(f'route_root_{anc}'))
    dag.add_gate(INIT(f'ctrl_root'))

    for layer in range(1 << (address_size - 1)):
        layer = int_to_bin(layer)
        dag.add_gate(INIT(f'ctrl_{layer}'))

        for anc in range(line_width):
            dag.add_gate(INIT(f'route_{layer}_{anc}'))

    for layer in range(1 << address_size):
        layer = int_to_bin(layer)
        for addr in range(line_width):
            dag.add_gate(INIT(f'mem_{layer}_{addr}'))



    # Build routing network
    for i in range(address_size):

        dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))
        if i > 0:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root', f'route_1_0')
        else:
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            continue

        # Route previous layers
        for layer in range(i - 1):
            if layer > 0:
                for last_layer in range(1 << (layer - 1)):
                    last_layer = int_to_bin(last_layer)
                    dag.add_gate(bb(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0', f'route_{last_layer}1_0)'))


        # Control current layer
        for last_layer in range(1 << (i - 1)):
            addr = int_to_bin(last_layer)
            dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_0', f'ctrl_{addr}0', f'ctrl_{addr}0)'))
            print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')

    # Readout
    print("READOUT")
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
        for idx in range(line_width):
            dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}', f'mem_{addr}1_{idx})'))


            print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    # Back prop routes
    for i in range(address_size - 1, 1, -1): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                for idx in range(line_width):
                    dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0', f'route_{addr}1_{idx})'))

                print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    for idx in range(line_width):
        dag.add_gate(bb(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}0', f'route_0_{idx}1'))
    print('\t','ROUTE ROOT', f'ctrl_root', f'route_root', f'route_1_0')

    # Performing Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    for idx in range(line_width):
        dag.add_gate(bb(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}0', f'route_0_{idx}1'))

    print('\t','ROUTE ROOT', f'ctrl_root', f'route_root', f'route_1_0')

    # Forward prop routes
    for i in range(address_size): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                for idx in range(line_width):
                    dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0', f'route_{addr}1_{idx})'))
                print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    # Memory Readin
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
         
        dag.add_gate(X(f'ctrl_{addr}'))
        for idx in range(line_width):
            dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}', f'mem_{addr}1_{idx})'))
            print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    #print("FANIN")

    # Unbuild routing network
    for i in range(address_size - 1, -1, -1):

         # Control current layer
        if i > 0:
            for last_layer in range(1 << (i - 1)):
                addr = int_to_bin(last_layer)
                dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_0', f'ctrl_{addr}0', f'ctrl_{addr}0)'))
                #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0')
                #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')


        # Route previous layers
        for layer in range(i - 1):
            if layer > 0:
                for last_layer in range(1 << (layer - 1)):
                    last_layer = int_to_bin(last_layer)
                    dag.add_gate(bb(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0', f'route_{last_layer}0_1)'))
                    #print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0')
                    #print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0')
        
        if i > 0:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            #print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root', f'route_1_0')
        else:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))

        dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))
    
    if compile:
        return compile_qcb(dag, width, height,  BB, **compiler_args) 
    else:
        return dag


def qmpa_in_place_operation(operation, readout_assert, *values, register_size = None):
    assert all(lambda x: type(x) is int for x in values)

    if register_size is None:
        register_size = int(np.ceil(np.log2(max(values))))

    circ = qmpa.circuit.Circuit()
    
    reg_carry = circ.register(1, 'carry')
    registers = [circ.register(register_size + i, 'reg_{}'.format(i), value) for i, value in enumerate(values)]
               
    reduce(partial(operation(circ), reg_carry=reg_carry), registers) 
    
    return circ

qmpa_addition = partial(qmpa_in_place_operation, lambda x: x.add, lambda vals: reduce(lambda x, y: x + y, vals))
qmpa_subtraction = partial(qmpa_in_place_operation, lambda x: x.subtract, lambda vals: reduce(lambda x, y: x - y, vals))



def bucket_brigade(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, compile=True, **compiler_args):
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()

    dag = DAG(Symbol('qram_bucket_brigade', ['query_{i}'.format(i=i) for i in range(address_size)] , ['readout_{i}'.format(i=i) for i in range(line_width)]))

    int_to_bin = lambda x: bin(x)[2:]


    #print("FANOUT")
    for target_anc in range(line_width):
        anc = int_to_bin(target_anc)
        dag.add_gate(INIT(f'route_root_{anc}'))
    dag.add_gate(INIT(f'ctrl_root'))

    for layer in range(1 << (address_size - 1)):
        layer = int_to_bin(layer)
        dag.add_gate(INIT(f'ctrl_{layer}'))

        for anc in range(line_width):
            dag.add_gate(INIT(f'route_{layer}_{anc}'))

    for layer in range(1 << address_size):
        layer = int_to_bin(layer)
        for addr in range(line_width):
            dag.add_gate(INIT(f'mem_{layer}_{addr}'))



    # Build routing network
    for i in range(address_size):

        dag.add_gate(SWAP(f'query_{i}', f'route_root_0'))
        if i > 0:
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            #print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root_0', f'route_1_0')
        else:
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))

            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            #print('\t',f'CTRL ROOT', f'route_root_0', f'route_0_0')
            continue


        # Route previous layers
        for layer in range(i - 1):
            if layer > 0:
                for last_layer in range(1 << (layer - 1)):
                    last_layer = int_to_bin(last_layer)
                    dag.add_gate(X(f'ctrl_{last_layer}'))
                    dag.add_gate(CSWAP(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0'))
                    dag.add_gate(X(f'ctrl_{last_layer}'))
                    dag.add_gate(CSWAP(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0'))
                    #print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0')
                    #print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0')


        # Control current layer
        for last_layer in range(1 << (i - 1)):
            addr = int_to_bin(last_layer)
            dag.add_gate(X(f'ctrl_{addr}'))
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0'))
            dag.add_gate(X(f'ctrl_{addr}'))
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1'))
            #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0')
            #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')




    # Readout
    #print("READOUT")
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
         
        dag.add_gate(X(f'ctrl_{addr}'))
        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}'))
        dag.add_gate(X(f'ctrl_{addr}'))

        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}'))
            #print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    # Back prop routes
    for i in range(address_size - 1, 1, -1): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                dag.add_gate(X(f'ctrl_{addr}'))
                for idx in range(line_width):
                    dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0_{idx}'))
                dag.add_gate(X(f'ctrl_{addr}'))
                for idx in range(line_width):
                    dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}1_{idx}'))
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}'))
    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_1_{idx}'))
    #print('\t','ROUTE ROOT', f'ctrl_root', f'route_root_0', f'route_1_0')


    # Performing Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}'))
    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_1_{idx}'))

    #print('\t','ROUTE ROOT', f'ctrl_root', f'route_root_0', f'route_1_0')


    # Forward prop routes
    for i in range(address_size): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                dag.add_gate(X(f'ctrl_{addr}'))
                for idx in range(line_width):
                    dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0_{idx}'))
                dag.add_gate(X(f'ctrl_{addr}'))
                for idx in range(line_width):
                    dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}1_{idx}'))
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    # Memory Readin
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
         
        dag.add_gate(X(f'ctrl_{addr}'))
        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}'))
        dag.add_gate(X(f'ctrl_{addr}'))

        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}'))
            #print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    #print("FANIN")

    # Unbuild routing network
    for i in range(address_size - 1, -1, -1):

        # Control current layer
        if i > 0:
            for last_layer in range(1 << (i - 1)):
                addr = int_to_bin(last_layer)
                dag.add_gate(X(f'ctrl_{addr}'))
                dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0'))
                dag.add_gate(X(f'ctrl_{addr}'))
                dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1'))
                #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0')
                #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')


        # Route previous layers
        for layer in range(i - 1):
            if layer > 0:
                for last_layer in range(1 << (layer - 1)):
                    last_layer = int_to_bin(last_layer)
                    dag.add_gate(X(f'ctrl_{last_layer}'))
                    dag.add_gate(CSWAP(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0'))
                    dag.add_gate(X(f'ctrl_{last_layer}'))
                    dag.add_gate(CSWAP(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0'))
                    #print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0')
                    #print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0')
        
        if i > 0:
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            #print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root_0', f'route_1_0')
        else:
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))

            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            #print('\t',f'CTRL ROOT', f'route_root_0', f'route_0_0')

        dag.add_gate(SWAP(f'query_{i}', f'route_root_0'))
    
    if compile:
        return compile_qcb(dag, width, height, t_factory, **compiler_args) 
    else:
        return dag



def qram_fanout(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, compile=True, **compiler_args):
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()

    dag = DAG(Symbol('qram_fanout', ['query_{i}'.format(i=i) for i in range(address_size)] , ['readout_{i}'.format(i=i) for i in range(line_width)]))

    for target_anc in range(1 << address_size):
        for memory_index in range(line_width):
            dag.add_gate(INIT(f'mem_{target_anc}_{memory_index}'))

    for target_anc in range(address_size):
        dag.add_gate(INIT(f'anc_{target_anc}'))

    # Fanout
    for addr_bit in range(address_size):
        mask = 1 << addr_bit
        target_ancillae = list(filter(lambda x: x % mask == 0, range(1 << address_size)))
        
        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

        for anc_a, anc_b in zip(target_ancillae[::2], target_ancillae[1::2]): 
            for memory_index in range(line_width):
                dag.add_gate(CSWAP(f'anc_{anc_a}', f'mem_{anc_a}_{memory_index}', f'mem_{anc_b}_{memory_index}'))

        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

    # Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    # Fan-in
    for addr_bit in range(address_size - 1, -1, -1):
        mask = 1 << addr_bit
        target_ancillae = list(filter(lambda x: x % mask == 0, range(1 << address_size)))
        
        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

        for anc_a, anc_b in zip(target_ancillae[::2], target_ancillae[1::2]): 
            for memory_index in range(line_width):
                dag.add_gate(CSWAP(f'anc_{anc_a}', f'mem_{anc_a}_{memory_index}', f'mem_{anc_b}_{memory_index}'))


        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

    if compile:
        return compile_qcb(dag, width, height, t_factory, **compiler_args) 
    return dag


from functools import partial

import qmpa
from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.lib_instructions import Toffoli, T, T_Factory


from surface_code_routing.compiled_qcb import compile_qcb

GATE_MAP = {
        qmpa.gates.X : X,
    qmpa.gates.CNOT : CNOT,
    qmpa.gates.Toffoli : Toffoli,
}

def circ_to_dag(qmpa_circ, dag_symbol, T=T, gate_map=GATE_MAP):

    dag = DAG(dag_symbol)

    # Local copy
    gate_map = dict(gate_map)
    gate_map[qmpa.gates.Toffoli] = partial(Toffoli, T=T)
    
    for i in range(qmpa_circ.allocator.max_mem):
        dag.add_gate(INIT(f'reg_{i}'))

    for gate in qmpa_circ.circuit:
        dag_gate = GATE_MAP.get(type(gate), None)
        if dag_gate is None:
            continue

        args = gate.qargs()
        dag.add_gate(
                dag_gate(
                    *list(
                        map(lambda x: "reg_{x}".format(x=x), args)
                        )
                    )
                )
    return dag 
