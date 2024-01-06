from abc import ABC, abstractmethod

class ExternPatchAllocator(ABC):

    @abstractmethod
    def alloc(self, gate):
        ...

    @abstractmethod
    def free(self, gate):
        ...

    @abstractmethod
    def lock(self, gate):
        ...
