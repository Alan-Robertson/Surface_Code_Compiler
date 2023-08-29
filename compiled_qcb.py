class CompiledQCB(self, qcb, router, dag):
    self.dag = dag
    self.router = router
    self.qcb = qcb

    self.symbol = qbc.symbol
    self.cycles = router.cycles
    self.width = qcb.width
    self.height = qcb.height
    self.externs = qcb.externs
