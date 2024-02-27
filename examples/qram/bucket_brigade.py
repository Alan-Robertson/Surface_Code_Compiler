from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard, SWAP
from surface_code_routing.synth_instructions import CPHASE_theta
from surface_code_routing.lib_instructions import T_Factory, CSWAP

from surface_code_routing.compiled_qcb import compile_qcb


def bucket_brigade(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, compile=True, **compiler_args):
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()

    dag = DAG(Symbol('qram_bucket_brigade', ['query_{i}'.format(i=i) for i in range(address_size)] , ['readout_{i}'.format(i=i) for i in range(line_width)]))

    int_to_bin = lambda x: bin(x)[2:]


    ##print("FANOUT")
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
            ##print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root_0', f'route_1_0')
        else:
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))

            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            ##print('\t',f'CTRL ROOT', f'route_root_0', f'route_0_0')
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
                    ##print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0')
                    ##print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0')


        # Control current layer
        for last_layer in range(1 << (i - 1)):
            addr = int_to_bin(last_layer)
            dag.add_gate(X(f'ctrl_{addr}'))
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0'))
            dag.add_gate(X(f'ctrl_{addr}'))
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1'))


    # Readout
    ##print("READOUT")
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
         
        dag.add_gate(X(f'ctrl_{addr}'))
        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}'))
        dag.add_gate(X(f'ctrl_{addr}'))

        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}'))

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

    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}'))
    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_1_{idx}'))


    # Performing Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}'))
    dag.add_gate(X(f'ctrl_root'))
    for idx in range(line_width):
        dag.add_gate(CSWAP(f'ctrl_root', f'route_root_{idx}', f'route_1_{idx}'))


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
                ##print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                ##print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    # Memory Readin
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
         
        dag.add_gate(X(f'ctrl_{addr}'))
        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}'))
        dag.add_gate(X(f'ctrl_{addr}'))

        for idx in range(line_width):
            dag.add_gate(CSWAP(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}'))
            ##print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    ##print("FANIN")

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


        # Route previous layers
        for layer in range(i - 1):
            if layer > 0:
                for last_layer in range(1 << (layer - 1)):
                    last_layer = int_to_bin(last_layer)
                    dag.add_gate(X(f'ctrl_{last_layer}'))
                    dag.add_gate(CSWAP(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0'))
                    dag.add_gate(X(f'ctrl_{last_layer}'))
                    dag.add_gate(CSWAP(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0'))
        
        if i > 0:
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            ##print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root_0', f'route_1_0')
        else:
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))

            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_0_0'))
            dag.add_gate(X(f'ctrl_root'))
            dag.add_gate(CSWAP(f'ctrl_root', f'route_root_0', f'route_1_0'))
            ##print('\t',f'CTRL ROOT', f'route_root_0', f'route_0_0')

        dag.add_gate(SWAP(f'query_{i}', f'route_root_0'))
    
    if compile:
        return compile_qcb(dag, height, width, t_factory, **compiler_args) 
    else:
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

        dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))
        if i > 0:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            #print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root', f'route_1_0')
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
            #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')

    # Readout
    #print("READOUT")
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
        for idx in range(line_width):
            dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}', f'mem_{addr}1_{idx})'))


            #print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    # Back prop routes
    for i in range(address_size - 1, 1, -1): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                for idx in range(line_width):
                    dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0', f'route_{addr}1_{idx})'))

                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    for idx in range(line_width):
        dag.add_gate(bb(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}0', f'route_0_{idx}1'))
    #print('\t','ROUTE ROOT', f'ctrl_root', f'route_root', f'route_1_0')

    # Performing Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    for idx in range(line_width):
        dag.add_gate(bb(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}0', f'route_0_{idx}1'))

    #print('\t','ROUTE ROOT', f'ctrl_root', f'route_root', f'route_1_0')

    # Forward prop routes
    for i in range(address_size): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                for idx in range(line_width):
                    dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0', f'route_{addr}1_{idx})'))
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}0_0')
                #print('\t','ROUTE', f'ctrl_{addr}', f'route_{addr}_0', f'route_{addr}1_0')

    # Memory Readin
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
         
        dag.add_gate(X(f'ctrl_{addr}'))
        for idx in range(line_width):
            dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}', f'mem_{addr}1_{idx})'))
            #print('\t','MEM', f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}1_{idx}')

    ##print("FANIN")

    # Unbuild routing network
    for i in range(address_size - 1, -1, -1):

         # Control current layer
        if i > 0:
            for last_layer in range(1 << (i - 1)):
                addr = int_to_bin(last_layer)
                dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_0', f'ctrl_{addr}0', f'ctrl_{addr}0)'))
                ##print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}0')
                ##print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')


        # Route previous layers
        for layer in range(i - 1):
            if layer > 0:
                for last_layer in range(1 << (layer - 1)):
                    last_layer = int_to_bin(last_layer)
                    dag.add_gate(bb(f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0', f'route_{last_layer}0_1)'))
                    ##print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}0_0')
                    ##print('\t','ROUTE', f'ctrl_{last_layer}', f'route_{last_layer}_0', f'route_{last_layer}1_0')
        
        if i > 0:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            ##print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root', f'route_1_0')
        else:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))

        dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))
    
    if compile:
        return compile_qcb(dag, height, width,  BB, **compiler_args) 
    else:
        return dag


def bucket_brigade_gadget_fanout(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, compile=True, BB=None, **compiler_args):
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
        dag.add_gate(SWAP(f'query_{i}', f'ctrl_root'))
        if i > 0:
            dag.add_gate(bb(f'ctrl_root', 'route_root', 'route_0_0', 'route_1_0'))
            #print('\t','ROUTE ROOT', i, f'ctrl_root', f'route_root', f'route_1_0')
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
            #print('\t','CTRL', i, addr , f'ctrl_{addr}', f'route_{addr}', f'ctrl_{addr}1')

    if compile:
        return compile_qcb(dag, height, width,  BB, **compiler_args) 
    else:
        return dag


def bucket_brigade_gadget_readout(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, compile=True, BB=None, **compiler_args):
 
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

    # Readout
    #print("READOUT")
    for i in range(1 << (address_size - 1)):
        addr = int_to_bin(i).zfill(address_size - 1)
        for idx in range(line_width):
            dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'mem_{addr}0_{idx}', f'mem_{addr}1_{idx}'))


    # Back prop routes
    for i in range(address_size - 1, 1, -1): 
        for layer in range(1, i):
            for last_layer in range(1 << (layer - 1)):
                addr = int_to_bin(last_layer)
                for idx in range(line_width):
                    dag.add_gate(bb(f'ctrl_{addr}', f'route_{addr}_{idx}', f'route_{addr}0', f'route_{addr}1_{idx}'))

    for idx in range(line_width):
        dag.add_gate(bb(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}', f'route_1_{idx}'))

    # Performing Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    for idx in range(line_width):
        dag.add_gate(bb(f'ctrl_root', f'route_root_{idx}', f'route_0_{idx}', f'route_1_{idx}'))

    if compile:
        return compile_qcb(dag, height, width,  BB, **compiler_args) 
    else:
        return dag

