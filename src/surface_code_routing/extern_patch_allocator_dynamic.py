from surface_code_routing.bind import AddrBind
from surface_code_routing.constants import COULD_NOT_ALLOCATE  

class ExternPatchAllocatorDynamic():
   

    def __init__(self, externs, patches):
        self.patches = list(map(ExternPatch, patches))
        self.extern_qcbs = externs
        self.locks = {}
        self.queue = []

        # Sort based on total area and minimise use of that
        self.patches.sort(key=lambda patch: patch.height * patch.width)

    def alloc(self, gate):
        qcb = self.externs[gate]
        height = qcb.height
        width = qcb.width

        for patch in (patch for patch in self.patches if not patch.locked()):
            if patch >= qcb:
                self.locks[gate] = patch
                patch.lock(gate)
                return patch.get_qcb()
        return COULD_NOT_ALLOCATE

    def free(self, gate):
        self.locks[gate].unlock()


class ExternPatch():
    '''
        Wrapper class for handling locks over QCB segments
    '''
    def __init__(self, patch):
        self.patch = patch
        self.height = patch.height
        self.width = patch.width
        self.lock_cond = None
 
    def get_qcb(self):
        return self.patch

    def locked(self):
        return self.lock_cond is not None

    def lock(self, gate):
        self.lock_cond = gate

    def unlock(self):
        if self.lock_cond is None:
            raise Exception(f"Double Free on {self}")
        self.lock_cond = None

    def __repr__(self):
        return self.patch.__repr__()
    def __str__(self):
        return self.__repr__()

    def __gt__(self, other):
        return (self.height > other.height) and (self.width > other.width)

    def __ge__(self, other):
        return (self.height >= other.height) and (self.width >= other.width)

