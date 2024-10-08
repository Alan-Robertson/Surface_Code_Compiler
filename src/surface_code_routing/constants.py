from surface_code_routing.bind import AddrBind
from surface_code_routing.symbol import Symbol 

SINGLE_ANCILLAE = AddrBind('single')
ELBOW_ANCILLAE = AddrBind('elbow')

# Used by Allocators
COULD_NOT_ALLOCATE = AddrBind("Failed to Allocate Patch")

COULD_NOT_ROUTE = Symbol('ROUTE')
