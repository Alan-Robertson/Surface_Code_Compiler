class ExternInterface():
    def __init__(self, symbol, n_cycles, n_prewarm=0):
        self.symbol = symbol
        self.__n_cycles = n_cycles
        self.__n_prewarm = n_prewarm

    def n_cycles(self):
        return self.__n_cycles 

    def n_prewarm(self):
        return self.__n_prewarm

    def __repr__(self):
        return self.symbol.__repr__()

    def __str__(self):
        return self.__repr__()