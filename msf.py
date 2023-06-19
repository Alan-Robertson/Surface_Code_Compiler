class MSF():
    def __init__(self, symbol, shape, cycles, err=0):
        self.symbol = symbol
        self.width = shape[0]
        self.height = shape[1]
        self.cycles = cycles
        self.err = err
    
    def __repr__(self):
        return f"MSF({self.symbol})"
    def copy(self):
        return MSF(self.symbol, (self.width, self.height), self.cycles, self.err)