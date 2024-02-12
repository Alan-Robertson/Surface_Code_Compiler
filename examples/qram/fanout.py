from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.synth_instructions import CPHASE_theta
from surface_code_routing.lib_instructions import T_Factory, CSWAP

from surface_code_routing.compiled_qcb import compile_qcb


def qram_fanout(address_size, line_width, width, height, gates=None, t_factory=None, readout=CNOT, **compiler_args):
    if gates is None:
        gates = {}
    if t_factory is None:
        t_factory = T_Factory()

    dag = DAG(Symbol('qram_fanout', ['query_{i}' for i in range(address_size)] , ['readout_{i}' for i in range(line_width)]))

    # Fanout
    for addr_bit in range(address_size):
        mask = 1 << addr_bit
        target_ancillae = list(filter(lambda x: x % mask == 0, range(address_size)))
        
        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

        for target_anc in target_ancillae: 
            for memory_index in range(line_width):
                dag.add_gate(CSWAP(f'anc_{target_anc}', 'mem_{target_anc}_{memory_index}', 'mem_{target_anc + mask}_{memory_index}'))

        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

    # Readout
    for index in range(line_width):
        dag.add_gate(readout(f'mem_0_{index}', f'readout_{index}'))

    # Fan-in
    for addr_bit in range(address_size - 1, -1, -1):
        mask = 1 << addr_bit
        target_ancillae = list(filter(lambda x: x % mask == 0, range(address_size)))
        
        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

        for target_anc in target_ancillae: 
            for memory_index in range(line_width):
                dag.add_gate(CSWAP(f'anc_{target_anc}', 'mem_{target_anc}_{memory_index}', 'mem_{target_anc + mask}_{memory_index}'))

        dag.add_gate(CNOT(f'query_{addr_bit}', *list(map(
            lambda x: 'anc_{i}'.format(i=x), target_ancillae
            ))))

    return compile_qcb(dag, width, height, t_factory, **compiler_args) 
