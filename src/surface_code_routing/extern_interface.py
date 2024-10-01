'''
    Interface for externs
'''
from surface_code_routing.symbol import symbol_resolve

class ExternInterface():
    '''
        Interface for externs
    '''
    def __init__(self, symbol, n_cycles, n_prewarm=0):
        self.symbol = symbol_resolve(symbol)
        self.__n_cycles = n_cycles
        self.__n_prewarm = n_prewarm
        self.slack = float('inf')

    def n_cycles(self):
        '''
            Number of cycles that the extern runs for 
            TODO: replace with a vtable 
        '''
        return self.__n_cycles

    def n_pre_warm_cycles(self):
        '''
            Number of pre-operation cycles this extern can run for 
            TODO: Not yet implemented
        '''
        return self.__n_prewarm

    def get_symbol(self):
        '''
            Gets the symbol of the extern
        '''
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
        '''
            Checks dependency satisfaction 
        '''
        return self.symbol.satisfies(other)

    def get_obj(self):
        '''
            Getter dispatch
        '''
        return self
