from itertools import chain, count
from surface_code_routing.qcb import SCPatch
from surface_code_routing.utils import debug_print
from surface_code_routing.instructions import pure_ancillae_instruction_factory
from surface_code_routing.bind import RouteBind, AddrBind

ancillae_teleport = pure_ancillae_instruction_factory('Teleport', n_cycles=1) 

class TeleportInjector():
    '''
        Injects teleportation circuits at intersections
        This is performed oppotunistically, rather than when a collision actually occurs
        Schedulers may be ASAP or ALAP
        ASAP results in fragmented chains of teleportations
        ALAP results potentially results in singlar larger teleportations

        TODO: create an intersection graph and teleport around that where possible
    '''
    DEFAULT_INTERSECTION = lambda self, x, y: (False, None)
    def __init__(self, router, 
                 scheduler='ASAP',
                 n_switch_route_adjacencies=2,
                 verbose=False):

        self.router = router
        self.graph = router.graph
        self.switches = dict()
        self.scheduler = scheduler
        self.verbose = verbose
        self.n_switch_route_adjacencies = n_switch_route_adjacencies
    
        # Find locations to set up teleport switches
        self.find_switches()

    def find_switches(self):
        # Currently only supports routes that are adjacent to other routes
        # Definitionally this ensures that you can't miss or re-order a register by teleporting past its adjacent node
        # This can build chains of teleports that can also be merged
        # This won't match any gates or None
        # This does turn large regions of routes into large teleport nexi
        probe = object()
        for i in range(self.graph.shape[0]):
            for j in range(self.graph.shape[1]):
                graph_node = self.graph[i, j]
                if ((graph_node.state is SCPatch.ROUTE)
                    # Only teleport if surrounded on all sides by routes
                    and (len(list(i for i in graph_node.adjacent(probe) if i.state is SCPatch.ROUTE)) <= self.n_switch_route_adjacencies)):
                        self.debug_print(f"Found teleport switch location {graph_node}") 
                        self.switches[graph_node] = TeleportSwitch(graph_node, self) 
        return

    def __call__(self, *args, **kwargs):
        return self.teleport(*args, **kwargs)

    def teleport(self, computational_gate, addresses, curr_cycle):
        teleport_operations = []
        address_locks = dict((address, False) for address in addresses)
        if computational_gate.non_local() and computational_gate.n_ancillae() == 0:
            for address in addresses:
                success, teleport_operation = self.switches.get(address, self.DEFAULT_INTERSECTION)(addresses, curr_cycle)
                if success is True:
                    self.debug_print(f"Injecting Teleport: {computational_gate} {teleport_operation} {addresses}")
                    teleport_operation.schedule(self.scheduler)
                    teleport_operations.append(teleport_operation)
                    for address in teleport_operation.intersection:
                        address_locks[address] = True

        # Merge simultaneous adjacent teleport operations
        teleport_operations = self.merge_teleportations(teleport_operations)
       
        # Check no-operations were subsumed across different cycles, there's almost certainly a neater way to do this
        teleport_operations = filter(lambda teleport: all(map(lambda address: not address_locks[address], 
                                                          teleport.endpoints)), 
                                     teleport_operations)

        for operation in teleport_operations:
            operation.inject_teleportation(computational_gate, self.router.routes, self.router.layers)

            # Teleported around these patches
            for patch in operation.intersection:
                addresses.remove(patch)
        return

    def debug_print(self, *msg):
        debug_print(*msg, debug=self.verbose)

    def merge_teleportations(self, teleport_operations):
        '''
        Merges teleportation operations that share a endpoints in the same cycle
        Currently this only applies to adjacent teleportations that occur in a single cycle
                | |           | |
               *A*B*   ->    *****
                | |           | | 
        '''
        for operation_a in (operation_a for operation_a in teleport_operations 
                            if not operation_a.merged):
            for operation_b in (operation_b for operation_b in teleport_operations 
                                if ((operation_b is not operation_a) 
                                and (operation_b.cycle == operation_a.cycle)
                                and (not operation_b.merged))):
                operation_a.merge(operation_b)
                if operation_b.merged:
                    self.debug_print(f"Merged {operation_a}, {operation_b}")
        teleport_operations = [op for op in teleport_operations if not op.merged]
        return teleport_operations


class TeleportOperation():
    def __init__(self, endpoints, intersection, cycle, curr_cycle, verbose=False):
        self.cycle = cycle
        self.curr_cycle = curr_cycle
        self.endpoints = list(endpoints)
        self.intersection = [intersection]
        self.scheduled = False # cycle currently reports earliest possible cycle

        # Flag for merging teleportation operations
        self.merged = False
        self.verbose = verbose

    def schedule(self, scheduler):
        # TODO: Wrap this into something more modular and extensible
        # Can schedule
        if scheduler == 'ALAP':
            self.cycle = self.curr_cycle - 1
        elif scheduler == 'ASAP':
            self.cycle = self.cycle 
        else:
            raise Exception(f"Unknown Scheduler {self.scheduler}")

    def merge(self, other):
        if self.curr_cycle != other.curr_cycle:
            return

        overlap = 0
        for endpoint in other.endpoints:
            if endpoint in self.intersection:
                overlap += 1

        # Already subsumed
        if overlap == len(other.endpoints): 
            other.merged = True
            return
        
        # One end subsumed
        if overlap > 0:
            other.merged = True
            anchor_self = None
            anchor_other = None

            for idx, patch in enumerate(other.intersection):
                if self.endpoints[0] == patch:
                    anchor_other = idx
                    anchor_self = 0
                    break
                elif self.endpoints[-1] == patch:
                    anchor_other = idx
                    anchor_self = 1
                    break

            if anchor_self == 1: 
                self.intersection += other.intersection[anchor_other:]
                self.endpoints[-1] = other.endpoints[-1]

            elif anchor_self == 0:
                self.intersection = other.intersection[:anchor_other + 1] + self.intersection
                self.endpoints[0] = other.endpoints[0]

            else:
                raise exception("Bleugh")
            return

        for endpoint in self.endpoints: 
            # Endpoints are shared, merge
            if endpoint in other.endpoints:
                shared_endpoint = endpoint
                self.endpoints.remove(shared_endpoint)
                if shared_endpoint in self.intersection[0].adjacent(object()):
                    self.intersection = other.intersection + [shared_endpoint] + self.intersection
                else:
                    self.intersection = self.intersection + [shared_endpoint] + other.intersection

                self.endpoints += other.endpoints
                # Second copy from the other operation removed
                self.endpoints.remove(shared_endpoint)

                other.merged = True
                return 

    def __repr__(self):
        return f"Teleport: {self.cycle}, {self.endpoints} -> {self.intersection}"

    def __str__(self):
        return self.__repr__()

    def __call__(self, *args, **kwargs):
        return self.inject_teleportation(*args, **kwargs)

    def inject_teleportation(self, computational_gate, routes, layers):
        # TODO Or rather to consider:
        # Should inject into DAG or not?
        # Argument for: probs should keep track of everything
        # Argument against; makes it difficult to figure out what is actually a logical vs a physical operation
        if self.curr_cycle is None:
            raise Exception("Scheduler pass has not been performed")

        gate = self.gate()
        bound_gate = AddrBind(gate)
        routes[bound_gate] = gate.addresses
        layers[self.cycle].append(gate)
        gate.obj.antecedants = {computational_gate}
        for address in self.endpoints:
            address.last_used = self.curr_cycle
        for address in self.intersection:
            address.last_used = self.cycle
        return

    def gate(self):
        gate = ancillae_teleport() 
        addresses = list(self.intersection)

        if self.endpoints[0] in self.intersection[0].adjacent(object()):
            addresses.insert(0, self.endpoints[0])
            addresses.insert(len(addresses), self.endpoints[1])
        else:
            addresses.insert(len(addresses), self.endpoints[0])
            addresses.insert(0, self.endpoints[1])
        gate = RouteBind(gate, addresses)
        return gate

class TeleportSwitch():
    def __init__(self, intersection, teleport_injector, nodes=None, verbose=False):
        self.last_used = -1
        self.intersection = intersection
        if nodes is None:
            nodes = set(i for i in intersection.adjacent(object()) if i.state is SCPatch.ROUTE)
        self.nodes = nodes
        self.teleport_injector = teleport_injector
        self.verbose = verbose
       
    def __call__(self, *args, **kwargs):
        return self.teleport_switch(*args, **kwargs)

    def debug_print(self, *msg):
        debug_print(*msg, debug=self.verbose)

    def teleport_switch(self, addresses, curr_cycle):
        teleportation_endpoints = []
        self.debug_print(f"Testing {self.intersection} {self.nodes} : {addresses} on {curr_cycle}")
        for patch in addresses:
            if patch in self.nodes:
                teleportation_endpoints.append(patch)
        self.debug_print(f"Endpoints: {teleportation_endpoints}")
        
        if len(teleportation_endpoints) > 2:
            # More complex operation, teleportation not trivially possible
            return False, None
        
        if len(teleportation_endpoints) <= 1:
            # Something odd, possibly being used as an ancillae
            return False, None

        # By implication this is only called when the operation requires one entrypoint and one exit
        earliest_teleportation_cycle = max(map(lambda x: x.last_used + 1, chain(teleportation_endpoints, [self.intersection]))) + 1 

        # Need at least one cycle
        if earliest_teleportation_cycle >= curr_cycle:
            return False, None
        
        teleport_operation = TeleportOperation(teleportation_endpoints, self.intersection, earliest_teleportation_cycle - 1, curr_cycle)

        return True, teleport_operation            
            
