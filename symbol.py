class Symbol(object):
    def __init__(self, symbol:object, io_in=None, io_out=None, parent=None):
        '''
            Perfectly reasonable Python code
        '''
        #assert (type(symbol) in (Symbol, int, str))
        self.symbol = symbol
        self.parent = parent
        self.io_in, self.io_out = map(self.format, (io_in, io_out))
        self.io = {j:i for i, j in enumerate(self.io_in)}
        self.io |= {j:len(self.io_in) + i for i, j in enumerate(self.io_out - self.io_in)}
        self.io_rev = dict(((j, i) for i, j in self.io.items()))

    def format(self, io:'object|Sequence'):
        '''
            Basically overloads our constructor
        '''
        if io is None:
            io = set()
        elif not (type(io) in (list, tuple, set)):
            io = [Symbol(io)]
        io = [Symbol(i.symbol, parent=self) for i in io]
        return {*io}

    def __getitem__(self, index):
        return self.io_rev[index]

    def __call__(self, index):
        return self.io[index]

    def __len__(self):
        return self.__len__(io)

    def __iter__(self):
        return iter(self.io)
       
    def get_in(self, index):
        return self.io[self.io_in[index]]

    def get_out(self, index):
        return self.io[self.io_out[index]] 

    def __repr__(self):
        if len(self.io_in) == 0 and len(self.io_out) == 0:
            return f'<{self.symbol}>'
        return f'<{self.symbol} : {tuple(self.io_in)} -> {tuple(self.io_out)}>'

    def __str__(self):
        return self.__repr__()

    def __eq__(self, comparator):
        return self is comparator

    def satisfies(self, comparator):
        return self.symbol == comparator.symbol

    def __hash__(self):
        return hash(self.symbol)

    def get_parent(self):
        if self.parent is None:
            return self
        return self.parent.get_parent()


class BindSymbol():
    def __init__(self, symbol):
        self.symbol = symbol
    def __hash__(self):
        return hash(self.symbol)
    def __eq__(self, comparator):
        return self.symbol.symbol == comparator.symbol
