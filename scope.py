class Scope():
    def __init__(self, outer=None):
        if outer is None:
            outer = {}
        self.mapping = {i:None for i in outer}

    def __getitem__(self, index):
        return self.mapping[index]

    def __setitem__(self, index, item):
        self.mapping[index] = item

    def __repr__(self):
        return self.mapping.__repr__()

    def __str__(self):
        return self.__repr__()

    def inject_scope(self, **symbols):
        for symbol in symbols.items():
            self.__setitem__(self, *symbol)

    def __or__(self, other):
        return self.mapping.__or__(other)

    def __ior__(self, other):
        return self.mapping.__ior__(other)
