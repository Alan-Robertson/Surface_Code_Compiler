from symbol import symbol_resolve

class ExternInterface():
    def __init__(self, symbol, n_cycles, n_prewarm=0):
        self.symbol = symbol_resolve(symbol)
        self.__n_cycles = n_cycles
        self.__n_prewarm = n_prewarm
        self.slack = float('inf')

    def n_cycles(self):
        return self.__n_cycles 

    def n_pre_warm_cycles(self):
        return self.__n_prewarm

    def get_symbol(self):
        return self.symbol

    def __repr__(self):
        return self.symbol.__repr__()

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)

    def satisfies(self, other):
        return self.symbol.satisfies(other)

    def get_obj(self):
        return self
