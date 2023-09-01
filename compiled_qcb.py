import copy

class CompiledQCB:
    def __init__(self, qcb, router, dag):
        self.dag = dag
        self.router = router
        self.qcb = qcb

        self.symbol = qcb.symbol.extern()
        self.n_cycles = lambda : len(router.layers)
        self.n_pre_warm_cycles = lambda : 0
        self.width = qcb.width
        self.height = qcb.height
        self.externs = qcb.externs
        self.predicate = qcb.symbol
    
    def is_extern(self):
        return True

    def instantiate(self):
        return CompiledQCB(self.qcb, self.router, self.dag) 

    def satisfies(self, other):
        return self.symbol.satisfies(other)

    def get_symbol(self):
        return self.symbol

    def get_obj(self):
        return self
    
    def __call__(self, args, targs):
        pass

    def instruction(self, args, targs):
        args = tuple(map(symbol_resolve, args))
        targs = tuple(map(symbol_resolve, targs))

        sym = self.predicate 
        fn = copy.deepcopy(self.symbol)
        scope = Scope({fn:fn})

        dag = DAG(sym, scope=scope)
        for arg, fn_arg in zip(args, sym.ordered_io_in()):
            dag.add_node(CNOT(factory(arg, fn(fn_arg))))
        
        dag.add_node(factory, n_cycles=self.n_cycles)

        for targ, fn_arg in zip(args, sym.ordered_io_out()):
            dag.add_node(CNOT(factory(arg, fn(fn_arg))))

        dag.add_gate(CNOT(factory('factory_out'), targ))
        dag.add_gate(RESET(factory))
        return dag
