class MSF():
    def __init__(self, symbol, shape, cycles, err=0):
        self.symbol = symbol
        self.width = shape[0]
        self.height = shape[1]
        self.cycles = cycles
        self.err = err