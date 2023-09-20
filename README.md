## Dependencies ##
Python >=3.10





## Gridsynth Installation ##

Currently GridSynth is partially merged into Quipper, so it follows that if we can install quipper then GridSynth should work.

Quipper is currently in a Haskell dependency hell, newer versions of ghc will not compile it, and newer versions of Cabal are incompatible with various dependencies of Quipper (newer versions of the dependencies are in turn incompatible with versions of ghc that are compatible with Quipper). As a result ghc 8.6.5 is stable, though 8.8.4 may or may not also work.

We'll version quipper using ghcup, you may look into your own nix, cabal or stack based solutions to this problem. This currently works as Cabal will invoke the legacy v1 installation methods, this may be unstable in the future.

```
    curl https://gitlab.haskell.org/haskell/ghcup/raw/master/ghcup > /tmp/ghcup
    chmod +x /tmp/ghcup
    /tmp/ghcup install 8.6.5
    /tmp/ghcup set 8.6.5
    /tmp/ghcup install-cabal 2.4.1.0

    # Update path
    PATH="$HOME/.cabal/bin:$HOME/.ghcup/bin:$PATH"

    # Install Quipper
    cabal update
    cabal install quipper-all
```
You may wish to add the path command to your terminal's appropriate rc file. Rather than installing quipper you may also install newsynth independently.

For more details see the quipper docs: (https://www.mathstat.dal.ca/~selinger/quipper/README)[https://www.mathstat.dal.ca/~selinger/quipper/README]

Once that's installed we can compile the relevant Haskell files 
```
make all
```

Once this is done now we can install the package
```
python setup.py install
```
