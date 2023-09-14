# coding: utf-8
import hyphen, sys
hyphen.importing.import_haskell_module('System.Random')
hyphen.importing.import_haskell_module('Quantum.Synthesis.GridSynth')
hyphen.importing.import_haskell_module('Quantum.Synthesis.SymReal')
gridsynth = sys.modules['hs.Quantum.Synthesis.GridSynth']
hsrandom = sys.modules['hs.System.Random']
SymReal = sys.modules['hs.Quantum.Synthesis.SymReal']

'''
    Returning p*Pi/q
'''
def make_pi_multiple(p, q=1):
    out = SymReal.Pi()
    out = SymReal.Times(SymReal.Const(p), out)
    out = SymReal.Div(out, SymReal.Const(q))
    return out


def gridsynth_gates(angle: 'SymReal', precision=10, effort=25, seed=0):
    gates = gridsynth.gridsynth_gates(hsrandom.mkStdGen(seed))(precision)(angle)(effort)
    gates = list(g.split("'")[1] for g in map(str, gates))
    gates.reverse()
    return gates
