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
