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

