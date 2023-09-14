git clone https://github.com/tbarnetlamb/hyphen
sudo apt install cabal-install
cabal update
cabal install newsynth
cabal install text transformers mtl parsec hashable unordered-containers ghc-paths --lib

In ghci:
:set -package random

python3 hyphen/build-extn.py
