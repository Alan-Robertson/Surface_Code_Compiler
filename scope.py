class Scope():
    def __init__(self, *args, outer=None):

        if len(args) > 1:
            scope = args

        if outer is None:
            outer = {}
        if isinstance(outer, dict):
            self.mapping = outer
        elif isinstance(outer, Scope):
            self.mapping = outer.mapping
        else:
            self.mapping = {i:None for i in outer}

    def __getitem__(self, index):
        return self.mapping[index]

    def __setitem__(self, index, item):
        self.mapping[index] = item

    def __iter__(self):
        return self.mapping.__iter__()

    def __repr__(self):
        return self.mapping.__repr__()

    def __str__(self):
        return self.__repr__()

    def inject_scope(self, scope):
        for symbol_pair in scope.items():
            self.__setitem__(symbol_pair)        

    def __or__(self, other:'Scope'):
        scope = Scope(self.mapping)
        for i in other:
            if i in self and other[i] is not None:
                scope[i] = other[i]
        return scope

    def items(self):
        return self.mapping.items()

    def __ior__(self, other):
        return self.mapping.__ior__(other)

    def __contains__(self, other):
        return other in self.mapping
