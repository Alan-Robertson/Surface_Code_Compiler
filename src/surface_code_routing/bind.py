'''
    Bind
    Set of bind indirection wrappers
    Promotes objects to permit comparisons on both the bind object, and the underlying object
'''

from typing import Type
from surface_code_routing.symbol import Symbol

class Bind():
    '''
    Bind
    Set of bind indirection wrappers
    Promotes objects to permit comparisons on
    both the bind object, and the underlying object
    '''
    def __init__(self, obj):
        '''
        Bind
        Set of bind indirection wrappers
        Promotes objects to permit comparisons on
        both the bind object, and the underlying
        object
        '''
        self.obj = obj
        self.cycles_completed = 0

    def get_symbol(self) -> Type[Symbol]:
        '''
        Obj wrapper
        '''
        return self.obj.get_symbol()

    # Getters and Setters
    def get_cycles_completed(self) -> int:
        '''
        Getter method for number of cycles this
        bound object has completed
        '''
        return self.cycles_completed

    def reset_cycles_completed(self):
        '''
        Setter to reset cycles completed
        '''
        self.cycles_completed = 0

    def __repr__(self) -> str:
        return f"{repr(self.obj)} {hex(id(self.obj.symbol))}: {self.curr_cycle()} {self.n_cycles()}"

    # Wrapper functions
    def predicates(self) -> set:
        '''
        Wrapper function for object predicates
        '''
        return self.obj.predicates

    def antecedents(self) -> set:
        '''
        Wrapper function for object antecedents 
        '''
        return self.obj.antecedents

    def n_pre_warm(self) -> int:
        '''
        Wrapper for any pre-warming cycles 
        Tracking this is not yet implemented
        '''
        return self.obj.pre_warm()

    def n_cycles(self) -> int:
        '''
        Wrapper for number of cycles required
        '''
        return self.obj.n_cycles()

    def n_pre_warm_cycles(self) -> int:
        '''
        Wrapper for any pre-warming cycles 
        Tracking this is not yet implemented
        '''
        return self.obj.n_pre_warm_cycles()

    def non_local(self) -> bool:
        '''
        Checks if the bound object is non-local
        '''
        return self.obj.non_local()

    def satisfies(self, other) -> bool:
        '''
        Checks if the bound object satisfies a 
        dependency
        '''
        return self.get_symbol().satisfies(other.get_symbol())

    def get_obj(self) -> object:
        '''
        Wrapper for obj
        '''
        return self.obj.get_obj()

    def __hash__(self) -> int:
        '''
        Hashing for binds depends on the address
        rather than the value of the bind
        '''
        return id(self)

    # Cycle functions
    def cycle(self) -> int:
        '''
        Increments the cycle count  
        '''
        self.cycles_completed += 1
        return self.cycles_completed

    def curr_cycle(self) -> int:
        '''
        Number of cycles completed 
        '''
        return self.cycles_completed

    def resolved(self) -> bool:
        '''
        Has the operation resolved
        '''
        return self.cycles_completed >= self.n_cycles()

    def reset(self):
        '''
        Reset the number of cycles
        '''
        self.cycles_completed = 0

    def get_unary_symbol(self) -> Type[Symbol]:
        '''
        Wrapper for the unary symbol of the object
        '''
        return self.obj.get_unary_symbol()

    def __gt__(self, other) -> bool:
        '''
        Naive sorting methods  
        '''
        return True

    def __lt__(self, other) -> bool:
        '''
        Naive sorting methods  
        '''
        return False

    def __ge__(self, other) -> bool:
        '''
        Naive sorting methods  
        '''
        return True

    def __le__(self, other) -> bool:
        '''
        Naive sorting methods  
        '''
        return False

class AddrBind():
    '''
        Wrapper that promotes comparisons to addresses
    '''
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other) -> bool:
        if isinstance(other, AddrBind):
            return other.obj is self.obj
        return other is self.obj

    def __hash__(self) -> int:
        return self.obj.__hash__()

    def __repr__(self) -> str:
        return self.obj.__repr__()


class ExternBind(Bind):
    '''
    ExternBind
    Bind wrapper over binds for externs
    '''
    def __init__(self, obj):
        '''
            ExternBind
            Bind wrapper for extern objects
        '''
        # Nesting this ensures non-fungibility
        self.obj = Bind(obj)
        self.slack = float('-inf')

    def pre_warm(self) -> bool:
        '''
        Attempts to pre-warm 
        Currently not implemented
        '''
        if self.n_cycles() < self.n_pre_warm_cycles():
            self.cycle()
            return True
        return False

    def bind_extern(self, extern):
        '''
        Binds to an extern
        '''
        self.n_cycles = extern.n_cycles

    def n_cycles(self) -> int:
        '''
        Gets the current number of cycles 
        '''
        return self.obj.n_cycles()

    def is_factory(self) -> bool:
        '''
        Is this extern also a factory
        '''
        return self.obj.obj.is_factory()

    def __repr__(self) -> str:
        return f"{repr(self.obj)}\
 {hex(id(self.obj.obj.symbol))}:\
 {self.curr_cycle()} {self.n_cycles()}"

    # Wrappers
    def get_cycles_completed(self) -> int:
        '''
        Wrapper to get cycles completed
        '''
        return self.obj.get_cycles_completed()

    def set_cycles_completed(self, n_cycles):
        '''
        Setter for cycles completed
        '''
        self.obj.cycles_completed = n_cycles

    def reset(self):
        '''
        Wraps the reset call
        '''
        self.obj.reset()

    def cycle(self) -> int:
        '''
        Obj wrapper
        '''
        return self.obj.cycle()

    def curr_cycle(self) -> int:
        '''
        Obj wrapper
        '''
        return self.obj.curr_cycle()

    def n_pre_warm_cycles(self) -> int:
        '''
        Obj wrapper
        '''
        return self.obj.n_pre_warm_cycles()

    def antecedents(self) -> set:
        '''
        Obj wrapper
        '''
        return self.obj.antecedents()

    def predicates(self) -> set:
        '''
        Obj wrapper
        '''
        return self.obj.predicates()

    def is_extern(self) -> bool:
        '''
        ExterBinds are externs
        '''
        return True

    def resolved(self) -> bool:
        return self.obj.resolved()

    def __eq__(self, other) -> bool:
        return hash(self) == hash(other)

    def __hash__(self) -> bool:
        return id(self.obj.obj)

    def __is__(self, other) -> bool:
        return hash(self) == hash(other)

class DAGBind(Bind):
    '''
        Bind
        This allows us to override the regular hashing behaviour of another arbitrary object
        such that we can compare instances of symbols rather than symbol strings
        DAGBind objects additionally track slack
    '''
    def __init__(self, obj):
        self.slack = obj.slack
        self.symbol = obj.symbol
        super().__init__(obj)

    def wait(self):
        '''
        Waiting decreases the slack on the gate
        '''
        self.slack -= 1

    def satisfies(self, other):
        '''
            Unwraps bind objects to check dependencies
        '''
        if isinstance(other, Bind):
            return self.obj.symbol == other.obj.symbol
        return self.obj.symbol == other.symbol

    def pre_warm(self) -> bool:
        '''
        DAGBind objects cannot be pre-warmed
        '''
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
        return id(self.obj) == id(obj)

    def __hash__(self):
        return id(self.obj)

    def is_extern(self) -> bool:
        '''
           DAGBind objects are not ExternBinds 
        '''
        return False

class RouteBind(Bind):
    '''
        Bind object over routes 
    '''
    def __init__(self, gate, addresses):
        self.addresses = addresses
        self.scope = gate.scope
        super().__init__(gate)

    def __eq__(self, other):
        if isinstance(other, RouteBind):
            return other.obj is self.obj
        return other is self.obj

    def __hash__(self):
        return self.obj.__hash__()

    def __repr__(self):
        return self.obj.__repr__()

    def rotates(self):
        '''
            Obj Wrapper
        '''
        return self.obj.rotates()

    def n_ancillae(self):
        '''
            Obj Wrapper
        '''
        return self.obj.n_ancillae

    def ancillae_type(self):
        '''
            Obj Wrapper
        '''
        return self.obj.ancillae_type

    def is_extern(self):
        '''
            Obj Wrapper
        '''
        return self.obj.is_extern()

    def is_factory(self):
        '''
            Obj Wrapper
        '''
        return self.obj.is_factory()
