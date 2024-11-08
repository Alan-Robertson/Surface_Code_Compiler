from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.lib_instructions import T_Factory, CSWAP

from surface_code_routing.compiled_qcb import compile_qcb


def qram_fanout(address_size, line_width, height, width, gates=None, t_factory=None, readout=CNOT, compile=True, **compiler_args):
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
        return compile_qcb(dag, height, width, t_factory, **compiler_args) 
    return dag



def mcswap_gadget(height, width, reg_width , *externs, **compiler_arguments):
     
    registers = ['ctrl'] + ['a_{}'.format(i) for i in range(reg_width)] + ['b_{}'.format(i) for i in range(reg_width)]

    dag = DAG(Symbol('mcswap', registers, registers))
    
    for i in range(reg_width):
        dag.add_gate(CSWAP(f'ctrl', f'a_{i}', f'b_{i}'))

    return compile_qcb(dag, height, width, *externs, **compiler_arguments)

def qram_fanout_fanout_gadget(address_size, line_width, height, width, MCSWAP, gates=None, t_factory=None, readout=CNOT, compile=True, **compiler_args):
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()

    def mcswap(*args):
        dag = MCSWAP.instruction(args=args, targs=args)
        return dag

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
            dag.add_gate(mcswap(f'anc_{anc_a}', 
                                *['mem_{anc_a}_{memory_index}'.format(anc_a=anc_a, memory_index=i) for i in range(line_width)],
                                *['mem_{anc_b}_{memory_index}'.format(anc_b=anc_b, memory_index=i) for i in range(line_width)]
                                )
                         )

        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))


    if compile:
        return compile_qcb(dag, height, width, MCSWAP, **compiler_args) 
    return dag


