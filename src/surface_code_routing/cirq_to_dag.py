from surface_code_routing.dag import DAG
from surface_code_routing.scope import Scope 
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Z, Hadamard, Phase
from surface_code_routing.synth_instructions import Z_theta
from surface_code_routing.lib_instructions import T_Factory, T, Toffoli
from surface_code_routing.symbol import Symbol
import numpy as np

import cirq

class CirqQubitMap:

    def __init__(self, cirq_circuit):
        self.qubit_map = {
            qubit: 'q_{i}'.format(i=i) for i, qubit in enumerate(cirq_circuit.all_qubits())
        }

    def __getitem__(self, qubit):
        return self.qubit_map[qubit]

    def __call__(self, cirq_gate):
        return [self[i] for i in cirq_gate.qubits]

    def init(self, dag: DAG):
        '''
            Adds the appropriate init gates
        '''
        for q in self.qubit_map.values():
            if q not in dag.scope:
                dag.add_gate(INIT(q)) 

class CirqToDagGate:

    UNKNOWN_GATE = Symbol('UNKNOWN GATE')
    def __init__(self, kwarg_map):
        self.gate_map = kwarg_map

    def add(self, symbol):
        pass

    def __setitem__(self, cirq_gate, dag_gate):
        self.gate_map[cirq_gate] = dag_gate

    def __getitem__(self, cirq_gate):
        gate_type = type(cirq_gate.gate)
        return self.gate_map.get(gate_type, CirqToDagGate.UNKNOWN_GATE)

    def __call__(self, gate):
        return self.__getitem__(gate)


    def __or__(self, other):
        if isinstance(dict, other):
            return CirqToDag(self.gate_map | other)

        if isinstance(CirqToDag, other):
            return CirqToDag(self.gate_map | other.gate_map)

        raise TypeError(f"CirqToDag only composes over itself and dicts, not {type(other)}")


def float_to_rz(targ, angle, precision, delta=3):

    angle = (angle / 2)

    sym = Symbol(f'rz_{angle}_{precision}', (targ,), (targ,))
    scope = Scope({sym(targ):targ})
    dag = DAG(sym, scope=scope)
    
    if np.abs(angle - 0.5) < 2 ** -delta:
        dag.add_gate(Phase(targ))
        return dag

    if np.abs(angle - 1) < 2 ** -delta:
        dag.add_gate(Z(targ))
        return dag

    
    # Basically just extract the mantissa
    sign = (2 * int(angle > 0) - 1) 
    angle = np.abs(angle)

    denominator = int(np.ceil(angle * 2 ** (precision + delta)))
    numerator = int(angle * denominator) 

    # All angles positive
    if sign == -1:
        numerator = denominator - numerator
    dag.add_gate(Z_theta(numerator, denominator, precision=precision)(targ))
    return dag

def cirq_rz(cirq_gate, qubit_map, *, precision=10, **kwargs):
    args = qubit_map(cirq_gate)
    return float_to_rz(*args, cirq_gate.gate._rads, precision)

def cirq_rx(cirq_gate, qubit_map, *, precision=10, **kwargs):
    args = qubit_map(cirq_gate)

    sym = Symbol(f'rx', args, args)
    scope = Scope({sym(arg):arg for arg in args})

    dag = DAG(sym, scope=scope)

    dag.add_gate(Hadamard(*args))
    dag.add_gate(float_to_rz(*args, cirq_gate.gate._rads, precision))
    dag.add_gate(Hadamard(*args))

    return dag

def cirq_hpow(cirq_gate, qubit_map, *, precision=10, **kwargs):
    args = qubit_map(cirq_gate)

    sym = Symbol(f'hpow', args, args)
    scope = Scope({sym(arg):arg for arg in args})

    dag = DAG(sym, scope=scope)

    dag.add_gate(Hadamard(*args))

    return dag


def cirq_cnot(cirq_gate, qubit_map, *, precision=10, **kwargs):
    args = qubit_map(cirq_gate)

    sym = Symbol(f'cirq_cnot', args, args)
    scope = Scope({sym(arg):arg for arg in args})

    dag = DAG(sym, scope=scope)

    dag.add_gate(CNOT(*args))

    return dag


# TODO
DEFAULT_MAP = CirqToDagGate(
    {
        cirq.ops.common_gates.Rz: cirq_rz,
        cirq.ops.common_gates.Rx: cirq_rx,
        cirq.ops.common_gates.HPowGate: cirq_hpow,
        cirq.ops.common_gates.CNOT: cirq_cnot,
        cirq.ops.common_gates.CXPowGate: cirq_cnot,
    }
) 

def cirq_dag(dag_sym, cirq_circuit, *, gate_map = DEFAULT_MAP, precision=10, **kwargs):
    '''
     :: dag_sym : [Symbol|str] :: Symbol for the dag
     :: cirq_circuit : Circuit :: Cirq Circuit 
     :: gate_map :: Gate Map to be used
     :: precision : int :: Precision of Rz decompositions in bits
    '''
    dag = DAG(dag_sym)
    m = CirqQubitMap(cirq_circuit)
    m.init(dag)

    for sl in cirq_circuit: 
        for gate in sl:
            gate_constructor = gate_map(gate)
            if gate_constructor is not CirqToDagGate.UNKNOWN_GATE:
                
                # Set gates to NONE to skip parsing 
                if gate_constructor is not None:
                    dag.add_gate(gate_constructor(gate, m, precision=precision))
            else:
                raise Exception()      
 
    return dag
