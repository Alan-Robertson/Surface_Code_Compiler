import numpy as np
from functools import partial
from surface_code_routing.dag import DAG
from surface_code_routing.scope import Scope 

from surface_code_routing.symbol import Symbol
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard, T_SLICE
from surface_code_routing.lib_instructions import T_Factory, T, Toffoli

from surface_code_routing.compiled_qcb import compile_qcb, CompiledQCB


# https://arxiv.org/pdf/1805.03662 figure 10, page 14

def toffoli(height, width, t_factory=None):
    if t_factory is None:
        t_factory = T_Factory() 
    dag = DAG(Symbol('Toffoli', ('ctrl_a', 'ctrl_b', 'targ'))) 
    dag.add_gate(Toffoli('ctrl_a', 'ctrl_b', 'targ'))
    return compile_qcb(dag, height, width, t_factory) 


def wrap(dag, gate, *args):
    if isinstance(gate, CompiledQCB):
        dag.add_gate(
            gate(
                args,
                args
            )
        )
    else: 
        dag.add_gate(
            gate(
                *args
            )
        )

def multi_control_toffoli(dag, ctrls, targs, anc = 'anc', toffoli=Toffoli): 

    round_ancillae = None
    
    wrap(dag, toffoli, ctrls[0], ctrls[1], f'{anc}_0')
    for idx, ctrl in enumerate(ctrls[1:]):
        round_ancillae = f'{anc}_{idx}'
        wrap(dag, toffoli, f'{anc}_{idx}', ctrl, f'{anc}_{idx + 1}')

    # The use of a round ancillae for the final round 
    dag.add_gate(CNOT(round_ancillae, *targs)) 

    for idx, ctrl in enumerate(ctrls[1:]):
        round_ancillae = f'{anc}_{idx}'
        wrap(dag, toffoli, f'{anc}_{idx}', ctrl, f'{anc}_{idx + 1}') 


def qrom_mc(dag, ctrls, targs, anc = 'anc', toffoli=Toffoli): 

    round_ancillae = None
    dag.add_gate(
        toffoli(ctrls[0], ctrls[1], f'{anc}_0') 
    )

    for idx, ctrl in enumerate(ctrls[1:]):
        round_ancillae = f'{anc}_{idx}'
        dag.add_gate(
            toffoli(f'{anc}_{idx}', ctrl, f'{anc}_{idx + 1}') 
        )

    # The use of a round ancillae for the final round 
    # Is to better support multi target operations
    for targ in targs: 
        dag.add_gate(CNOT(round_ancillae, targ)) 

    # TODO: flip this
    for idx, ctrl in enumerate(ctrls[1:]):
        round_ancillae = f'{anc}_{idx}'
        dag.add_gate(
            toffoli(f'{anc}_{idx}', ctrl, f'{anc}_{idx + 1}') 
        )




def qrom(dag, ctrl, inputs, targs, anc='anc', toffoli=Toffoli): 
    ctrl_bits = len(inputs)

    curr = 0
    for i in range(len(inputs)):
        dag.add_gate(INIT(f'{anc}_{i}'))

    # Initial multi_control Toffoli
    round_ancillae = None
    dag.add_gate(
        toffoli(ctrl, inputs[0], f'{anc}_0') 
    )

    for idx in range(len(inputs) - 1):
        round_ancillae = f'{anc}_{idx}'
        dag.add_gate(
            toffoli(
                f'{anc}_{idx}', 
                inputs[idx + 1], 
                f'{anc}_{idx + 1}') 
        )
        print(f'{anc}_{idx}', 
                inputs[idx + 1], 
                f'{anc}_{idx + 1}')


    dag.add_gate(CNOT(round_ancillae, *targs)) 

    for i in range(2 ** ctrl_bits - 2, 0 , -1):
        mask = i ^ curr 

        round_bits = len(bin(mask)) - 2

        #for curr_bit in range(ctrl_bits - round_bits, round_bits, -1):
              
 

#        # CNOT rather than Toffoli 
#        for targ in ctrls[:round_bits]:
#            dag.add_gate(X(targ))
#
#        multi_control_toffoli(dag, ctrls[:round_bits], targs, anc=anc, toffoli=toffoli)
#
#    multi_control_toffoli(dag, ctrls, targs, anc=anc, toffoli=toffoli)
    return 
         

def qrom_naive(dag, ctrl, inputs, targs, anc='anc', toffoli=Toffoli):

    n_inputs = len(inputs)

    curr = 0  
    for i in range(2 ** n_inputs - 2, 0 , -1):
        mask = i ^ curr

        for i in range(n_inputs): 
            if bool(not not((1 << i) & mask)):
                dag.add_gate(X(inputs[i]))

        # Just using multiple toffoli gates 
        multi_control_toffoli(dag, inputs, targs, anc=anc, toffoli=toffoli)
    return dag



def _sawtooth(i, ctrls, targs, ancs):
    dag = DAG('_sawtooth') 
    
    if i > 0: 
        dag.add_gate(Toffoli(ctrls[0], ancs[0], ancs[1]))
        dag.add_gate(_sawtooth(i - 1, ctrls[1:], targs, ancs[1:]))
        dag.add_gate(CNOT(ancs[0], ancs[1]))
        dag.add_gate(_sawtooth(i - 1, ctrls[1:], targs, ancs[1:]))

        dag.add_gate(Toffoli(ctrls[0], ancs[0], ancs[1]))

    else:
        dag.add_gate(CNOT(ancs[1], *targs))
        dag.add_gate(CNOT(ancs[0], ancs[1]))
        dag.add_gate(CNOT(ancs[1], *targs))

    return dag



def qrom_sawtooth(ctrls, targs, extern=False, Toffoli=None):
    n_ancillae = len(ctrls) - 1 

    if extern:
         sym = Symbol('QROM_SAWTOOTH', ctrls + targs, ctrls + targs)
    else:
        sym = Symbol('QROM_SAWTOOTH')
    dag = DAG(sym)

    ancillae = [f'anc_{i}' for i in range(n_ancillae)]
    for anc in ancillae:
        dag.add_gate(INIT(anc))
  
    s_ctrls = ctrls[:-1]  
    s_anc = [ctrls[-1]] + ancillae 
    dag.add_gate(
        _sawtooth(
            n_ancillae - 1,
            s_ctrls,
            targs,
            s_anc
        )
    ) 




    return dag 
    

def qrom_dag(
        n_inputs, 
        n_outputs, 
        extern=True,
        toffoli=Toffoli):

    inputs = tuple(f'input_{i}' for i in range(n_inputs))
    outputs = tuple(f'output_{i}' for i in range(n_outputs))
    ctrl = 'ctrl'

    registers = inputs + outputs + (ctrl,) 

    if extern:
        dag = DAG(Symbol(f'QROM', 
            registers, registers                
            ))
    else:
        dag = DAG(f'QROM')
        for sym in registers: 
            dag.add_gate(INIT(sym))


    qrom_naive(dag, ctrl, inputs, outputs, toffoli=toffoli)
    return dag


t_factory = T_Factory()
toffoli_qcb = toffoli(10, 10)

height = 20
width = 20
dag = qrom_dag(2, 2, toffoli=toffoli_qcb)
qcb = compile_qcb(dag, height, width, toffoli_qcb, t_factory)
