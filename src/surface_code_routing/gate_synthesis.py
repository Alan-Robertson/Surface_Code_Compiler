import subprocess
from functools import lru_cache

from surface_code_routing.dag import DAG
from surface_code_routing.symbol import Symbol
from surface_code_routing.scope import Scope
from surface_code_routing.instructions import Hadamard, Phase, X, Z
from surface_code_routing.lib_instructions import T

import surface_code_routing 
import os

class GateSynth:
    GATE_SYNTH_BNR = os.path.join(os.path.dirname(surface_code_routing.dag.__file__), 'gridsynth/gate_synth')
    CMD = f"{GATE_SYNTH_BNR}".split() 

   
    DEFAULT_GATE_DICT = {
            'X':X,
            'Z':Z,
            'S':Phase,
            'H':Hadamard,
            'T':T
            }

    def __init__(self, gate_dict=None):
        # Because these depend on the location of the file they can't be trusted at compile time
        self.proc = subprocess.Popen(self.CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE) 
        if gate_dict is None:
            self.gate_dict = self.DEFAULT_GATE_DICT
        else:
            self.gate_dict = gate_dict

    @lru_cache
    def z_theta_instruction(self, p, q, precision=10, effort=25, seed=0, **gates):
        '''
            Returns a series of gates that perform Z(PI * p / q) with some epsilon precision
        '''
        self.proc.stdin.write(f"{p} {q} {precision} {effort} {seed}\n".encode('ascii'))
        self.proc.stdin.flush()
        sequence = self.proc.stdout.readline().decode()
        op_sequence = sequence.split('[')[1].split(']')[0].split(',')[::-1]
        instruction = self.operations_to_instruction(f'Z({p}/{q})', op_sequence, **gates)
        return instruction

    def operations_to_instruction(self, fn, op_sequence, **gates):
        gate_dict = self.gate_dict | gates
        def instruction(targ):
            targ = Symbol(targ)
            sym = Symbol(fn, 'targ')
            scope = Scope({sym('targ'):targ})
            dag = DAG(sym, scope=scope)
            
            for instruction in op_sequence:
                gate = gate_dict.get(instruction, None)
                if gate is not None:
                    dag.add_gate(gate(targ))
            return dag
        return instruction

    def __del__(self):
        self.proc.terminate()
