class SCPatch():
    def __init__(self):
        pass


class QCB():

    def __init__(self, height, width, **msfs):
        self.msfs = {i.symbol:i for i in msfs}
        self.height = height
        self.width = width
        self.qcb = np.array((width, height), SCPatch)

    def build(self, dag):
        return
        