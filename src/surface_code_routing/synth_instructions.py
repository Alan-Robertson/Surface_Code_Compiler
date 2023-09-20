from surface_code_routing.symbol import Symbol, symbol_resolve
from surface_code_routing.scope import Scope
from surface_code_routing.dag import DAG
from surface_code_routing.gate_synthesis import GateSynth
from surface_code_routing.instructions import CNOT

SYNTH = None

# This avoids trying to import the synth at compile time
def initialise_synth(fn):
    global SYNTH
    if SYNTH is None:
        SYNTH = GateSynth()
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


def Z_theta(p, q, precision=10, effort=25, seed=0):
    return SYNTH.z_theta_instruction(
            p, q, 
            precision=precision,
            effort=effort,
            seed=seed)

@initialise_synth
def CPHASE_theta(p, q, precision=10, effort=25, seed=0):
    z_theta_2 = SYNTH.z_theta_instruction(p, q * 2, precision=precision, effort=effort, seed=seed)
    z_theta_2_dag = SYNTH.z_theta_instruction(-p, q * 2, precision=precision, effort=effort, seed=seed)
    def instruction(*args):
        args = tuple(map(symbol_resolve, args))
        sym = Symbol(f'CPHASE({p}/{q})', args)

        # Scope injection passes variables from a higher scope
        scope = Scope({sym(arg):arg for arg in args})
        
        dag = DAG(sym, scope=scope)
        ctrl = args[0]

        for arg in args:
            dag.add_gate(z_theta_2(arg))

        # Splitting these gives some time for the other operations to complete
        for arg in args[1:]:
            dag.add_gate(CNOT(ctrl, arg))
        for arg in args[1:]:
            dag.add_gate(z_theta_2_dag(arg))
        for arg in args[1:]:
            dag.add_gate(CNOT(ctrl, arg))
        return dag

    return instruction

