from itertools import chain
from typing import *
import copy
import pdb
from surface_code_routing.qcb import Segment, SCPatch, QCB
from surface_code_routing.dag import DAG
import surface_code_routing.utils as utils 
from surface_code_routing.bind import AddrBind

class AllocatorError(Exception):
    pass

class Allocator:
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

    def __init__(self, qcb: QCB, *extern_templates, optimise=False, tikz_build=True, verbose=True, opt_space=False, opt_route=True):
        self.qcb = qcb
        self.qcb.allocator = self

        self.extern_templates = sorted(extern_templates, 
                                     key=lambda extern: (extern.width, extern.height),
                                     reverse=True)

        self.height = qcb.height
        self.width = qcb.width

        if opt_space and opt_route:
            raise Exception("Cannot optimise for both space and routes, these are mutually exclusive")
        self.opt_space = opt_space # Try to optimise space at the cost of routes
        self.opt_route = opt_route # Try to optimise routes at the cost of space
        
        self.io_width = len(qcb.io)
        self.reg_allocated = 0
        self.reg_quota = len(qcb.operations.internal_scope()) - len(qcb.operations.io())

        self.tikz_build = tikz_build
        self.tikz_str = ""
        self.verbose = verbose

        # optimise variables
        self.msfs = []
        self.n_channels = 1

        self.allocate()
#        if optimise:
#           self.optimise()
#        self.route_remainder()


    def debug_print(self, *args):
        return utils.debug_print(*args, debug=self.verbose)

    def build_tikz_str(self):
        if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()

    def allocate(self):
        for extern in self.extern_templates:
            self.global_left_merge()
            self.debug_print(f"Externs: {extern}")   
            invariant = self.extern_invariant(extern)
            self.build_tikz_str()
            if invariant is self.INVARIANT_FAILED:
                raise Exception("Not enough space for registers")

        while self.reg_allocated < self.reg_quota: 
            self.debug_print(f"Registers: {self.reg_allocated} / {self.reg_quota}")

            # Have to global merge before attempting to retrieve segment
            self.global_merge_tl()

            free_segment = next(iter(self.get_free_segments()), None)
            invariant = self.reg_invariant(free_segment)
            self.build_tikz_str()
            if invariant is self.INVARIANT_FAILED:
                raise Exception("Not enough space for registers")

    def extern_invariant(self, extern):
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
        if placed is not True:
            raise Exception(f"Could not allocate extern: {extern}, no valid placement")

    def reg_invariant(self, segment):
        self.debug_print(segment)

        invariant, regs, routes = self.alloc_reg(segment)
        
        self.debug_print(invariant, regs, routes, '\n')
        if invariant is not self.INVARIANT_FAILED:
            if regs is None and routes is None:
                return self.INVARIANT_FAILED
            if regs is not None:
                self.place_reg_segments(*regs)
            if routes is not None:
                self.place_route_segments(*routes)
        else:
            self.place_route_segments((segment, ))
        return invariant

    
    def alloc_extern(self, extern, segment):
        # Check extern fits
        # TODO, grow this region
        if extern.height > segment.height or extern.width > segment.width:
            self.debug_print(f"Segment {segment} was too small to contain {extern}")
            return self.INVARIANT_FAILED, None, None

        confirm, segments = segment.split_top_left(extern.height, extern.width) 
        confirm(self.qcb.segments)
        extern_segment = next((seg for seg in segments if seg.x_0 == segment.x_0 and seg.y_0 == segment.y_0), None)


        if ((extern_segment.x_0 == 0 and extern_segment.y_0 == 0) # First allocation, just place below
            or (any(seg.get_state() is SCPatch.ROUTE for seg in extern_segment.below) and # Already routable from below 
                all(seg.get_state() in self.ROUTEABLE for seg in extern_segment.below))
            ):

            self.debug_print("First allocation")
            success, extern, below_route = self.route_below(extern_segment)
            if success is not True:
                return self.INVARIANT_FAILED, None, None
            else:
                return self.EXTERN_INVARIANT_BELOW, extern[0], below_route

        success, extern, below_route = self.route_below(extern_segment)
        if not success:
            # Cannot route below
            return self.INVARIANT_FAILED, None, None

        # Check if already routed
        # should be single right element as the route has height 1
        left_probe = next(iter(Segment.leftmost_segment(below_route).left), None)

        if left_probe is not None and left_probe.get_state() is SCPatch.ROUTE: 
            # Connected to routing net from left
            # TODO check that IO is routed
            return self.EXTERN_INVARIANT_LEFT, extern_segment, below_route 

        # Need to do a drop, start with a right drop up
        success, _, routes = self.route_right_drop_up(extern_segment)
        if success is not self.INVARIANT_FAILED:
            return success, extern_segment, routes + below_route
        self.debug_print(f"Right drop failed")

        # Try a left drop up
        success, _, routes = self.route_left_drop_up(extern_segment)
        if success is not self.INVARIANT_FAILED:
            return success, extern_segment, routes + below_route
        self.debug_print(f"Left drop failed")

        # Attempt a route down

        # Shift segment and route on the left

        return self.INVARIANT_FAILED, None, None


    def place_segment_of_type(self, seg_type, *segments):
        for segment in segments:
            segment.set_state(seg_type)
            segment.allocate()

    def place_route_segments(self, *segments):
        self.place_segment_of_type(SCPatch.ROUTE, *segments)

    def place_reg_segments(self, *segments):
        self.place_segment_of_type(SCPatch.REG, *segments)
        for segment in segments:
            self.reg_allocated += segment.height * segment.width

    def place_extern_segment(self, segment, extern):
        segment.state = SCPatch(extern)
        segment.allocate()

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
                return success, (segment, ), routes + [below_right_route]
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
        below_probe = segment.leftmost_segment(segment.below)
        # Probe extends beyond range of block
        if below_probe.x_1 > segment.x_1:
            below_left_probe = below_probe
        else:
            below_left_probe = Segment.topmost_segment(below_probe.left)

        below_left_routeable = (
                (below_left_probe != None) 
                and (below_left_probe.get_state() in SCPatch.ROUTEABLE)
                )

        # Trying to find a viable left route
        if below_left_routeable:
            # Routing is possible, create the corner
            confirm, segments = below_left_routeable.split(segment.x_0 - 1, segment.y_1 + 1, 1, 1)
            confirm(self.qcb.segments)
            below_left_route = next(seg for seg in segments if (
                (seg.x_0 == segment.x_1 + 1)
                and (seg.y_0 == segment.y_1 + 1)))

            # Try to route up the left hand side
            success, routes = segment.route_edge(segment.left)
            if success is True:
                return success, segment, routes + [below_left_route]
        return self.INVARIANT_FAILED, None, None


    def route_extern_tight_below(extern_segment):
        # Find all nodes below that need routing
        # This function is not called unless all nodes below are routes or unallocated

        # Above is the top, no need to route up
        route = list()
        if (extern_segment.y_0 == 0):
            # Top left corner is the first placement so we don't need to worry about anything
            self.debug_print("Top Row")
            if extern.segment.x_0 < 0:
                # Instead this means it's not the first placement
                # Hence there should be something to the left
                
                # Try left and above
                left_drop, route = self.route_extern_left_drop_up(extern_segment)
                self.debug_print("Trying Left Drop") 
                if left_drop is False:
                    # Try left and below
                    drop_down_left, route = self.route_extern_left_drop_down(extern_segment) 
                    self.debug_print("Trying Drop Down Left")
                    if drop_down_left is False:
                        # Could not connect to any routes
                        return self.INVARIANT_FAILED, None, None

        else:
            # We're not on top and hence are concerned with the state of the routing network
            right_drop, route = self.route_extern_right_drop(extern_segment)

            if right_drop is False:
                # Can't connect on the right, try the left
                left_drop, route = self.route_extern_left_drop(extern_segment)
             
                if left_drop is False:
                    # Cannot connect from left up, try dropping down
                    drop_down_left, route = self.route_extern_drop_down_left(extern_segment) 

                    if drop_down_left is False:
                        # Cannot connect to the routing network from here
                        return self.INVARIANT_FAILED, None, None

        # Having established that we can connect to the routing network
        # We can now route below our extern 
        confirm(self.qcb.segments)
        for route_element in (x for x in extern_segment.below if x.get_state() is not SCPatch.ROUTE):
            confirm, route = extern_segment.split_contains_below(route_element)
            if confirm is not None:
                confirm(self.qcb.segments)
            route.append(route)

        # If you can't route from below with a tight fit then you can't route this block 
        return self.INVARIANT_FAILED, None, None



    def alloc_reg(self, segment):
        '''
            Given the current free segment, try to allocate a register
            If this function does not return INVARIANT_FAILED then register allocation is feasible 
        '''
        self.debug_print("Attempting to allocate Register")
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
            return self.REG_INVARIANT_ABOVE, regs, routes

        ####  
        # Segment cannot be routed from above
        # Split to create a probe on the left
        #
        #       ?%%%%%%%%%
        #       @---------
        #        
        confirm(self.qcb.segments)
        confirm, segments = reg_segment.split_top_left(1, 1)
        original_segment = reg_segment
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
            bottom_probe = left_probe.rightmost_segment(left_probe.below)
            if (bottom_probe is not None) and (bottom_probe.get_state() is SCPatch.ROUTE):
                bottom_probe_routable = True
            else:
                bottom_probe_routable = False
        
        self.debug_print(f"Top Probe {top_probe} : {top_probe_routable}\nLeft Probe {left_probe} : {left_probe_routable}\nBottom Probe {bottom_probe} : {bottom_probe_routable}")

        if left_probe_routable: 
            #      *%%%%%%%%%%
            #      +@---------
            #      ?
            confirm(self.qcb.segments)
            regs, routes = self.route_reg_from_left(left_probe, probe_segment, reg_segment)
            return self.REG_INVARIANT_ABOVE_LEFT, regs, routes
        
        if top_probe_routable:
            # Left is not routeable, check above
            #       ?%%%%%%%%%
            #      %@---------
            confirm(self.qcb.segments)
            regs, routes = self.route_reg_from_top_left(probe_segment, reg_segment) 
            return self.REG_INVARIANT_ABOVE_LEFT, regs, routes

        # All else failed, attempt to drop left
        success, regs, routes = self.route_drop_left(original_segment)
        if success:
            return self.REG_INVARIANT_DROP, regs, routes

        # Could not find a routing strategy that doesn't violate the invariant
        # Fail
        return self.INVARIANT_FAILED, None, None
  
    def route_single_reg(self, segment):
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

            return self.ROUTE_BLOCK, None, (segment, )

#            else:
#                # Below is bounded from above by the current segment
#                self.debug_print('Below Left', below_left, below_left.get_state())
#                if below_left is not None and below_left.get_state() in self.ROUTEABLE:
#                    routes = []
#                    if below_left.get_state() is SCPatch.ROUTE:
#                    if below_left.get_state() is not SCPatch.ROUTE:
#                        confirm, segments = below_left.split(segment.y_1 + 1, segment.x_0 - 1, 1, 1)
#                        below_left_route = next((seg for seg in segments if seg.x_0 == segment.x_0 - 1 and seg.y_0 == segment.y_0 + 1), None)
#                        confirm(self.qcb.segments)
#                        routes.append(below_left_route)
#                    if below.get_state() is not SCPatch.ROUTE:
#                        # Construct a routing channel
#                        confirm, segments = below.split(segment.y_1 + 1, segment.x_0, 1, 1)
#                        below_route = next((seg for seg in segments if seg.x_0 == segment.x_0 - 1 and seg.y_0 == segment.y_0 + 1), None)
#                        confirm(self.qcb.segments)
#                        routes.append(below_route)
#
            return self.REG_INVARIANT_ABOVE_LEFT, (segment, ), routes

        return self.ROUTE_BLOCK, None, (segment, )


    def route_reg_from_left(self, left_probe, probe, segment): 
         if ((left_probe.y_1 > probe_segment.y_1) # Two high, this implies a route below
                or (left_probe.rightmost_segment(left_probe.below).get_state() is SCPatch.ROUTE)
                ):
                #      **%%%%%%%%%
                #      +@---------
                #      +
                segment, confirm = probe_segment.horizontal_merge(reg_segment)
                ###
                #      **%%%%%%%%%
                #      +----------
                #      +++++++++++
                success, reg_segments, route_segments = self.route_below(segment) 
                return reg_segments, route_segments

    def route_reg_from_top_left(self, probe, segment):
        # Above of probe is routable
        #       +%%%%%%%%%
        #      %@---------
        print(probe, segment)
        probe.allocate() 
        segment.allocate()
        success, probe, route_below_probe = self.route_below(probe) 
        success, regs, route_below = self.route_below(segment)
        #       +%%%%%%%%%
        #      %+---------
        #       ++++++++++
        return regs, (*probe, *route_below_probe, *route_below)


    def route_reg_from_above(self, segment):
        ###
        # Routeable from above
        #
        # ++++++++ 
        # --------
        #
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
                # The routable left edge may either extend past the current y coordinate
                if left_element.y_1 > reg_segment.y_1:
                    self.debug_print("")
                    return self.REG_INVARIANT_ABOVE, (reg_segment, ), None 

                # Routable left edge is split vertically
                # Two block case
                else:
                    probe_existing_route = Segment.rightmost_segment(left_element.below)
                    if probe_existing_route is not None:
                        if probe_existing_route.get_state() in self.ROUTEABLE:
                            return self.REG_INVARIANT_ABOVE, (reg_segment, ), None 
            # Both tests failed, fallback to routing through the probe
            return self.INVARIANT_FAILED, None, None 
        else:
        # Can't route from right, have to use route through the probe
        #       *++++++++++
        #       %@---------
        #       %
            confirm(self.qcb.segments)
            return self.REG_INVARIANT_ABOVE, (reg_segment,), (potential_route_segment,) 
   
    def route_drop_left(self, segment):

        # Can't route from right, have to use route through the probe
        #        %%%%%%%%%%
        #       %@---------
        #       %+
        #       ++
        probe = Segment.leftmost_segment(segment.below)
        print(f"Drop Left {probe}, {segment}")
        success, routes = self.route_vertical_down(probe, segment.x_0)
        if success is True:
            success, regs, route_below = self.route_below(segment, exclude={routes[0]})
            return self.REG_INVARIANT_DROP, (segment, ), routes + route_below

        # Cannot create routing channel under the current segment
        return self.INVARIANT_FAILED, None, None 

    def route_below(self, segment, fallback_split=False, fallback_end_cap=False, exclude=None):
        #
        # ------------
        # ++++++++++++
        if exclude is None:
            exclude = set()

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
                route_length = min(potential_route.width, segment.x_1 - potential_route.x_0 + 1)
                self.debug_print(f"Splitting for route: {potential_route} {route_length}")
                confirm, segments = potential_route.split_top_left(1, route_length)
                confirm(self.qcb.segments)
                potential_route = next((seg for seg in segments if seg.y_0 == potential_route.y_0), None)
                routing_elements.append(potential_route)

            # If it's in routable but is not a route, then skip it
        self.debug_print("Sucessfully routed below")
        return True, (segment, ), routing_elements 
    
    def route_vertical_up(self, *args, **kwargs):
        return self.route_vertical(*args, direction = self.VERTICAL_UP, **kwargs)

    def route_vertical_down(self, *args, **kwargs):
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
            raise Exception("Invalid vertical routing direction")

        route_segments = []
        curr_segment = segment
        while curr_segment is not None:
            print(f"Dropping on {curr_segment} {curr_segment.get_state()} {curr_segment.get_state() is SCPatch.NONE}")
            # Unallocated, prepare to route
            if curr_segment.get_state() is SCPatch.NONE:
                # Cleave a width 1 column
                confirm, segments = curr_segment.split(curr_segment.y_0, x_coordinate, curr_segment.height, 1)
                print(f"Cloven Segments {segments}")
                if confirm is not None:
                    route = next((seg for seg in segments if seg.x_0 == x_coordinate), None)
                    if route is not None:
                        route_segments.append(route)
                    else:
                        return False, None
                else:
                    return False, None
                confirm(self.qcb.segments)
                print(f"Route: {route} {route.width}")
          
                # Check if this is a terminating condition
                joining_route = next((seg for seg 
                                     in join_direction(route.left | route.right)
                                        if seg.get_state() is SCPatch.ROUTE), None)

                print("Join: ", joining_route)
                print(tuple((x, x.get_state()) for x in route.left | route.right))

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
                            confirm, segments = route.split_bottom(joining_route.y_1 - route.y_1 + 1)
                            joining_segment = next((seg for seg in segments if seg.y_1 == route.y_1), None)
                    else:
                        # Handle join in downwards direction
                        if joining_route.y_0 > route.y_0:
                            # Join extends above this segment
                            confirm, segments = route.split_top(joining_route.y_0 - route.y_0 + 1)
                            joining_segment = next((seg for seg in segments if seg.y_0 == route.y_0), None)
                        else: 
                            # Join extends below this segment
                            confirm, segments = route.split_top(1)
                            joining_segment = next((seg for seg in segments if seg.y_0 == route.y_0), None)
                    print(f"JOIN TO ROUTE {route}, {joining_segment}")
                    confirm(self.qcb.segments)
                    route_segments.append(joining_segment)
                    return True, route_segments 
                else:
                    # If this is None then we have hit the top or the bottom of the QCB
                    route_segments.append(route)
                    curr_segment = next_element(route)# Width 1 so single element

            # Found an existing route
            elif curr_segment.get_state() is SCPatch.ROUTE:
                return True, route_segments 

            # Was either another extern, a register, halt
            else:
                return False, None
        # Found the top without a route
        return False, None


###############################################33

    def reg_to_route(self, keep: Set[Tuple[int, int]]):
        
        long_reg = next((s for s in self.qcb.segments 
                        if s.state.state == SCPatch.REG
                        and s.width > 1), None)
        while long_reg:
            long_reg.allocated = False
            (reg, right), confirm = long_reg.alloc(1, 1)
            confirm(self.qcb.segments)

            reg.state = SCPatch(SCPatch.REG)
            right.allocated = True
            right.state = SCPatch(SCPatch.REG)

            long_reg = next((s for s in self.qcb.segments 
                        if s.state.state == SCPatch.REG
                        and s.width > 1), None)

        for seg in self.qcb.segments:
            if seg.state.state == SCPatch.REG and (seg.x_0, seg.y_0) not in keep:
                seg.state = SCPatch(SCPatch.ROUTE)
                seg.debug_name = "r2r"

    def try_opt_channel(self) -> bool:
        
        self.global_merge_lt()

        longest_reg = max((s 
                           for s in self.qcb.segments 
                           if s.state.state == SCPatch.REG
                           and s.y_0 != 0
                           and s.y_1 != self.height), 
                           key=lambda s:s.width, 
                           default=None)
        
        if not longest_reg or longest_reg.width == 1:
            return False

        split_x = (longest_reg.x_0 + longest_reg.x_1 + 1) // 2

        affected_regs = [s 
                        for s in self.qcb.segments 
                        if s.state.state == SCPatch.REG 
                        and s.x_0 <= split_x <= s.x_1 
                        and s.width > 1 
                        and s.y_0 != 0
                        and s.y_1 != self.height - 1]

        if len(affected_regs) == 0:
            return False # Noop is a failure

        new_req = self.reg_allocated - self.reg_quota - len(affected_regs)
        while new_req < 0:
            try:
                self.place_reg()
            except AllocatorError as e:
                return False
            new_req = self.reg_allocated - self.reg_quota - len(affected_regs)

        for r in affected_regs:
            r.allocated = False
            (route, *parts), confirm = r.split(r.y_0, split_x, 1, 1)
            confirm(self.qcb.segments)

            route.state = SCPatch(SCPatch.ROUTE)
            route.allocated = True

            for p in parts:
                p.allocated = True
                p.state = SCPatch(SCPatch.REG)

            self.reg_allocated -= 1

        return True

    
    def try_opt_new_msf(self, new_msf) -> bool:
        try:
            fringe = (float('-inf'), float('-inf'))

            success, position = self.try_place_msf(new_msf, fringe)
            while not success:
                self.global_top_merge()
                self.global_left_merge()
                fringe = position
                success, position = self.try_place_msf(new_msf, fringe)

        except AllocatorError:
            return False
        return True


    def try_optimise(self) -> bool:
        '''
            Attempt an optimisation
        '''
        dag = self.qcb.operations
        if not self.get_free_segments():
            return False
        
        def heuristic(new_msf):
            if new_msf:
                return (new_msf, dag.compile(self.n_channels, *self.msfs, new_msf)[0])
            else:
                return (new_msf, dag.compile(self.n_channels + 1, *self.msfs)[0])

        options = [new_msf.instantiate() for new_msf in self.extern_templates]
        options.append(None)
        options = sorted(map(heuristic, options), key=lambda o:o[1])

        curr_score = dag.compile(self.n_channels, *self.msfs)[0]

        options = [o[0] for o in options if o[1] < curr_score]

        for new_msf in options:
            if not new_msf and self.try_opt_channel():
                self.n_channels += 1
                return True
            elif new_msf and self.try_opt_new_msf(new_msf):
                self.msfs.append(new_msf)
                return True
        return False

    def optimise(self):
        # Attempts to allocate either an extern or a new channel
        dag = self.qcb.operations
        while self.try_optimise():
            if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()
            self.global_merge_tl()

        # Splits remaining blocks
        while self.try_opt_channel():
            self.n_channels += 1
            if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()
        
        
        # Set final compilation in the QCB
        n_layers, compiled_layers = dag.compile(self.n_channels, *self.msfs)
        #self.qcb.compiled_layers = compiled_layers

        self.global_top_merge()
        self.global_left_merge()

        free = self.get_free_segments()
        if free:
            last = next((s for s in free 
                         if s.x_1 == self.width - 1 
                         and s.y_1 == self.height - 1), None)
            if last and last.height >= 2:
                (bottom_block, *_), confirm = last.split(last.y_1 - 1, last.x_0, 2,  last.width)
                confirm(self.qcb.segments)
                
                (route, reg), confirm = bottom_block.alloc(1, bottom_block.width)
                confirm(self.qcb.segments)
                
                route.state = SCPatch(SCPatch.ROUTE)
                reg.state = SCPatch(SCPatch.REG) 
                reg.allocated = True

        if self.tikz_build:
            self.tikz_str += self.qcb.__tikz__()


        self.global_merge_tl()
        # Add routing to flood fill 
        for seg in self.get_free_segments():
            if not all(left_node.state.state == SCPatch.ROUTE for left_node in seg.left):
                (left, *main), confirm = seg.alloc(seg.height, 1)
                confirm(self.qcb.segments)
                left.state = SCPatch(SCPatch.ROUTE)
        
        if self.tikz_build:
            self.tikz_str += self.qcb.__tikz__()

        # TODO add reg before flood
        while self.get_free_segments():
            self.global_merge_tl()
            regs = self.place_reg()
            for r in regs:
                # maybe green red green red?

                while r.width >= 3:
                    r.allocated = False

                    (l, r), confirm = r.alloc(1, 1)
                    confirm(self.qcb.segments)
                    l.state = SCPatch(SCPatch.REG)

                    (l, r), confirm = r.alloc(1, 1)
                    confirm(self.qcb.segments)
                    l.state = SCPatch(SCPatch.ROUTE)

                if r.width == 2:
                    r.allocated = False

                    (l, r), confirm = r.alloc(1, 1)
                    confirm(self.qcb.segments)
                    l.state = SCPatch(SCPatch.REG)

                    r.allocated = True
                    r.state = SCPatch(SCPatch.ROUTE)
                else:
                    r.allocated = True
                    r.state = SCPatch(SCPatch.REG)
        if self.tikz_build:
            self.tikz_str += self.qcb.__tikz__()

    def route_remainder(self):
        '''
        Final allocation step, set everything that remains as a route
        '''
        for seg in self.qcb.segments:
            if seg.get_state() is SCPatch.NONE:
                seg.state = SCPatch(SCPatch.LOCAL_ROUTE)

    def place_io(self):
        if self.io_width == 0:
            return

        segs, confirm = self.get_free_segments()[0].split(self.height - 1, 0, 1,  self.io_width)
        if not confirm:
            raise AllocatorError("IO placement failed")

        confirm(self.qcb.segments)

        io, *main = segs
        io.allocated = True
        io.state = SCPatch(SCPatch.IO)
        
        above_block = next(iter(io.above))
        (route, *_), confirm = above_block.split(self.height - 2, 0, 1, self.io_width)
        route.allocated = True
        route.state = SCPatch(SCPatch.ROUTE)
        confirm(self.qcb.segments)

        if io.width < self.width:
            self.global_top_merge()
            self.global_left_merge()
            right_block = next(iter(io.right))
            (route, *_), confirm = right_block.alloc(2, 1)
            route.state = SCPatch(SCPatch.ROUTE)
            confirm(self.qcb.segments)

    def get_free_segments(self):
        # Todo, discuss how to optimise this garbage
        curr_segment = min((seg for seg in self.qcb.segments if not seg.allocated), default=None)
        while curr_segment is not None:
            yield curr_segment
            curr_segment = min((
                    seg for seg in self.qcb.segments 
                    if not seg.allocated and seg > curr_segment),
                    default=None)
        return

    def try_place_msf(self, msf, fringe: Tuple[int, int]) \
            -> Tuple[bool, Tuple[int, int]]:
        
        first = next((s for s in self.get_free_segments() if s.y_position() > fringe), None)
        if not first:
            raise AllocatorError(f"Extern placement failed: all blocks exhausted for {msf}")
        
        # Merge sequence
        segs, confirm = first.top_merge()
        confirm(self.qcb.segments)
        first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]
        segs, confirm = first.left_merge()
        confirm(self.qcb.segments)
        first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]

        # Check top drop
        if first.x_0 == 0 and first.y_0 != 0: # Connect to msf routing net in row above
            bounds = (msf.height + 1, msf.width + 1)
        else:
            bounds = (msf.height + 1, msf.width) # No connection needed

        # Attempt 1
        segs, confirm = first.alloc(*bounds)

        if not confirm:
            # Try additional merge
            segs, confirm = first.top_merge()
            confirm(self.qcb.segments)
            first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]

            # Attempt 2
            segs, confirm = first.alloc(*bounds)
            if not confirm:
                return False, first.y_position() # Expand testing fringe
        
        confirm(self.qcb.segments)

        msf_block, *others = segs
        msf_block.allocated = False

        # Do right drop for leftmost MSF (connection to routing net in row above)
#        if msf_block.x_0 == 0 and msf_block.y_0 != 0:
#            (msf_block, right_drop), confirm = msf_block.alloc(msf.height + 1, msf.width)
#            confirm(self.qcb.segments)
#
#            right_drop.allocated = True
#            right_drop.state = SCPatch(SCPatch.ROUTE)
#
#            msf_block.allocated = False
#
        if msf_block.x_0 == 0 and msf_block.y_0 != 0:
            (left_drop, msf_block), confirm = msf_block.alloc(msf.height + 1, 1)
            confirm(self.qcb.segments)

            left_drop.allocated = True
            left_drop.state = SCPatch(SCPatch.ROUTE)

            msf_block.allocated = False


        # Add route layer below
        (msf_seg, route_seg), confirm = msf_block.alloc(msf.height, msf.width)
        confirm(self.qcb.segments)

        msf_seg.allocated = True
        msf_seg.state = SCPatch(msf)

        route_seg.allocated = True
        route_seg.state = SCPatch(SCPatch.ROUTE)

        # Check if drop required for routing segment
        if first.x_0 != 0 and not self.check_reachable(route_seg):
            # Drop either on left or curr block

            self.global_top_merge()
            left_seg = next(iter(route_seg.left)) # Must exist since route_seg.x_0 != 0
            if left_seg.allocated: 
                # must be MSF block, drop below route seg
                left_route = next(iter(left_seg.below))

                drop_block = next(iter(route_seg.below & left_route.right))
                drop_height = left_route.y_1 - route_seg.y_1

                segs, confirm = drop_block.alloc(drop_height, 1)
                confirm(self.qcb.segments)

                drop_seg, *others = segs
                drop_seg.state = SCPatch(SCPatch.ROUTE)
                drop_seg.allocated = True
            else:
                # Drop to left of route seg
                left_route = next(s for s in left_seg.above 
                                  if s.state.state == SCPatch.ROUTE
                                  and s.x_1 >= route_seg.x_0 - 1)

                drop_block = left_seg
                drop_height = route_seg.y_1 - left_route.y_1
                
                segs, confirm = drop_block.split(left_route.y_1 + 1, route_seg.x_0 - 1, drop_height, 1)
                confirm(self.qcb.segments)

                drop_seg, *others = segs
                drop_seg.state = SCPatch(SCPatch.ROUTE)
                drop_seg.allocated = True
                

        return True, msf_seg.y_position()



    def place_msf(self, msf):
        fringe = (float('-inf'), float('-inf'))

        success, position = self.try_place_msf(msf, fringe)
        while not success:
            fringe = position
            success, position = self.try_place_msf(msf, fringe)
    
    def route_to_io(self):
        if len(self.qcb.io) == 0:
            return
        
        # Find bottommost route segment connected to left edge of board
        bottom_route = max((s for s in self.qcb.segments 
                           if s.state.state == SCPatch.ROUTE
                           and s.x_0 == 0
                           and s.y_0 != self.height - 2
                           ), 
                           key = Segment.y_position, default=None)
        
        if bottom_route is None:
            return
        

        # Always valid because we perform a global top merge before
        bottom_free = next(s for s in bottom_route.below if s.x_0 == 0)
        self.debug_print(bottom_free)
        if not bottom_free.get_state() == SCPatch.IO and not bottom_free.get_state() == SCPatch.ROUTE :
            segs, confirm = bottom_free.alloc(self.height - bottom_route.y_1 - 3, 1)
            if not confirm:
                raise AllocatorError("Could not route routing layer to IO")
            
            confirm(self.qcb.segments)

            route_seg, *_ = segs
            route_seg.state = SCPatch(SCPatch.ROUTE)

    def place_reg_top(self, seg):
        out = []

        left_route = next((s for s in seg.left if s.y_0 == 0), None)
        if not left_route:
            # No MSFS: make dummy segment
            left_route = Segment(-1, self.height-3, -1, self.height-3)
        elif left_route.state.state == SCPatch.EXTERN:
            left_route = next(iter(left_route.below))


        (reg, seg), confirm = seg.alloc(1, seg.width)
        confirm(self.qcb.segments)
        reg.state = SCPatch(SCPatch.REG)
        out.append(reg)
        self.reg_allocated += reg.width

        (route, *_), confirm = seg.alloc(1, seg.width)
        confirm(self.qcb.segments)
        route.state = SCPatch(SCPatch.ROUTE)

        if route.y_0 < left_route.y_0:
            # self.global_top_merge()
            # self.global_left_merge()
            seg = next(iter(route.below))

            (drop, *_), confirm = seg.alloc(left_route.y_0 - route.y_0, 1)
            confirm(self.qcb.segments)
            drop.state = SCPatch(SCPatch.ROUTE)
        
        return out

    def check_reachable(self, seg):
        return any(s 
               for s in set.union(*seg.edges().values()) 
               if s.state.state == SCPatch.ROUTE)

    def check_reg_valid(self, seg):
        return ((seg.above and all(s.state.state == SCPatch.ROUTE for s in seg.above)) or 
                (seg.below and all(s.state.state == SCPatch.ROUTE for s in seg.below)))

    def check_free_reachable(self, seg):
        (row, *_), confirm = seg.alloc(1, seg.width)
        return self.check_reachable(row)
    
    def place_reg_top_routable(self, seg):
        out = []

        (reg, *_), confirm = seg.alloc(1, seg.width)
        confirm(self.qcb.segments)
        reg.state = SCPatch(SCPatch.REG)
        out.append(reg)
        self.reg_allocated += reg.width
        self.global_left_merge()

        # Find the next unallocated segment
        below_seg = next(iter(s for s in reg.below if not s.allocated), None)
        if not below_seg:
            return out

        if not self.check_free_reachable(below_seg):
            if below_seg.width == 1 and self.check_reachable(below_seg):
                (reg, *route), confirm = below_seg.alloc(1, 1)
                out.append(reg)
                confirm(self.qcb.segments)
                reg.state = SCPatch(SCPatch.REG)
                self.reg_allocated += reg.width
                if route:
                    route[0].state = SCPatch(SCPatch.ROUTE)
                    route[0].allocated = True
                return out
            if reg.width > 1:
                # raise Exception("test")

                reg.allocated = False
                out.remove(reg)
                (single, reg), confirm = reg.alloc(1, 1)
                confirm(self.qcb.segments)
                single.state = SCPatch(SCPatch.ROUTE)
                single.debug_name = '(280)'
                reg.state = SCPatch(SCPatch.REG)
                out.append(reg)
                reg.allocated = True
                self.reg_allocated -= 1
            else:
                below_seg.allocated = True
                below_seg.debug_name = "Temp fixs"

            assert self.check_free_reachable(below_seg)

        return out

    def place_reg_isolated(self, seg):
        out = []

        self.global_left_merge()
        seg = self.get_free_segments()[0]

        # Abandon if seg width is 1
        if seg.width == 1:
            seg.allocated = True
            seg.state = SCPatch(SCPatch.ROUTE)
            return out
        
        (reg, *_), confirm = seg.alloc(1, 1)
        confirm(self.qcb.segments)
        reg.state = SCPatch(SCPatch.REG)
        out.append(reg)

        if not self.check_reachable(reg):  
            below_seg = next(iter(reg.below))
            assert self.check_reachable(below_seg)
            assert not below_seg.allocated

            below_seg.allocated = True
            below_seg.state = SCPatch(SCPatch.ROUTE)

        return out


    def place_reg_route_below(self, seg):
        out = []

        # First check left edge
        left_edge = next(iter(s 
                                for s in seg.left 
                                if s.y_0 <= seg.y_0 + 1 <= s.y_1
                                and s.state.state == SCPatch.ROUTE), None)
        right_edge = next(iter(s 
                            for s in seg.right 
                            if s.y_0 <= seg.y_0 + 1 <= s.y_1
                            and s.state.state == SCPatch.ROUTE), None)

        self.debug_print(seg, left_edge, right_edge)
        if left_edge or right_edge:
            # Don't need drop
            (reg, seg), confirm = seg.alloc(1, seg.width)
            confirm(self.qcb.segments)
            reg.state = SCPatch(SCPatch.REG)
            out.append(reg)
            self.reg_allocated += reg.width
        else:
            # Need a center drop
            drop_x = min((s.x_0 
                        for s in seg.above 
                        if s.state.state == SCPatch.ROUTE), default=None)
            self.debug_print(drop_x)   
            if drop_x is None:
                left_edge = next(iter(s 
                        for s in seg.left 
                        if s.y_0 <= seg.y_0 <= s.y_1
                        and s.state.state == SCPatch.ROUTE), None)
                right_edge = next(iter(s 
                                    for s in seg.right 
                                    if s.y_0 <= seg.y_0 <= s.y_1
                                    and s.state.state == SCPatch.ROUTE), None)
                if left_edge:
                    drop_x = seg.x_0
                elif right_edge:
                    drop_x = seg.x_1
                else:
                    return out + self.place_reg_isolated(seg)
             
            drop_x = max(drop_x, seg.x_0)
            (row, seg), confirm = seg.alloc(1, seg.width)
            confirm(self.qcb.segments)
            self.debug_print(row, seg)

            row.allocated = False
            (drop, *regs), confirm = row.split(row.y_0, drop_x, 1, 1)
            confirm(self.qcb.segments)
            self.debug_print(drop)

            drop.allocated = True
            drop.state = SCPatch(SCPatch.ROUTE)

            for r in regs:
                r.allocated = True
                r.state = SCPatch(SCPatch.REG)
                out.append(r)
                self.reg_allocated += r.width

        (route, *_), confirm = seg.alloc(1, seg.width)
        confirm(self.qcb.segments)
        route.state = SCPatch(SCPatch.ROUTE)
        return out


    def place_reg(self) -> List[Segment]:
        seg = next(iter(self.get_free_segments()), None)
        if not seg:
            raise AllocatorError('No free space for registers left')

        if seg.y_0 == 0:
            return self.place_reg_top(seg)
       
        self.debug_print([(s, s.state.state) for s in seg.above])

        if all(s.state.state == SCPatch.ROUTE for s in seg.above):
            segs = self.place_reg_top_routable(seg)
            self.debug_print("Placed Top", segs)
            return segs
        elif seg.height >= 2:
            return self.place_reg_route_below(seg)
        
        self.global_top_merge()
        seg = self.get_free_segments()[0]

        if all(s.state.state == SCPatch.ROUTE for s in seg.above):
            return self.place_reg_top_routable(seg)
        elif seg.height >= 2:
            return self.place_reg_route_below(seg)
        elif seg.below and all(s.state.state == SCPatch.ROUTE for s in seg.below):
            # We use this here because its the same case, but with no below_seg in top_routable
            return self.place_reg_top_routable(seg)
        else:            
            return self.place_reg_one_high(seg)

 

    def place_reg_one_high(self, seg):
        out = []
        fill_top_x = min((s for s in seg.above), key=lambda s: s.x_0, default=None)
        if not fill_top_x:
            # This is topmost block
            (block, *_), confirm = seg.alloc(1, 1)
            if self.check_reg_valid(block):
                confirm(self.qcb.segments)
                block.state = SCPatch(SCPatch.REG)
                out.append(block)
                self.reg_allocated += block.width
            elif self.check_reachable(block):
                confirm(self.qcb.segments)
                block.state = SCPatch(SCPatch.ROUTE)
            else:
                confirm(self.qcb.segments)
                block.debug_name = 'useless'
            return out
        
        fill_bottom_x = min((s for s in seg.below), key=lambda s: s.x_0, default=None)
        if fill_bottom_x and fill_bottom_x.state.state == SCPatch.ROUTE:
            fill_x = fill_top_x if fill_top_x.x_1 <= fill_bottom_x.x_1 else fill_bottom_x
        else:
            fill_x = fill_top_x

        split_x = min(fill_x.x_1, seg.x_1)
        
        (block, *_), confirm = seg.alloc(1, split_x - seg.x_0 + 1)
        if self.check_reg_valid(block):
            confirm(self.qcb.segments)
            block.state = SCPatch(SCPatch.REG)
            out.append(block)
            self.reg_allocated += block.width
        elif self.check_reachable(block):
            confirm(self.qcb.segments)
            block.state = SCPatch(SCPatch.ROUTE)
            block.debug_name = 'bail'
        else:
            confirm(self.qcb.segments)
            block.debug_name = 'useless'
        return out

    def allocate_old(self):
        '''
            Perform initial allocation
        '''
        self.place_io()
        if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()

        externs = self.extern_templates
        if len(externs) > 0:
            # self.place_first_extern(externs[0])
            self.place_msf(externs[0])
            self.msfs.append(externs[0])
            self.global_merge_lt()

            if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()

            for i, extern in enumerate(externs[1:]):
                self.place_msf(extern)
                self.msfs.append(extern)
                self.global_merge_lt()

                if self.tikz_build:
                    self.tikz_str += self.qcb.__tikz__()

            self.route_to_io()
            if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()

        self.global_merge_tl()
        if self.tikz_build:
            self.tikz_str += self.qcb.__tikz__()

        while self.reg_allocated < self.reg_quota:
            # If an IO exists, then our first block must be rouatable to it
            # If the IO has already been created by the externs then this isn't needed
            if self.reg_allocated == 0 and len(externs) == 0 and self.io_width > 0:
                self.place_reg()
                self.global_merge_tl()
                self.route_to_io()
                self.global_merge_tl()
            else:
                self.place_reg()
                self.global_merge_tl()

            if self.tikz_build:
                self.tikz_str += self.qcb.__tikz__()

    def global_merge_tl(self):
        self.global_top_merge()
        self.global_left_merge()

    def global_merge_lt(self):
        self.global_left_merge()
        self.global_top_merge()

    def global_top_merge(self):
        offset = 0
        curr_node = min(self.get_free_segments())
        queue = list(self.get_free_segments())
        while offset < len(queue):
            confirm, _ = queue[-offset - 1].top_merge()
            confirm(self.qcb.segments)
            queue = list(self.get_free_segments())
            offset += 1

    def global_left_merge(self):
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
        return self.tikz_str
