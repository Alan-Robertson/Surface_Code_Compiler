'''
    QCB Segment Allocator
'''

from surface_code_routing.qcb import Segment, SCPatch, QCB
import surface_code_routing.utils as utils
from surface_code_routing.bind import AddrBind

class AllocatorError(Exception):
    '''
        Allocator error object
    '''

class Allocator:
    '''
        QCB Segment Allocator
    '''
    REG_INVARIANT_ABOVE = AddrBind("Register All Above")
    REG_INVARIANT_ABOVE_LEFT = AddrBind("Register Above or Left")
    REG_INVARIANT_DROP = AddrBind("Register Left Drop")

    EXTERN_INVARIANT_TIGHT = AddrBind("Extern Tight Placement")
    EXTERN_INVARIANT_RIGHT = AddrBind("Extern Right Edge Connection")
    EXTERN_INVARIANT_LEFT = AddrBind("Extern Left Connection")
    EXTERN_INVARIANT_LEFT_DROP = AddrBind("Extern Left Drop Connection")
    EXTERN_INVARIANT_BELOW = AddrBind("Extern First Placement")

    ROUTE_BLOCK = AddrBind("Route Block")
    REG_BLOCK = AddrBind("Reg Block")
    INVARIANT_FAILED = AddrBind("Failed")
    ROUTEABLE = (SCPatch.ROUTE, SCPatch.NONE)

    VERTICAL_UP = AddrBind("Vertical Up")
    VERTICAL_DOWN = AddrBind("Vertical Down")

    def __init__(self,
        qcb: QCB,  # qcb Object to allocate patches to
        *extern_templates,  # Template objects for externs
        optimise=True,  # Optimisation pass enabled
        tikz_build=False,  # Incremental tikz build enabled
        verbose=False,  # Verbose debugging info
        opt_space=False,  # Space optimisation (not currently used)
        opt_route=True,  # Route optimisation (not currently used)
        over_allocate=False # Early termination of optimisation
        ):
        '''
            :: qcb : QCB :: QCB object to allocate to
            :: *extern_templates :: Template externs
            :: optimise : bool :: Optimisation pass enabled / disabled  
            :: tikz_build : bool :: Incremental tikz building 
            :: verbose : bool :: Debug info
            :: over_allocate : bool :: Terminate optimisation only on space constraints  

            over_allocate is a useful setting for `faster' circuits where there's a chance 
            of missing an extern speedup    
        '''

        self.qcb = qcb
        self.qcb.allocator = self

        # Sort extern templates by width, then height
        self.extern_templates = sorted(extern_templates,
                                     key=lambda extern: (extern.width, extern.height),
                                     reverse=True)
        self.height = qcb.height
        self.width = qcb.width

        self.over_allocate = over_allocate

        if opt_space and opt_route:
            raise AllocatorError("Cannot optimise for both space and routes, these are mutually exclusive")
        self.opt_space = opt_space # Try to optimise space at the cost of routes
        self.opt_route = opt_route # Try to optimise routes at the cost of space

        self.io_width = len(qcb.io)
        self.io_connected = False
        self.contains_io = self.io_width > 0
        if not self.contains_io:
            self.io_connected = True
        self.io_segment = None

        self.reg_allocated = 0
        self.reg_quota = len(qcb.operations.internal_scope()) - len(qcb.operations.io())

        self.tikz_build = tikz_build
        self.tikz_str = ""
        self.verbose = verbose

        # optimise variables
        self.externs = []
        self.n_channels = 1

        # Perform initial minimal allocation
        self.allocate()

        # Continue to optimised allocation
        if optimise:
           self.optimise()

        self.route_remainder()


    def debug_print(self, *args):
        '''
            Debug printing conditional dispatch
        '''
        return utils.debug_print(*args, debug=self.verbose)

    def build_tikz_str(self):
        '''
            Incremental tikz build wrapper
        '''
        if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()

    def allocate(self):
        '''
            Initial allocation
            Places a minimal set of objects on the QCB to implement the DAG
        '''
        # Handle any initial io placement and set appropriate io invariants
        self.io_invariant()

        # Place initial extern objects
        for extern in self.extern_templates:
            self.global_left_merge()
            self.debug_print(f"Externs: {extern}")
            invariant = self.extern_invariant(extern)
            self.build_tikz_str()
            if invariant is self.INVARIANT_FAILED:
                raise AllocatorError(f"Not enough space for Extern {extern}")

            self.externs.append(extern.instantiate())

        # Attempt to connect io route to remainder of graph
        if len(self.extern_templates) > 0:
            self.io_route_invariant()

        # Iteratively place registers until quota is satisfied
        while self.reg_allocated < self.reg_quota:
            self.debug_print(f"Registers: {self.reg_allocated} / {self.reg_quota}")

            # Connect io route if no externs were placed earlier
            if (    self.contains_io
                    and (not self.io_connected)   # IO is not connected
                    and (len(self.extern_templates) == 0)  # No externs
                    and self.reg_allocated > 0  # Not the first pass of this
                ):
                self.io_route_invariant()

            # Have to global merge before attempting to retrieve segment
            self.global_merge_tl()
            free_segment = next(iter(self.get_free_segments()), None)
            if free_segment is None:
                raise AllocatorError("Not enough space for registers")

            # Attempt to place a register object
            invariant, _ = self.reg_invariant(free_segment)
            self.build_tikz_str()
            if invariant is self.INVARIANT_FAILED:
                raise AllocatorError("Not enough space for registers")

        self.debug_print(f"Registers: {self.reg_allocated} / {self.reg_quota}\n")
        return


    def optimise(self):
        '''
            Optimised allocation
            Continues allocating registers, externs and routes to reduce circuit depth
        '''
        # Attempts to allocate either an extern or a new channel
        dag = self.qcb.operations
        self.debug_print("Attempting to optimise remaining space\n")
        while self.optimise_invariant() is True:
            self.build_tikz_str()
            self.global_merge_tl()
            self.debug_print('\n')

        self.debug_print("Allocating Additional Channels")
        # Splits remaining blocks
        try:
            while self.allocate_channel() is True:
                self.n_channels += 1
                self.build_tikz_str()
        except AllocatorError:
            pass

        # Set final compilation in the DAG 
        n_layers, compiled_layers = dag.compile(self.n_channels, *self.externs)
        #self.qcb.compiled_layers = compiled_layers

        self.global_top_merge()
        self.global_left_merge()

        # Droppings routes and regs
        if self.tikz_build:
            self.tikz_str += self.qcb.__tikz__()

        self.global_merge_tl()
        self.optimise_flood_fill()

    def extern_invariant(self, extern, speculative=False):
        '''
            extern_invariant
            Attempts to place an extern
        '''
        placed = False
        self.global_merge_tl()
        for free_segment in self.get_free_segments():
            self.debug_print(f"Attempting to allocate {extern} {free_segment}")
            invariant, segment, routes = self.alloc_extern(extern, free_segment)
            if invariant is not self.INVARIANT_FAILED:
                self.place_extern_segment(segment, extern)
                self.place_route_segments(*routes)
                self.debug_print(f"Success: {extern} {segment}\n\n")
                return True
            else:
                self.global_merge_tl()
        if not speculative:
            raise AllocatorError(f"Could not allocate extern: {extern}, no valid placement")
        return False

    def reg_invariant(self, segment, fallback_route=True):
        self.debug_print(f"\nAttempting to allocate a register at {segment}")
        invariant, regs, routes = self.alloc_reg(segment)

        self.debug_print(invariant, regs, routes, '\n')
        if invariant is not self.INVARIANT_FAILED:
            if regs is None and routes is None:
                return invariant, None
            if regs is not None:
                self.place_reg_segments(*regs)
            if routes is not None:
                self.place_route_segments(*routes)

        # TODO this won't work due to splits in the reg
        elif fallback_route: # If can't place then fallback to route
            self.debug_print(f"Falling back to routing {segment}")
            self.place_route_segments(segment)
        return invariant, (regs, routes)

    def io_invariant(self):
        '''
            Allocate initial io segments
        '''
        if not self.contains_io:
            self.debug_print("No IO Needed")
            return
        if self.io_width > self.qcb.width:
            raise AllocatorError("QCB is not wide enough to support IO channel")

        io_segment = next(
                (seg for seg in self.get_free_segments()
                    if (seg.y_1 == self.qcb.height - 1
                        and seg.x_0 == 0)),
                 None)
        if io_segment is None:
           raise AllocatorError("No room for IO")

        confirm, segments = io_segment.split(self.qcb.height - 2, 0, 2, self.io_width)
        if confirm is None:
            raise AllocatorError("No room for IO")
        confirm(self.qcb.segments)

        io_chunk = next((seg for seg in segments
                           if (seg.y_0 == self.qcb.height - 2
                               and seg.x_0 == 0)),
                           None)
        confirm, segments = io_chunk.split_top(1)
        confirm(self.qcb.segments)

        io_route = min(segments)
        io_elements = max(segments)

        self.place_io_segments(io_elements)
        self.place_route_segments(io_route)
        self.io_segment = io_elements
        self.debug_print("IO Placed", io_elements)

        # See if a right drop is wise,
        if self.io_width < self.qcb.width - 1:
            route_seg = next((seg for seg in self.get_free_segments()
                   if (seg.y_0 == self.qcb.height - 2
                       and seg.x_0 == self.io_width)),
                None)
            confirm, segments = route_seg.split_left(1)
            right_route = next((seg for seg in segments if
                   (seg.y_0 == self.qcb.height - 2
                    and seg.x_0 == self.io_width)),
                None)
            confirm(self.qcb.segments)

            self.debug_print("IO Right Route", right_route)
            self.place_route_segments(right_route)
        return

    def io_route_invariant(self):
        '''
            Connects the IO route with the remainder of the routing graph
        '''
        self.debug_print("Injecting IO Route")
        if (not self.contains_io) or (self.io_connected):
            self.debug_print("IO was connected during a prior allocation")
            return

        io_route = Segment.leftmost_segment(self.io_segment.above)
        io_free_edge = Segment.leftmost_segment((seg for seg in io_route.above if seg.get_state() is SCPatch.NONE))
        # TODO
        # Edge case where io_free_edge is None
        success, routes = self.route_vertical_up(io_free_edge, io_free_edge.x_0)
        self.place_route_segments(*routes)
        self.debug_print(f"Placing IO route on {routes}")
        self.io_connected = True
        return


    def optimise_invariant(self) -> bool:
        '''
            Attempt an optimisation
        '''
        dag = self.qcb.operations
        if not self.get_free_segments():
            return False

        def heuristic(new_extern):
            '''
                Tests addding a route vs adding one of any extern
            '''
            if new_extern:
                return (new_extern, dag.compile(self.n_channels, *self.externs, new_extern)[0])
            else:
                return (new_extern, dag.compile(self.n_channels + 1, *self.externs)[0])

        options = [new_extern.instantiate() for new_extern in self.extern_templates]
        options.append(None)
        options = sorted(map(heuristic, options), key=lambda opt:opt[1])
        self.debug_print(options)
        curr_score = dag.compile(self.n_channels, *self.externs)[0]

        # Compare options
        if self.over_allocate:
            options = [opt[0] for opt in options if opt[1] <= curr_score]
        else:
            options = [opt[0] for opt in options if opt[1] < curr_score]

        # Attempt to perform a placement based on the options
        for new_extern in options:


            if not new_extern and self.allocate_channel():
                self.n_channels += 1
                return True
            elif new_extern and self.extern_invariant(new_extern, speculative=True):
                self.externs.append(new_extern)
                return True
        return False


    def optimise_flood_fill(self):
        '''
            Flood remaining areas
        '''
        self.debug_print("Flood Filling")
        while (segment := next(self.get_free_segments(), None)) is not None:
            self.debug_print(f"Attempting to flood fill {segment}")
            invariant, regs, routes = self.alloc_reg(segment)
            if invariant is self.INVARIANT_FAILED:
                break

            local_segments = []
            if routes is not None:
                route_segments = list(routes)
            else:
                route_segments = []

            if regs is None:
                regs = []
            register_segments = []

            self.debug_print(f"Reg:{regs}, Routes: {routes}")

            for register in regs:
                while register.width >= 3:
                    confirm, (left, register) = register.split_left(1)
                    confirm(self.qcb.segments)
                    register_segments.append(left)

                    confirm, (left, register) = register.split_left(1)
                    confirm(self.qcb.segments)
                    local_segments.append(left)

                if register.width == 2:
                    confirm, (left, register) = register.split_left(1)
                    confirm(self.qcb.segments)
                    register_segments.append(left)
                    local_segments.append(register)
                else:
                    register_segments.append(register)

            self.place_reg_segments(*register_segments)
            self.place_route_segments(*route_segments)
            self.place_local_segments(*local_segments)

            self.global_merge_tl()
            if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()
        return

    def alloc_extern(self, extern, segment):
        '''
            Place an extern segment
        '''
        # Check extern fits
        if extern.height > segment.height or extern.width > segment.width:
            self.debug_print("Extern does not fit, attempting to grow")
            #Try to grow the region
            if extern.width > segment.width:
                if extern.height <= segment.height:
                    segment = self.grow_segment(segment, only_right=True)
                else:
                    segment = self.grow_segment(segment)
            else:
                if extern.width <= segment.width:
                    segment = self.grow_segment(segment, only_below=True)
                else:
                    segment = self.grow_segment(segment, right_first=False)

            self.debug_print(f"New Segment: {segment}")
            # Tried to grow the region but it still didn't fit
            if segment is None or extern.height > segment.height or extern.width > segment.width:
                self.debug_print(f"Segment {segment} was too small to contain {extern}")
                return self.INVARIANT_FAILED, None, None

        confirm, segments = segment.split_top_left(extern.height, extern.width)
        confirm(self.qcb.segments)
        extern_segment = next((seg for seg in segments if seg.x_0 == segment.x_0 and seg.y_0 == segment.y_0), None)

        self.debug_print(f"Testing Segment: {extern_segment}")

        if len(extern_segment.below) == 0:
            self.debug_print("Could not route below")
            return self.INVARIANT_FAILED, None, None


        if ((extern_segment.x_0 == 0 and extern_segment.y_0 == 0) # First allocation, just place below
            or (any(seg.get_state() is SCPatch.ROUTE for seg in extern_segment.below) and # Already routable from below
                all(seg.get_state() in self.ROUTEABLE for seg in extern_segment.below))
            ):

            self.debug_print("First allocation, or routeable from below")
            success, extern, below_route = self.route_below(extern_segment)
            if success is not True:
                return self.INVARIANT_FAILED, None, None
            else:
                return self.EXTERN_INVARIANT_BELOW, extern[0], below_route

        success, extern, below_route = self.route_below(extern_segment)
        if not success:
            # Cannot route below
            return self.INVARIANT_FAILED, None, None

        # If already routed from below
        if (self.io_connected
            and len(extern_segment.below) > 0
            and any(seg.get_state() is SCPatch.ROUTE for seg in extern_segment.below)
            ):
            # Connected to routing net from below
            self.debug_print(f"Connected from below: {list(seg for seg in segment.below if seg.get_state() is SCPatch.ROUTE)}")
            return self.EXTERN_INVARIANT_LEFT, extern_segment, below_route

        # Check if already routed
        # should be single right element as the route has height 1
        left_seg = Segment.leftmost_segment(below_route)
        if left_seg is not None:
            left_probe = Segment.leftmost_segment(left_seg.left)
        else:
            left_probe = None

        if (left_probe is not None and left_probe.get_state() is SCPatch.ROUTE):
            # Connected to routing net from left
            return self.EXTERN_INVARIANT_LEFT, extern_segment, below_route


        # Try a right probe
        right_seg = Segment.rightmost_segment(below_route)
        if right_seg is not None:
            right_probe = Segment.rightmost_segment(right_seg.right)
        else:
            right_probe = None

        if (right_probe is not None and right_probe.get_state() is SCPatch.ROUTE):
            # Connected to routing net from left
            return self.EXTERN_INVARIANT_LEFT, extern_segment, below_route




        # Need to do a drop, start with a right drop up
        self.debug_print("Attempting Right Drop Up")
        success, _, routes = self.route_right_drop_up(extern_segment)
        if success is not self.INVARIANT_FAILED:
            return success, extern_segment, routes + below_route
        self.debug_print("Right drop failed")

        # Try a left drop up
        self.debug_print("Attempting Left Drop Up")
        success, _, routes = self.route_left_drop_up(extern_segment)
        if success is not self.INVARIANT_FAILED:
            return success, extern_segment, list(set(routes + below_route))
        self.debug_print("Left drop up failed")

        # Attempt a route down
        self.debug_print("Attempting Left Drop Down")
        success, _, routes = self.route_left_drop_down(extern_segment)
        if success is not self.INVARIANT_FAILED:
            return success, extern_segment, routes + below_route
        self.debug_print("Left drop down failed")

        # TODO Shift segment and route on the left
        return self.INVARIANT_FAILED, None, None

    def allocate_channel(self):
        '''
            Place a routing channel by splitting register segments
        '''
        self.global_merge_lt()

        longest_reg = max((seg
                           for seg in self.qcb.segments
                           if seg.state.state == SCPatch.REG
                           and seg.y_0 != 0
                           and seg.y_1 != self.height),
                           key=lambda seg:seg.width,
                           default=None)

        # Include top register this time
        # Avoids a trap where the only register is  
        # the top register and an early halt to optimisation occurs
        edge_reg = False
        if longest_reg is None:
            edge_reg = True
            longest_reg = max((seg
               for seg in self.qcb.segments
               if seg.state.state == SCPatch.REG),
               key=lambda seg:seg.width,
               default=None)

        if longest_reg is None or longest_reg.width == 1:
            return False

        split_x = (longest_reg.x_0 + longest_reg.x_1 + 1) // 2

        if not edge_reg:  # Don't split edge registers 
            affected_regs = [seg
                            for seg in self.qcb.segments
                            if seg.state.state == SCPatch.REG
                            and seg.x_0 <= split_x <= seg.x_1
                            and seg.width > 1
                            and seg.y_0 != 0
                            and seg.y_1 != self.height - 1]
        else:  # Include edge registers in the split
            affected_regs = [seg
                            for seg in self.qcb.segments
                            if seg.state.state == SCPatch.REG
                            and seg.x_0 <= split_x <= seg.x_1
                            and seg.width > 1
                            ]

        self.debug_print(f"Registers to split for channel: {affected_regs}")

        # Number of registers that we're going to lose to the channel
        n_reg_split = len(affected_regs)

        if n_reg_split == 0:
            return False # Nothing to split

        # Perform the split
        # First check that if this reduces the number of registers below the requirements
        # of the dag, that we attempt to allocate more registers to make up the difference    
        # if that fails then halt
        # This requires a multi-reg alloc, with rollback
        allocated_segments = []
        while ((self.reg_allocated - n_reg_split < self.reg_quota)
               and (segment := next(self.get_free_segments(),  None)) is not None):
            self.debug_print(f"Registers: ({self.reg_allocated} - {n_reg_split} / {self.reg_quota})")
            invariant, regs, routes = self.alloc_reg(segment)
            self.debug_print(f"Reg to support channel {invariant}, {regs}, {routes}")

            if invariant is self.INVARIANT_FAILED:
                # Failed to place enough registers
                self.debug_print("Not enough registers to create channels")
                for segment in allocated_segments:
                    segment.free()
                return False

            if regs is not None:
                self.place_reg_segments(*regs)
                allocated_segments += regs
            if routes is not None:
                self.place_route_segments(*routes)
                allocated_segments += routes

        self.debug_print(f"Registers: ({self.reg_allocated} - {n_reg_split} / {self.reg_quota})")
        if self.reg_allocated - n_reg_split < self.reg_quota:
            # Ran out of cells before getting enough routes
            for segment in allocated_segments:
                segment.free()
            return False

        for register in affected_regs:
            register.free()
            self.reg_allocated -= register.width
            confirm, (route, *segments) = register.split(register.y_0, split_x, 1, 1)
            confirm(self.qcb.segments)

            self.place_route_segments(route)
            self.place_reg_segments(*segments)
        self.debug_print("\n")
        return True

    def place_segment_of_type(self, seg_type, *segments):
        '''
            Small helper function to paint groups of segments
        '''
        self.debug_print(f"Placing {seg_type} at {segments}")
        for segment in segments:
            segment.set_state(seg_type)
            segment.allocate()

    def place_route_segments(self, *segments):
        '''
            Place route segments
        '''
        self.place_segment_of_type(SCPatch.ROUTE, *segments)
        if not self.io_connected:
            for segment in segments:
                if ((self.qcb.height - 3 >= segment.y_0)
                    and (self.qcb.height - 3 <= segment.y_1)
                    and (segment.x_0 <= self.io_width)):
                    self.debug_print("IO Connected")
                    self.io_connected = True

    def place_io_segments(self, *segments):
        '''
            Wrapper for placing IO segments
        '''
        self.place_segment_of_type(SCPatch.IO, *segments)

    def place_reg_segments(self, *segments):
        '''
            Wrapper for placing register segments
        '''
        self.place_segment_of_type(SCPatch.REG, *segments)
        for segment in segments:
            self.reg_allocated += segment.height * segment.width

    def place_extern_segment(self, segment, extern):
        '''
            Wrapper for placing extern segments
        '''

        segment.state = SCPatch(extern)
        segment.allocate()

    def place_local_segments(self, *segments):
        '''
            Sets segments to LOCAL ROUTE
        '''
        for segment in segments:
            if self.is_connected(segment):
                self.place_route_segments(segment)
            else:
                self.place_segment_of_type(SCPatch.LOCAL_ROUTE, segment)

    def is_connected(self, segment):
        '''
            Checks if a segment is connected to the routing bus
        '''
        return any(seg.get_state() is SCPatch.ROUTE for seg in segment.neighbours())

    def route_right_drop_up(self, segment):
        '''
                     +
            %%%%%%%%%+
            %       %+
            %       %+
            %       %+
            %%%%%%%%%+
                    @@
        '''
        # Not at the top, try a right drop
        below_probe = segment.rightmost_segment(segment.below)
        # Probe extends beyond range of block
        if below_probe.x_1 > segment.x_1:
            below_right_probe = below_probe
        else:
            below_right_probe = Segment.topmost_segment(below_probe.right)

        below_right_routeable = (
                (below_right_probe is not None)
                and (below_right_probe.get_state() in self.ROUTEABLE)
                )
        # Trying to find a viable right route
        if below_right_routeable:
            # Routing is possible, create the corner
            confirm, segments = below_right_probe.split(segment.y_1 + 1, segment.x_1 + 1, 1, 1)
            confirm(self.qcb.segments)
            below_right_route = next(seg for seg in segments if (
                (seg.x_0 == segment.x_1 + 1)
                and (seg.y_0 == segment.y_1 + 1)))

            # Try to route up the right hand side
            success, routes = self.route_vertical_up(below_right_route, segment.x_1 + 1)
            if success is True:
                return success, (segment, ), routes
        return self.INVARIANT_FAILED, None, None

    def route_left_drop_up(self, segment):
        '''
           +
           +%%%%%%%%%
           +%       %
           +%       %
           +%       %
           +%%%%%%%%%
           @@
        '''
        # Not at the top, try a left drop
        below_probe = Segment.leftmost_segment(segment.below)
        # Probe extends beyond range of block
        if below_probe.x_1 > segment.x_1:
            below_left_probe = below_probe
        else:
            below_left_probe = Segment.topmost_segment(below_probe.left)
        below_left_routeable = (
                (below_left_probe is not None)
                and (below_left_probe.get_state() in self.ROUTEABLE)
                )

        self.debug_print(f"Below: {below_probe} {below_probe.get_state() in self.ROUTEABLE}\nBelow Left: {below_left_probe} {below_left_routeable}")
        # Trying to find a viable left route
        if below_left_routeable is True:
            # If the below left probe was in ROUTE then it would have been caught by an earlier case, hence this implies that it is in NONE
            # Routing is possible, create the corner
            confirm, segments = below_left_probe.split(segment.y_1 + 1, segment.x_0 - 1, 1, 1)
            confirm(self.qcb.segments)
            below_left_route = next((seg for seg in segments if (
                (seg.x_0 == segment.x_0 - 1)
                and (seg.y_0 == segment.y_1 + 1))), None)

            # Try to route up the left hand side
            self.debug_print(f"Routing Up Left {below_left_route} {segment.x_1 - 1}")
            success, left_up_route = self.route_vertical_up(below_left_route, segment.x_0 - 1)
            if success is True:
                return success, (segment, ), left_up_route + [below_left_route]
        return self.INVARIANT_FAILED, None, None

    def route_left_drop_down(self, segment):
        '''
           %%%%%%%%%
           %       %
           %       %
           %       %
           %%%%%%%%%
           @
           +
           +
          ++
        '''
        # Not at the top, try a left drop down
        below_probe = Segment.leftmost_segment(segment.below)
        if below_probe is not None:
            # Route below has already created the below route, need to go one down
            drop_column = segment.x_0
            below_left_probe = next((seg for seg in below_probe.below if seg.x_0 <= drop_column and seg.x_1 >= drop_column), None)
            if below_left_probe is not None:
                success, left_down_route = self.route_vertical_down(below_left_probe, segment.x_0)

                if success:
                    return self.EXTERN_INVARIANT_LEFT_DROP, (segment, ), left_down_route
        return self.INVARIANT_FAILED, None, None

    def grow_segment(self, segment, right_first=True, only_right=False, only_below=False):
        '''
            Attempts to grow an unallocated segment horizontally and vertically
        '''
        # We aren't going to respect these variable names if the grow functions are reversed
        unbounded_right = (not only_below and len(segment.right) > 0
                         and all(seg.get_state() is SCPatch.NONE for seg in segment.right)
                         )
        unbounded_below = (not only_right and len(segment.below) > 0
                         and all(seg.get_state() is SCPatch.NONE for seg in segment.below)
                         )
        merged_segment = None
        self.debug_print(f"Unbound Right: {unbounded_right}\tUnbound Below: {unbounded_below}")
        while unbounded_right or unbounded_below:
            if right_first:
                if unbounded_right:
                    self.debug_print("Attempting to grow right")
                    merged_segment = self.grow_segment_right(segment)
                    if merged_segment is not None:
                        segment = merged_segment
                        self.debug_print(f"New Segment {segment}")
                    else:
                        unbounded_right = False
            if unbounded_below:
                self.debug_print("Attempting to grow below")
                merged_segment = self.grow_segment_below(segment)
                if merged_segment is not None:
                    segment = merged_segment
                    self.debug_print(f"New Segment {segment}")
                else:
                    unbounded_below = False
            if not right_first:
                if unbounded_right:
                    self.debug_print("Attempting to grow right")
                    merged_segment = self.grow_segment_right(segment)
                    if merged_segment is not None:
                        segment = merged_segment
                        self.debug_print(f"New Segment {segment}")
                    else:
                        unbounded_right = False
        return segment


    def grow_segment_right(self, segment):
        '''
            Attempts to grow the segment to the right
            This is useful for joining split unallocated segments into larger regions that may then
            support externs.
        '''
        # Possible to grow right
        if len(segment.right) > 0 and all(seg.get_state() is SCPatch.NONE for seg in segment.right):
            extra_width = min(seg.x_1 for seg in segment.right) - segment.x_1
            merging_segments = []
            for seg in segment.right:
                min_height = max(seg.y_0, segment.y_0)
                max_height = min(seg.y_1, segment.y_1)
                confirm, segments = seg.split(min_height, segment.x_1 + 1, max_height - min_height + 1, extra_width)
                confirm(self.qcb.segments)
                merging_segments.append(next(iter(seg for seg in segments if seg.x_0 == segment.x_1 + 1 and seg.y_0 == min_height), None))

            merged_segment = None
            for seg in sorted(merging_segments):
                if merged_segment is None:
                    merged_segment = seg
                else:
                    confirm, merged_segment = merged_segment.vertical_merge(seg)
                    if confirm is None:
                        return None
                    confirm(self.qcb.segments)
            return merged_segment
        return None

    def grow_segment_below(self, segment):
        '''
            Attempts to grow the segment down
            This is useful for joining split unallocated segments into larger regions that may then
            support externs.
        '''

        # Possible to grow below
        if len(segment.below) > 0 and all(seg.get_state() is SCPatch.NONE for seg in segment.below):
            extra_height = min(seg.y_1 for seg in segment.below) - segment.y_1
            self.debug_print(f"Growing Height: {extra_height}")
            merging_segments = []
            for seg in list(segment.below):
                min_width = max(seg.x_0, segment.x_0)
                max_width = min(seg.x_1, segment.x_1)
                confirm, segments = seg.split(segment.y_1 + 1, min_width, extra_height, max_width - min_width + 1)
                confirm(self.qcb.segments)
                merging_segments.append(next(iter(seg for seg in segments if seg.y_0 == segment.y_1 + 1 and seg.x_0 == min_width), None))

            merged_segment = None
            for seg in sorted(merging_segments):
                if merged_segment is None:
                    merged_segment = seg
                else:
                    confirm, merged_segment = merged_segment.horizontal_merge(seg)
                    confirm(self.qcb.segments)
            confirm, merged_segment = segment.vertical_merge(merged_segment)
            confirm(self.qcb.segments)
            return merged_segment
        return None

    def alloc_reg(self, segment):
        '''
            Given the current free segment, try to allocate a register
            If this function does not return INVARIANT_FAILED then register allocation is feasible
        '''
        # Try the split to get a height 1 register
        # TODO check below routable, split left and end cap
        confirm, segments = segment.split_top(1)
        if confirm is None:
            self.debug_print("Failed initial split")
            return self.INVARIANT_FAILED, None, None

        # The segment to allocate as a register
        reg_segment = segments[0]
        if reg_segment.width == 1:
            self.debug_print(f"Width 1 Segment {reg_segment}")
            confirm(self.qcb.segments)
            return self.route_single_reg(reg_segment)


        # Check if this segment would already be routable from above
        if len(self.extern_templates) == 0 and reg_segment.y_0 == 0:
            self.debug_print("Top of QCB Route, No Externs")

            ###
            # No externs, no IO top route
            #
            # ----------
            # ++++++++++
            #
            confirm(self.qcb.segments)
            success, regs, routes = self.route_below(reg_segment)
            if success is True:
                return self.REG_INVARIANT_ABOVE, regs, routes
            else:
                return self.INVARIANT_FAILED, None, None

        if ((len(segment.above) > 0) # Don't do this if you're at the top
             and (all(x.get_state() is SCPatch.ROUTE for x in segment.above))):
            self.debug_print("Routeable from the top")
            ###
            # Routeable from above
            #
            # ++++++++
            # --------
            #
            confirm(self.qcb.segments)
            invariant, regs, routes = self.route_reg_from_above(reg_segment)
            if invariant is not self.INVARIANT_FAILED:
                return self.REG_INVARIANT_ABOVE, regs, routes

        # Clearing the bottom row as a special case as it cannot be routed from below
        if (segment.y_0 > self.qcb.height - 2):
            invariant, regs, _ = self.route_reg_final_row(reg_segment)
            return self.REG_INVARIANT_ABOVE, regs, None

        # From here on out we assume you can be routed from below

        ####
        # Segment cannot be routed from above
        # Split to create a probe on the left
        #
        #       ?%%%%%%%%%
        #       @---------
        #
        confirm(self.qcb.segments)
        confirm, segments = reg_segment.split_top_left(1, 1)
        probe_segment, reg_segment = segments
        # If this is the top row then it gets split
        #
        #      *?%%%%%%%%% Top Probe
        #      ?@--------- Left Probe
        #      ?           Bottom Probe
        left_probe = next(iter(probe_segment.left), None)
        top_probe = next(iter(probe_segment.above), None)
        left_probe_routable = ((left_probe is not None)
                               and (left_probe.get_state() is SCPatch.ROUTE)
                               )
        top_probe_routable = ((top_probe is not None)
                              and (top_probe.get_state() is SCPatch.ROUTE)
                              )

        if left_probe is None:
            bottom_probe = None
            bottom_probe_routable = False
        else:
            bottom_probe = Segment.rightmost_segment(left_probe.below)
            if (bottom_probe is not None) and (bottom_probe.get_state() is SCPatch.ROUTE):
                bottom_probe_routable = True
            else:
                bottom_probe_routable = False

        routeable_below = (len(reg_segment.below) > 0 and (all(seg.get_state() in self.ROUTEABLE for seg in reg_segment.below)))
        if not routeable_below:
            return self.INVARIANT_FAILED, None, None

        self.debug_print(f"Top Probe {top_probe} : {top_probe_routable}\nLeft Probe {left_probe} : {left_probe_routable}\nBottom Probe {bottom_probe} : {bottom_probe_routable}")

        if left_probe_routable and len(left_probe.below) > 0:
            #      *%%%%%%%%%%
            #      +@---------
            #      ?
            self.debug_print(f"Route Reg from Left {left_probe}")
            confirm(self.qcb.segments)
            regs, routes = self.route_reg_from_left(left_probe, probe_segment, reg_segment)
            return self.REG_INVARIANT_ABOVE_LEFT, regs, routes

        if top_probe_routable:
            # Left is not routeable, check above
            #       ?%%%%%%%%%
            #      %@---------
            confirm(self.qcb.segments)
            self.debug_print(f"Route Reg from Top Left {top_probe} {probe_segment}")
            regs, routes = self.route_reg_from_top_left(probe_segment, reg_segment)
            return self.REG_INVARIANT_ABOVE_LEFT, regs, routes

        # All else failed, attempt to drop left
        confirm(self.qcb.segments)
        success, routes = self.route_vertical_down(
                               next(iter(probe_segment.below), None),
                               probe_segment.x_0)
        if success:
            success, _, bottom_route = self.route_below(reg_segment)
            return self.REG_INVARIANT_DROP, (probe_segment, reg_segment), routes + bottom_route

        # Could not find a routing strategy that doesn't violate the invariant
        # Fail
        return self.INVARIANT_FAILED, None, None

    def route_single_reg(self, segment):
        '''
            Adds routes for single width registers
        '''
        above = next(iter(segment.above), None)
        left = next(iter(segment.left), None)
        below = next(iter(segment.below), None)
        if below is not None:
            if below.x_0 < segment.x_0:
                below_left = below
            else:
                below_left = Segment.topmost_segment(below.left)
        else:
            below_left = None
        above_routeable, left_routeable, below_routeable, below_left_routeable = ((x is not None) and (x.get_state() in self.ROUTEABLE) for x in (above, left, below, below_left))

        self.debug_print(f"Top Probe {above} : {above_routeable}\nLeft Probe {left} : {left_routeable}\nBottom Probe {below} : {below_routeable}\nBelow Left Probe {below_left} : {below_left_routeable}")

        if above is None:
            # Top of the QCB, route down
            success, routes = self.route_vertical_down(below, segment.x_0)
            if success is True:
                return self.REG_INVARIANT_DROP, (segment, ), routes

        if below_routeable is True and below.get_state() is SCPatch.ROUTE:
            # Already attached to a routing path
            return self.REG_BLOCK, (segment, ), None

        if (above_routeable
            and left_routeable
            and (above.get_state() is SCPatch.ROUTE and left.get_state() is SCPatch.ROUTE)
            ):
            # These two routes must be already connected elsewhere
            return self.REG_BLOCK, (segment, ), None

        if (left_routeable and below_routeable and below_left_routeable and left.get_state() is SCPatch.ROUTE):
            # Left can be routed, if we can join via below left then we can route

            if below_left is below:
                # Below joins up with below left, create a route
                # Below cannot already be a route as that was caught earlier
                confirm, segments = below.split(segment.y_1 + 1, segment.x_0 - 1, 1, 2)
                below_route = next((seg for seg in segments if seg.x_0 == segment.x_0 - 1 and seg.y_0 == segment.y_1 + 1), None)
                confirm(self.qcb.segments)
                return self.REG_BLOCK, (segment, ), (below_route, )

            else:
                # These are two separate blocks, create two routes
                confirm, segments = below.split(segment.y_1 + 1, segment.x_0, 1, 1)
                below_route = next((seg for seg in segments if seg.x_0 == segment.x_0 and seg.y_0 == segment.y_1 + 1), None)
                confirm(self.qcb.segments)

                # Below left route
                if below_left.get_state() is SCPatch.NONE:
                    confirm, segments = below_left.split(segment.y_1 + 1, segment.x_0 - 1, 1, 1)
                    below_left_route = next((seg for seg in segments if seg.x_0 == segment.x_0 - 1 and seg.y_0 == segment.y_1 + 1), None)
                    confirm(self.qcb.segments)
                    return self.REG_BLOCK, (segment, ), (below_route, below_left_route)

                else:
                    # Below left is already a route, don't worry about it
                    return self.REG_BLOCK, (segment, ), (below_route, )
        self.place_local_segments(segment)
        return self.ROUTE_BLOCK, None, None


    def route_reg_from_left(self, left_probe, probe, segment):
        '''
            Routes along the left hand side of a segment
        '''
        if ((left_probe.y_1 > probe.y_1) # Two high, this implies a route below
               or (left_probe.rightmost_segment(left_probe.below).get_state() is SCPatch.ROUTE)
               ):
                #      **%%%%%%%%%
                #      +@---------
                #      +
                confirm, segment = probe.horizontal_merge(segment)
                confirm(self.qcb.segments)
                ###
                #      **%%%%%%%%%
                #      +----------
                #      +++++++++++
                success, reg_segments, route_segments = self.route_below(segment)
                assert success
                return reg_segments, route_segments
        else:
           below_left_probe = next((seg for seg in left_probe.below if seg.x_0 <= left_probe.x_0 and seg.x_1 >= left_probe.x_1), None)
           if below_left_probe is not None and below_left_probe.get_state() in self.ROUTEABLE:
                # Can just route below
                confirm, segment = probe.horizontal_merge(segment)
                confirm(self.qcb.segments)
                _, reg_segments, route_segments = self.route_below(segment)

                below_probe = Segment.leftmost_segment(segment.below)
                if below_probe.x_0 < segment.x_0:
                   below_left_probe = segment.x_0
                else:
                   below_left_probe = next((seg for seg in below_probe.left if seg.y_0 <= below_probe.y_0 and seg.y_1 >= below_probe.y_1), None)

                if below_left_probe.get_state() is SCPatch.NONE:
                  confirm, segments = below_left_probe.split(below_probe.y_0, below_probe.x_0 - 1, 1, 1)
                  confirm(self.qcb.segments)
                  below_left_probe = next((seg for seg in segments if seg.x_0 == below_probe.x_0 - 1 and seg.y_0 == below_probe.y_0), None)
                  return reg_segments, route_segments + [below_left_probe]

        # Can dip in to route
        ###
        #      **%%%%%%%%%
        #      ++---------
        #      *++++++++++
        success, reg_segments, route_segments = self.route_below(segment)
        assert success
        return reg_segments, [probe] + route_segments


    def route_reg_from_top_left(self, probe, segment):
        '''
            Routes to the top left corner of a segment
        '''
        # Above of probe is routable
        #       +%%%%%%%%%
        #      %@---------
        self.debug_print(probe, segment)
        if not any(seg.get_state() in self.ROUTEABLE for seg in segment.below):
            max_x_0 = min(segment.x_1, next((seg.x_0 for seg in Segment.left_to_right(segment.above) if seg.get_state() is not SCPatch.ROUTE), segment.x_1))
            if max_x_0 == segment.x_0:
                # Not salvageable
                return None, None

            if max_x_0 <= segment.x_1:
                self.debug_print(f"Splitting to route {segment} {max_x_0}")
                confirm, segments = segment.split_left(max_x_0 - segment.x_0 - 1)
                confirm(self.qcb.segments)
                segment = next((seg for seg in segments if seg.x_0 == segment.x_0), None)

        success, probe, route_below_probe = self.route_below(probe)
        assert success
        success, regs, route_below = self.route_below(segment)
        assert success
        #       +%%%%%%%%%
        #      %+---------
        #       ++++++++++
        return regs, (*probe, *route_below_probe, *route_below)


    def route_reg_from_above(self, segment):
        '''
    Routes from above
    Routeable from above
    # ++++++++
    # --------
        '''

        confirm, segments = segment.split_top_left(1, 1)
        potential_route_segment, reg_segment = segments
        # May already be routeable from the left
        # In this instance the next row is routeable, so we handle a special case
        #
        #       *++++++++++
        #       +@---------
        #       +
        if len(potential_route_segment.left) > 0:
            # Check the left element, it should exist if the previous check passed
            left_element = next(iter(potential_route_segment.left))
            self.debug_print("Trying Left Route")

            # The left edge must be routeable, otherwise fallback
            if left_element.get_state() is SCPatch.ROUTE:
                self.debug_print("Left Element Routeable")
                # The routable left edge may either extend past the current y coordinate
                if left_element.y_1 > reg_segment.y_1:
                    # Don't confirm, rollback the split
                    self.debug_print("Rolling back the split")
                    return self.REG_INVARIANT_ABOVE, (segment, ), None

                # Routable left edge is split vertically
                # Two block case
                else:
                    confirm(self.qcb.segments)
                    probe_existing_route = Segment.rightmost_segment(left_element.below)
#                    if probe_existing_route is not None:
                    if probe_existing_route is None or probe_existing_route.get_state() in self.ROUTEABLE:
                        return self.REG_INVARIANT_ABOVE, (potential_route_segment, reg_segment), None
            else:
                confirm(self.qcb.segments)
        # Can't route from right, have to use route through the probe
        #       *++++++++++
        #       %@---------
        #       %
        else:
            confirm(self.qcb.segments)
        return self.REG_INVARIANT_ABOVE, (reg_segment,), (potential_route_segment,)


    def route_reg_final_row(self, segment):
        '''
            Register routing for the bottom row
        '''
        # Segment should be 1 high on the bottom row
        reg_segments = []
        prev_seg = None
        while (seg := Segment.leftmost_segment(segment.above)) is not prev_seg:
            confirm, segments = segment.split_left(min(segment.x_1, seg.x_1) - segment.x_0 + 1)
            confirm(self.qcb.segments)
            if len(segments) == 2:
                probe, segment = segments
            else:
                probe = segments[0]
            if seg.get_state() is SCPatch.ROUTE:
                reg_segments.append(probe)
            else:
                self.place_local_segments(probe)
                prev_seg = seg
            prev_seg = seg
        return self.REG_INVARIANT_ABOVE, reg_segments, None

    def route_below(self, segment, fallback_split=False, fallback_end_cap=False, exclude=None):
        '''
        Place route below segment
         ------------
         ++++++++++++
        '''
        if exclude is None:
            exclude = set()

        self.debug_print(f"Routing below {segment}")
        routing_elements = list()
        for potential_route in Segment.left_to_right(segment.below):
            # As routing below may impact other allocations we can exclude particular elements
            if potential_route in exclude:
                self.debug_print("Excluded", potential_route, exclude, potential_route in exclude)
                continue

            self.debug_print(f"Potential Route: {potential_route} {potential_route.get_state()}")
            if potential_route.get_state() not in self.ROUTEABLE:
                if not fallback_split or len(routing_elements) == 0:
                    self.debug_print("Not possible to route below")
                    # Nothing below was ever routable
                    # or don't fallback, just fail
                    return False, None, None
                # TODO split segment and end cap

            if potential_route.get_state() is SCPatch.NONE:
                route_left = max(segment.x_0, potential_route.x_0)
                route_right = min(segment.x_1, potential_route.x_1)
                width = route_right - route_left + 1

                confirm, segments = potential_route.split(segment.y_1 + 1, route_left, 1, width)
                confirm(self.qcb.segments)
                potential_route = next((seg for seg in segments if seg.x_0 == route_left and seg.y_0 == segment.y_1 + 1), None)
                self.debug_print(f"Splitting for route: {potential_route}")
                routing_elements.append(potential_route)

            # If it's in routable but is not a route, then skip it
        self.debug_print(f"Sucessfully routed below {segment} : {routing_elements}")
        return True, (segment, ), routing_elements

    def route_vertical_up(self, *args, **kwargs):
        '''
            Routes vertically up
        '''
        return self.route_vertical(*args, direction = self.VERTICAL_UP, **kwargs)

    def route_vertical_down(self, *args, **kwargs):
        '''
            Routes vertically down
        '''
        return self.route_vertical(*args, direction = self.VERTICAL_DOWN, **kwargs)

    def route_vertical(self,
                       segment,
                       x_coordinate,
                       direction):
        '''
            Given a coordinate draw a route up from this point
            If it intersects with an existing route then it's a valid placement
            Otherwise it's not, and rollback
        '''

        if direction is self.VERTICAL_UP:
            join_direction = Segment.bottom_to_top
            next_element = lambda x: next(iter(x.above), None)
        elif direction is self.VERTICAL_DOWN:
            join_direction = Segment.top_to_bottom
            next_element = lambda x: next(iter(x.below), None)
        else:
            raise AllocatorError("Invalid vertical routing direction")

        route_segments = []
        curr_segment = segment
        # Only continue routing up while routable
        while curr_segment is not None and curr_segment.get_state() is SCPatch.NONE:
            self.debug_print(f"Routing on {curr_segment} {x_coordinate} {curr_segment.get_state()} {curr_segment.get_state() is SCPatch.NONE}")
            # Unallocated, prepare to route
            if curr_segment.width > 1:
                # Cleave a width 1 column
                confirm, segments = curr_segment.split(curr_segment.y_0, x_coordinate, curr_segment.height, 1)
                self.debug_print(f"Cloven Segments {segments}")
                if confirm is not None:
                    route = next((seg for seg in segments if seg.x_0 == x_coordinate), None)
                    if route is None:
                        return False, None
                else:
                    return False, None
                confirm(self.qcb.segments)
            else:
                route = curr_segment
            self.debug_print(f"Route: {route} {route.width}")

            # Check if this is a terminating condition
            joining_route = next((seg for seg
                                 in join_direction(route.left | route.right)
                                    if seg.get_state() is SCPatch.ROUTE), None)

            self.debug_print("Horizontal Joins: ", joining_route)
            self.debug_print(tuple((x, x.get_state()) for x in route.left | route.right))

            if joining_route is not None:
                # We've found the routing network
                if direction is self.VERTICAL_UP:
                    # Handle join in upwards direction
                    if joining_route.y_1 > route.y_1: # Route extends beyond this one
                        # Join extends below this segment
                        confirm, segments = route.split_bottom(1)
                        joining_segment = next((seg for seg in segments if seg.y_1 == route.y_1), None)
                    else:
                        # Join extends above this segment
                        confirm, segments = route.split_bottom(abs(joining_route.y_1 - route.y_1) + 1)
                        joining_segment = next((seg for seg in segments if seg.y_1 == route.y_1), None)
                else:
                    # Handle join in downwards direction
                    if joining_route.y_0 > route.y_0:
                        # Join extends above this segment
                        confirm, segments = route.split_top(abs(joining_route.y_0 - route.y_0) + 1)
                        joining_segment = next((seg for seg in segments if seg.y_0 == route.y_0), None)
                    else:
                        # Join extends below this segment
                        confirm, segments = route.split_top(1)
                        joining_segment = next((seg for seg in segments if seg.y_0 == route.y_0), None)
                self.debug_print(f"Joining to route {route}, {joining_segment}")
                confirm(self.qcb.segments)
                route_segments.append(joining_segment)
                self.debug_print(f"Vertical Route {route_segments}")
                return True, route_segments
            else:
                # If this is None then we have hit the top or the bottom of the QCB
                route_segments.append(route)
                curr_segment = next_element(route)# Width 1 so single element

        # Found an existing route
        if curr_segment is not None and curr_segment.get_state() is SCPatch.ROUTE:
            self.debug_print(f"Vertical Route {route_segments}")
            return True, route_segments

        # Found the top without a route
        # Or hit an extern or similar
        return False, None



###############################################

    def route_remainder(self):
        '''
        Final allocation step, set everything that remains as a local route
        This is because we cannot guarantee connectivity for these components
        '''
        self.place_local_segments(*self.get_free_segments())

    def get_free_segments(self):
        '''
            Gets the current free segments
        '''
        # TODO, discuss how to optimise this garbage
        curr_segment = min((seg for seg in self.qcb.segments if not seg.allocated), default=None)
        while curr_segment is not None:
            yield curr_segment
            curr_segment = min((
                    seg for seg in self.qcb.segments
                    if not seg.allocated and seg > curr_segment),
                    default=None)
        return

    def assert_reg_valid(self, segment):
        '''
            Checks that a register is valid
        '''
        return ((
                len(segment.above) > 0
                and all(seg.get_state() is SCPatch.ROUTE for seg in segment.above))
            or
                (
                len(segment.below) > 0
                and all(seg.seg_state() is SCPatch.ROUTE for seg in segment.below))
            )

    def assert_route_valid(self, segment):
        '''
            Checks that a route is valid
        '''
        return any(seg.get_state() is SCPatch.ROUTE for seg in segment.neighbours())

    def assert_extern_valid(self, segment):
        '''
            Checks that an extern is valid
        '''
        return (
                len(segment.below) > 0
                and all(seg.get_state() is SCPatch.ROUTE for seg in segment.below)
               )

    def assert_io_valid(self, segment):
        '''
            Checks that an io segment is valid
        '''
        return (
                len(segment.above) > 0
                and all(seg.get_state() is SCPatch.ROUTE for seg in segment.above)
               )

    #################
    # Merge operations
    #################

    def global_merge_tl(self):
        '''
            Merges all unallocated nodes top then left
        '''
        self.global_top_merge()
        self.global_left_merge()

    def global_merge_lt(self):
        '''
            Merges all unallocated nodes left then top
        '''
        self.global_left_merge()
        self.global_top_merge()

    def global_top_merge(self):
        '''
            Merges all unallocated nodes vertically
        '''
        offset = 0
        queue = list(self.get_free_segments())
        while offset < len(queue):
            confirm, _ = queue[-offset - 1].top_merge()
            confirm(self.qcb.segments)
            queue = list(self.get_free_segments())
            offset += 1

    def global_left_merge(self):
        '''
            Merges all unallocated nodes horiztonally
        '''
        offset = 0
        queue = list(self.get_free_segments())
        queue.sort(key=lambda s: (s.x_0, s.y_0))
        while offset < len(queue):
            confirm, _ = queue[-offset - 1].left_merge()
            confirm(self.qcb.segments)
            queue = list(self.get_free_segments())
            queue.sort(key=lambda s: (s.x_0, s.y_0))
            offset += 1

    def __tikz__(self):
        '''
            Tikz dispatch method
        '''
        return self.tikz_str
