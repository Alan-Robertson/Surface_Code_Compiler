'''
    Abstract base class for extern patch allocators
'''
from abc import ABC, abstractmethod

class ExternPatchAllocator(ABC):
    '''
        Abstract base class for extern patch allocators
    '''
    @abstractmethod
    def alloc(self, gate):
        '''
            Allocate a patch given a dependent gate
        '''

    @abstractmethod
    def free(self, gate):
        '''
            Free an allocated patch given a dependent gate
        '''

    @abstractmethod
    def lock(self, gate):
        '''
           Lock an allocated patch given a dependent gate 
        '''
