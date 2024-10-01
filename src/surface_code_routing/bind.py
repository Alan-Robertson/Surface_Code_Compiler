'''
    Bind
    Set of bind indirection wrappers 
    Promotes objects to permit comparisons on both the bind object, and the underlying object 
'''

class Bind():
    def __init__(self, obj):
        '''
            Bind
            Set of bind indirection wrappers 
            Promotes objects to permit comparisons on both the bind object, and the underlying object 
        '''
        self.obj = obj
        self.cycles_completed = 0

    def get_symbol(self):
        return self.obj.get_symbol()

    # Getters and Setters
    def get_cycles_completed(self):
        return self.cycles_completed

    def reset_cycles_completed(self):
        self.cycles_completed = 0

    def __repr__(self):
        return f"{repr(self.obj)} {hex(id(self.obj.symbol))}: {self.curr_cycle()} {self.n_cycles()}"

    # Wrapper functions
    def predicates(self):
        return self.obj.predicates

    def antecedents(self):
        return self.obj.antecedents

    def n_pre_warm_cycles(self):
        return self.obj.pre_warm()

    def n_cycles(self):
        return self.obj.n_cycles()

    def n_pre_warm_cycles(self):
        return self.obj.n_pre_warm_cycles()

    def non_local(self):
        return self.obj.non_local()

    def satisfies(self, other):
        return self.get_symbol().satisfies(other.get_symbol())

    def get_obj(self):
        return self.obj.get_obj()

    def __hash__(self):
        return id(self)

    # Cycle functions
    def cycle(self):
        self.cycles_completed += 1
        return self.cycles_completed

    def curr_cycle(self):
        return self.cycles_completed

    def resolved(self):
        return self.cycles_completed >= self.n_cycles()

    def reset(self):
        self.cycles_completed = 0

    def get_unary_symbol(self):
        return self.obj.get_unary_symbol()


    def __gt__(self, other):
        return True

    def __lt__(self, other):
        return False

    def __ge__(self, other):
        return True

    def __le__(self, other):
        return False

class AddrBind():
    '''
        Wrapper that promotes comparisons to addresses
    '''
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        if isinstance(other, AddrBind):
            return other.obj is self.obj
        else:
            return other is self.obj
    
    def __hash__(self):
        return self.obj.__hash__()

    def __repr__(self):
        return self.obj.__repr__()

    
class ExternBind(Bind):
    def __init__(self, obj):
        '''
            ExternBind
            Bind wrapper for extern objects
        '''
        # Nesting this ensures non-fungibility
        self.obj = Bind(obj)
        self.slack = float('-inf')

    def pre_warm(self):
        if self.n_cycles() < self.n_pre_warm_cycles():
            self.cycle()
            return True
        return False

    def bind_extern(self, extern):
        self.n_cycles = extern.n_cycles

    def n_cycles(self):
        return self.obj.n_cycles()

    def is_factory(self):
        return self.obj.obj.is_factory()

    def __repr__(self):
        return f"{repr(self.obj)} {hex(id(self.obj.obj.symbol))}: {self.curr_cycle()} {self.n_cycles()}"

    # Wrappers
    def get_cycles_completed(self):
        return self.obj.get_cycles_completed()

    def set_cycles_completed(self, n_cycles):
        self.obj.cycles_completed = n_cycles

    def reset(self):
        self.obj.reset()

    def cycle(self):
        return self.obj.cycle()

    def curr_cycle(self):
        return self.obj.curr_cycle()

    def n_pre_warm_cycles(self):
        return self.obj.n_pre_warm_cycles()

    def antecedents(self):
        return self.obj.antecedents()

    def predicates(self):
        return self.obj.predicates()

    def is_extern(self):
        return True

    def resolved(self):
        return self.obj.resolved()

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return id(self.obj.obj)

    def __is__(self, other):
        return hash(self) == hash(other)

class DAGBind(Bind):
    '''
        Bind
        This allows us to override the regular hashing behaviour of another arbitrary object
        such that we can compare instances of symbols rather than symbol strings 
    '''
    def __init__(self, obj):
        self.slack = obj.slack
        self.symbol = obj.symbol
        super().__init__(obj)

    def wait(self):
        self.slack -= 1

    def satisfies(self, other):
        if isinstance(other, Bind):
            return self.obj.symbol == other.obj.symbol
        else:
            return self.obj.symbol == other.symbol

    def pre_warm(self):
        return False

    def __gt__(self, other):
        return self.slack > other.slack

    def __lt__(self, other):
        return self.slack < other.slack

    def __ge__(self, other):
        return self.slack >= other.slack

    def __le__(self, other):
        return self.slack <= other.slack

    def __eq__(self, obj):
        if isinstance(obj, Bind):
            return id(self.obj) == id(obj.obj)
        else:
            return id(self.obj) == id(obj)

    def __hash__(self):
        return id(self.obj)

    def is_extern(self):
        return False

class RouteBind(Bind):
    def __init__(self, gate, addresses):
        self.addresses = addresses
        self.scope = gate.scope
        super().__init__(gate)

    def __eq__(self, other):
        if isinstance(other, RouteBind):
            return other.obj is self.obj
        else:
            return other is self.obj
    
    def __hash__(self):
        return self.obj.__hash__()

    def __repr__(self):
        return self.obj.__repr__()

    def rotates(self):
        return self.obj.rotates()
    
    def n_ancillae(self):
        return self.obj.n_ancillae
    def ancillae_type(self):
        return self.obj.ancillae_type
    def is_extern(self):
        return self.obj.is_extern()
    def is_factory(self):
        return self.obj.is_factory()
