class Symbol(object):

    def __init__(self, symbol:object, io_in=None, io_out=None, parent=None):
        '''
            Perfectly reasonable Python code
        '''
        if io_in is None:
            io_in = set()
        if io_out is None:
            io_out = set()

        if isinstance(symbol, Symbol) and not isinstance(symbol, ExternSymbol):
            io_in |= symbol.io_in
            io_out |= symbol.io_out
            symbol = symbol.symbol
            
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
        io = [Symbol(i, parent=self) for i in io]
        return {*io}

    def __getitem__(self, index):
        return self.io_rev[index]

    def __call__(self, index):
        return self[self.io[index]]

    def __len__(self):
        return self.__len__(io)

    def __iter__(self):
        return iter(self.io)
       
    def __contains__(self, other):
        if isinstance(other, Symbol):
            return other in self.io
        else:
            return other.__in__(Symbol)

    def __repr__(self):
        if len(self.io_in) == 0 and len(self.io_out) == 0:
            return f'<{self.symbol}>'
        if len(self.io_in) == 0:
            return f'<{self.symbol}: -> {tuple(self.io_out)}>'
        if len(self.io_out) == 0:
            return f'<{self.symbol}: {tuple(self.io_in)}>'
        return f'<{self.symbol}: {tuple(self.io_in)} -> {tuple(self.io_out)}>'

    def __copy__(self):
        return Symbol(self.symbol, self.io_in, self.io_out)

    def rewrite(self, scope):
        io_in = {scope[i] for i in self.io_in}
        io_out = {scope[i] for i in self.io_out}
        new_symbol = Symbol(self.symbol, io_in, io_out)
        self.io_in = new_symbol.io_in
        self.io_out = new_symbol.io_out
        self.io = new_symbol.io
        self.io_rev = new_symbol.io_rev
        return self

    def __str__(self):
        return self.__repr__()

    def __eq__(self, comparator):
        if isinstance(comparator, Symbol):
            return self.symbol == comparator.symbol
        else:
            return self.symbol == comparator

    def satisfies(self, comparator):
        return self.symbol == comparator.symbol

    def __hash__(self):
        return hash(self.symbol)

    def get_parent(self):
        if self.parent is None:
            return self
        return self.parent.get_parent()

    def bind_scope(self):
        return Scope(self.io.keys())

    def inject(self, scope):
        io_in = set(scope[i] for i in self.io_in)
        io_out = set(scope[i] for i in self.io_out)

        io = {j:self.io[i] for i, j in zip(self.io_in, io_in)}
        io |= {j:self.io[i] for i, j in zip(self.io_out, io_out)}

        self.io = io
        self.io_rev = dict(((j, i) for i, j in self.io.items()))
        self.io_in = io_in
        self.io_out = io_out

        return self

    def is_extern(self):
        return isinstance(self.symbol, ExternSymbol)

class ExternSymbol(Symbol):
    singleton = object()

    def __init__(self, predicate, io_element=None):
        
        self.symbol = Symbol('Extern Symbol')

        if isinstance(predicate, str):
            predicate = Symbol(predicate)
        
        if isinstance(io_element, str):
            io_element = Symbol(io_element)

        self.predicate = predicate
        self.io_element = io_element
        self.io_in = set()
        self.io_out = set()
        self.io = dict()
        self.externs = [self]

    def __repr__(self):
        if self.io_element is not None:
            return f'EXTERN: {self.predicate.__repr__()} : {self.io_element.__repr__()}'
        else:
            return f'EXTERN: {self.predicate.__repr__()}'

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return id(self.singleton)

    def __eq__(self, other):
        if not isinstance(other, ExternSymbol):
            return False
        return id(self.predicate) == id(other.predicate)

    def __len__(self):
        return 1

    def __call__(self, io_element):
        return ExternSymbol(self.predicate, io_element)

    def satisfies(self, other):
        if isinstance(other.predicate, ExternSymbol):
            return self.predicate.symbol == other.predicate.predicate
        return self.predicate.symbol == other.predicate.symbol


from scope import Scope