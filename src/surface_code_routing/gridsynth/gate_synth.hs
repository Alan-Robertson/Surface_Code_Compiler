import Quantum.Synthesis.GridSynth
import Quantum.Synthesis.SymReal
import System.Random
import System.IO


gate_synth :: IO ()
gate_synth = do
    input <- getLine
    let (p:q:precision:effort:seed:xs) = map read(words input) :: [Int]

    let angle = ( Pi * to_real p ) / to_real q

    print(gridsynth_gates(mkStdGen seed)(fromIntegral precision)(angle)(effort))

    gate_synth

main :: IO ()
main = do 
    hSetBuffering stdout NoBuffering
    gate_synth
    
