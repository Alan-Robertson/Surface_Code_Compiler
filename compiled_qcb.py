class CompiledQCB:
    def __init__(self, qcb, router, dag):
        self.dag = dag
        self.router = router
        self.qcb = qcb

        self.symbol = qcb.symbol.extern()
        self.cycles = len(router.layers)
        self.width = qcb.width
        self.height = qcb.height
        self.externs = qcb.externs

