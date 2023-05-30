from qcb import Segment, SCPatch
from msf import MSF
from typing import *

class AllocatorError(Exception):
    pass


class QCB:
    def __init__(self, height, width, io_width, reg, *msfs_templates):
        # A list of segments comprising the qcb sorted by top left point
        self.segments: 'Set[Segment]' = {Segment(0, 0, width-1, height-1)}
        self.msfs = {i.symbol:i for i in msfs_templates}
        self.height = height
        self.width = width
        self.io_width = io_width
        self.reg_remaining = reg


    
    def place_io(self):
        segs, confirm = self.get_free_segments()[0].split(0, self.height - 1, self.io_width, 1)
        if not confirm:
            raise AllocatorError("IO placement failed")

        confirm(self.segments)

        io, *main = segs
        io.allocated = True
        io.state = SCPatch(SCPatch.IO)
        
        above_block = next(iter(io.above))
        (route, *_), confirm = above_block.split(0, self.height - 2, self.io_width, 1)
        route.allocated = True
        route.state = SCPatch(SCPatch.ROUTE)
        confirm(self.segments)


    def get_free_segments(self):
        return sorted((s for s in self.segments if not s.allocated), key=Segment.y_position)


    def place_first_msf(self, msf: MSF):
        # Merge sequence
        _, confirm = self.get_free_segments()[0].top_merge()
        confirm(self.segments)
        _, confirm = self.get_free_segments()[0].left_merge()
        confirm(self.segments)


        # Attempt 1
        segs, confirm = self.get_free_segments()[0].alloc(msf.width, msf.height + 1)
        if not confirm:
            # Try to merge again
            _, confirm = self.get_free_segments()[0].top_merge()
            confirm(self.segments)

            # Attempt 2
            segs, confirm = self.get_free_segments()[0].alloc(msf.width, msf.height + 1)
            print(self.get_free_segments()[0])
            print(msf.width, msf.height)
            if not confirm:
                raise AllocatorError("First MSF placement failed")
        
        confirm(self.segments)



        msf_block, *others = segs
        msf_block.allocated = False

        # Split block into MSF and routing
        (msf_seg, route_seg), confirm = msf_block.alloc(msf.width, msf.height)
        confirm(self.segments)

        msf_seg.allocated = True
        msf_seg.state = SCPatch(msf)
        route_seg.allocated = True
        route_seg.state = SCPatch(SCPatch.ROUTE)

    def try_place_msf(self, msf: MSF, fringe: Tuple[int, int]) \
            -> Tuple[bool, Tuple[int, int]]:
        
        first = next((s for s in self.get_free_segments() if s.y_position() > fringe), None)
        if not first:
            raise AllocatorError("MSF placement failed: all blocks exhausted")
        
        # Merge sequence
        segs, confirm = first.top_merge()
        confirm(self.segments)
        first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]
        segs, confirm = first.left_merge()
        confirm(self.segments)
        first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]

        # Check top drop
        if first.x_0 == 0:
            bounds = (msf.width + 1, msf.height + 1)
        else:
            bounds = (msf.width, msf.height + 1)



        # Attempt 1
        segs, confirm = first.alloc(*bounds)

        if not confirm:
            # Try additional merge
            # if (first.x_0, first.y_0, first.x_1, first.y_1) == (9, 3, 12, 5):
            #     raise AllocatorError("debug")
            segs, confirm = first.top_merge()
            confirm(self.segments)
            first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]

            # Attempt 2
            segs, confirm = first.alloc(*bounds)
            if not confirm:
                return False, first.y_position() # Expand testing fringe
        
        confirm(self.segments)



        msf_block, *others = segs
        msf_block.allocated = False

        # Split block into MSF and routing
        if msf_block.x_0 == 0:
            (msf_block, right_drop), confirm = msf_block.alloc(msf.width, msf.height + 1)
            confirm(self.segments)
            right_drop.allocated = True
            right_drop.state = SCPatch(SCPatch.ROUTE)
            msf_block.allocated = False


        (msf_seg, route_seg), confirm = msf_block.alloc(msf.width, msf.height)
        confirm(self.segments)

        msf_seg.allocated = True
        msf_seg.state = SCPatch(msf)
        route_seg.allocated = True
        route_seg.state = SCPatch(SCPatch.ROUTE)

        if first.x_0 != 0 and not next((
                s for s in set.union(*route_seg.edges().values()) 
                if s.state.state == SCPatch.ROUTE
            ), None):
            # Drop either on left or curr block

   
            left_seg = next(iter(route_seg.left))
            if left_seg.allocated: # must be MSF block
                left_route = next(iter(left_seg.below))
                drop_block = next(iter(route_seg.below & left_route.right))
                drop_height = left_route.y_1 - route_seg.y_1
                print(drop_height)

                segs, confirm = drop_block.alloc(1, drop_height)
                assert confirm is not None
                confirm(self.segments)

                drop_seg, *others = segs
                drop_seg.state = SCPatch(SCPatch.ROUTE)
                drop_seg.allocated = True
            else:
                left_route = next(s for s in left_seg.above 
                                  if s.state.state == SCPatch.ROUTE
                                  and s.x_1 == route_seg.x_0 - 1)

                drop_block = left_seg
                drop_height = route_seg.y_1 - left_route.y_1
                
                segs, confirm = drop_block.split(route_seg.x_0 - 1, left_route.y_1 + 1, 1, drop_height)
                assert confirm is not None
                confirm(self.segments)

                drop_seg, *others = segs
                drop_seg.state = SCPatch(SCPatch.ROUTE)
                drop_seg.allocated = True
                

        return True, msf_seg.y_position()


    def place_msf(self, msf: MSF):
        fringe = (float('-inf'), float('-inf'))

        success, position = self.try_place_msf(msf, fringe)
        while not success:
            fringe = position
            success, position = self.try_place_msf(msf, fringe)
    

    def route_to_io(self):
        bottom_route = max((s for s in self.segments 
                           if s.state.state == SCPatch.ROUTE
                           and s.x_0 == 0
                           and s.y_0 != self.height - 2
                           ), 
                           key = Segment.y_position)
        
        bottom_free = next(iter(bottom_route.below))
        if not bottom_free.state.state == SCPatch.IO:
            segs, confirm = bottom_free.alloc(1, self.height - bottom_route.y_1 - 3)
            if not confirm:
                raise AllocatorError("Could not route routing layer to IO")
            
            confirm(self.segments)

            route_seg, *_ = segs
            route_seg.state = SCPatch(SCPatch.ROUTE)


    def place_reg(self):
        seg = next(iter(self.get_free_segments()), None)
        if not seg:
            raise AllocatorError('No free space for registers left')
        
        if seg.y_0 == 0:
            # Topmost segment, treat specially
            # TODO fix
            seg.allocated = True
            seg.state.state = 'debug'
            return 
        
        # elif not all(s.state.state == SCPatch.ROUTE 
        #            for s in seg.left):
        #     # Drop left edge
        #     if seg.width == 1:
        #         # Can't drop
        #         # TODO check right edge?
        #         seg.allocated = True
        #         return
            
        #     (left_edge, seg), confirm = seg.alloc(1, seg.height)
        #     confirm(self.segments)
        #     left_edge.state = SCPatch(SCPatch.ROUTE)
        
        if all(s.state.state == SCPatch.ROUTE for s in seg.above):
            (reg, *_), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= reg.width
            return
        elif seg.height >= 2:
            
            # First check left edge
            left_edge = next(iter(s for s in seg.left if s.y_0 <= seg.y_0 + 1 <= s.y_1))
            if left_edge.state.state != SCPatch.ROUTE:
                if seg.width == 1:
                    seg.allocated = True
                    seg.state = SCPatch(SCPatch.ROUTE)
                    return

                (left_drop, *_), confirm = seg.alloc(1, 2)
                confirm(self.segments)
                left_drop.state = SCPatch(SCPatch.ROUTE)
                seg = next(iter(left_drop.right))

            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= reg.width

            (route, *_), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            route.state = SCPatch(SCPatch.ROUTE)
            return
        else:
            seg.state = SCPatch(SCPatch.ROUTE)
            seg.allocated = True
            return

        while seg.height > 3:
            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= seg.width

            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= seg.width

            (route, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            route.state = SCPatch(SCPatch.ROUTE)

        if seg.height == 3:
            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= seg.width

            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= seg.width

            (route,), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            route.state = SCPatch(SCPatch.ROUTE)
            seg.allocated = True
        elif seg.height == 2:
            pass # TODO check
            seg.allocated = True
        elif seg.height == 1:
            (reg,), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_remaining -= seg.width






    def allocate(self):
        self.place_io()


        msfs = list(self.msfs.values())

        self.place_first_msf(msfs[0])
        self.global_left_merge()
        self.global_top_merge()

        for i, msf in enumerate(msfs[1:]):
            self.place_msf(msf)
            self.global_left_merge()
            self.global_top_merge()

        self.route_to_io()

        self.global_top_merge()
        self.global_left_merge()

        while self.reg_remaining > 0:
            self.place_reg()
            self.global_top_merge()
            self.global_left_merge()
        
    def global_top_merge(self):
        offset = 0
        queue = self.get_free_segments()
        while offset < len(queue):
            _, confirm = queue[-offset-1].top_merge()
            confirm(self.segments)
            queue = self.get_free_segments()
            offset += 1

    def global_left_merge(self):
        offset = 0
        queue = self.get_free_segments()
        queue.sort(key=lambda s: (s.x_0, s.y_0))
        while offset < len(queue):
            _, confirm = queue[-offset-1].left_merge()
            confirm(self.segments)
            queue = self.get_free_segments()
            queue.sort(key=lambda s: (s.x_0, s.y_0))
            offset += 1



# class QCB():
#     def __init__(self, height, width, **msfs_templates):
#         self.msfs = {i.symbol:i for i in msfs_templates}
#         self.height = height
#         self.width = width
#         self.qcb = np.array([[SCPatch() for _ in range(width)] for _ in range(height)], SCPatch)

#         self.open_segments = np.array([[0, 0]])

#         self.factories = {}

#     def __getitem__(self, x, y):
#         return self.qcb[x][y]

#     def __repr__(self):
#         string = ''
#         lookups = {None:'_', "MSF":"@", "Routing":"~", "Data":"#"}
#         for i in range(self.height):
#             for j in range(self.width):
#                 block = self.qcb[i][j]
#                 string += lookups[block.state]
#             string += '\n'
#         return string

#     def build(self, dag):

#         allocated_segments = []
#         unallocated_segments = [Segment(0, 0, self.width, self.height)]

#         for factory in dag.msfs:
#             if factory not in self.msfs:
#                 raise Exception("Magic State Factory {} Not Defined".format(factory))
#             if self.place(self.msfs[factory]) == False:
#                 raise Exception("No legal placement for MSFs")

#     def place_factory(self, unallocated_segments, factory):
#         for segment in unallocated_segments:
#             if segment.y_0 + factory.height < self.height:
#                 if segment.x_0 + factory.width < self.width:
#                     region_clear = True
#                     for i in range(segment.x_0, segment.x_0 + width):
#                         if self.qcb[i][segment.y_0].state is not None:
#                             region_clear = False
                    
#                     # Try next region
#                     if region_clear:
#                         new_segments = segment.split()


#             split_segments = segments[0].split(factory.height, factory.width)
#             segments.pop(0)
#             segments.append(split_segments[1:])
#             return split_segments[0]    

        



