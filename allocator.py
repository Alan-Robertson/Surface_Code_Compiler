from qcb import Segment, SCPatch
from msf import MSF
from dag import DAG
from typing import *
import copy
class AllocatorError(Exception):
    pass

class QCB:
    def __init__(self, height, width, io_width, reg, *msfs_templates):
        # A list of segments comprising the qcb sorted by top left point
        self.segments: 'Set[Segment]' = {Segment(0, 0, width-1, height-1)}
        self.msfs_templates = msfs_templates
        self.height = height
        self.width = width
        self.io_width = io_width
        self.reg_allocated = 0
        self.reg_quota = reg

        # optimise variables
        self.msfs = []
        self.n_channels = 1

    def try_opt_channel(self) -> bool:
        longest_reg = max((s 
                           for s in self.segments 
                           if s.state.state == SCPatch.REG
                           and s.y_0 != 0
                           and s.y_1 != self.height), 
                           key=lambda s:s.width, 
                           default=None)
        
        if not longest_reg or longest_reg.width == 1:
            print("No longest found")
            return False

        split_x = (longest_reg.x_0 + longest_reg.x_1 + 1) // 2

        affected_regs = [s 
                        for s in self.segments 
                        if s.state.state == SCPatch.REG 
                        and s.x_0 <= split_x <= s.x_1 
                        and s.width > 1 
                        and s.y_0 != 0
                        and s.y_1 != self.height - 1]

        print("affected", affected_regs)

        new_req = self.reg_allocated - self.reg_quota - len(affected_regs)
        while new_req < 0:
            try:
                self.place_reg()
            except AllocatorError as e:
                import traceback
                traceback.print_exc()
                return False
            new_req = self.reg_allocated - self.reg_quota - len(affected_regs)

        for r in affected_regs:
            r.allocated = False
            (route, *parts), confirm = r.split(split_x, r.y_0, 1, 1)
            confirm(self.segments)

            route.state = SCPatch(SCPatch.ROUTE)
            route.allocated = True

            for p in parts:
                p.allocated = True
                p.state = SCPatch(SCPatch.REG)

            self.reg_allocated -= 1

        return True


    
    def try_opt_new_msf(self, new_msf) -> bool:
        try:
            self.place_msf(new_msf)
            return True
        except AllocatorError:
            return False

    def try_optimise(self, dag: DAG) -> bool:
        if not self.get_free_segments():
            return False
        
        def heuristic(new_msf):
            if new_msf:
                return (new_msf, dag.dag_traverse(self.n_channels, *self.msfs, new_msf)[0])
            else:
                return (new_msf, dag.dag_traverse(self.n_channels + 1, *self.msfs)[0])

        options = [new_msf for new_msf in self.msfs_templates]
        options.append(None)
        options = sorted(map(heuristic, options), key=lambda o:o[1])

        curr_score = dag.dag_traverse(self.n_channels, *self.msfs)[0]
        print(options, curr_score, self.n_channels, self.msfs)

        options = [o[0] for o in options if o[1] < curr_score]

        for new_msf in options:
            if not new_msf and self.try_opt_channel():
                self.n_channels += 1
                return True
            elif new_msf and self.try_opt_new_msf(new_msf):
                self.msfs.append(new_msf)
                return True
        
        return False

    def optimise(self, dag):
        while self.try_optimise(dag):
            pass

        while self.try_opt_channel():
            self.n_channels += 1
            pass

        print("final score", dag.dag_traverse(self.n_channels, *self.msfs)[0], self.n_channels, self.msfs)

        for s in self.get_free_segments():
            s.allocated = True
            s.state = SCPatch(SCPatch.ROUTE)
            s.debug_name = "(flood)"

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

        # Do right drop for leftmost MSF
        if msf_block.x_0 == 0:
            (msf_block, right_drop), confirm = msf_block.alloc(msf.width, msf.height + 1)
            confirm(self.segments)

            right_drop.allocated = True
            right_drop.state = SCPatch(SCPatch.ROUTE)

            msf_block.allocated = False

        # Add route layer below
        (msf_seg, route_seg), confirm = msf_block.alloc(msf.width, msf.height)
        confirm(self.segments)

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

                segs, confirm = drop_block.alloc(1, drop_height)
                confirm(self.segments)

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
                
                segs, confirm = drop_block.split(route_seg.x_0 - 1, left_route.y_1 + 1, 1, drop_height)
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
    

    def route_msf_to_io(self):
        # Find bottommost route segment connected to left edge of board
        bottom_route = max((s for s in self.segments 
                           if s.state.state == SCPatch.ROUTE
                           and s.x_0 == 0
                           and s.y_0 != self.height - 2
                           ), 
                           key = Segment.y_position)
        

        # Always valid because we perform a global top merge before
        bottom_free = next(s for s in bottom_route.below if s.x_0 == 0)
        if not bottom_free.state.state == SCPatch.IO:
            segs, confirm = bottom_free.alloc(1, self.height - bottom_route.y_1 - 3)
            if not confirm:
                raise AllocatorError("Could not route routing layer to IO")
            
            confirm(self.segments)

            route_seg, *_ = segs
            route_seg.state = SCPatch(SCPatch.ROUTE)

    def place_reg_top(self, seg):
        left_route = next((s for s in seg.left if s.y_0 == 0), None)
        if not left_route:
            # No MSFS: make dummy segment
            left_route = Segment(-1, self.height-3, -1, self.height-3)
        elif left_route.state.state == SCPatch.MSF:
            left_route = next(iter(left_route.below))


        (reg, seg), confirm = seg.alloc(seg.width, 1)
        confirm(self.segments)
        reg.state = SCPatch(SCPatch.REG)
        self.reg_allocated += reg.width

        (route, *_), confirm = seg.alloc(seg.width, 1)
        confirm(self.segments)
        route.state = SCPatch(SCPatch.ROUTE)

        if route.y_0 < left_route.y_0:
            # self.global_top_merge()
            # self.global_left_merge()
            seg = next(iter(route.below))

            (drop, *_), confirm = seg.alloc(1, left_route.y_0 - route.y_0)
            confirm(self.segments)
            drop.state = SCPatch(SCPatch.ROUTE)

    def check_reachable(self, seg):
        return any(s 
               for s in set.union(*seg.edges().values()) 
               if s.state.state == SCPatch.ROUTE)

    def check_reg_valid(self, seg):
        return ((seg.above and all(s.state.state == SCPatch.ROUTE for s in seg.above)) or 
                (seg.below and all(s.state.state == SCPatch.ROUTE for s in seg.below)))

    def check_free_reachable(self, seg):
        (row, *_), confirm = seg.alloc(seg.width, 1)
        return self.check_reachable(row)
    
    def place_reg_top_routable(self, seg):
        (reg, *_), confirm = seg.alloc(seg.width, 1)
        confirm(self.segments)
        reg.state = SCPatch(SCPatch.REG)
        self.reg_allocated += reg.width
        self.global_left_merge()
        below_seg = next(iter(s for s in reg.below if not s.allocated), None)
        if not below_seg:
            return

        if not self.check_free_reachable(below_seg):
            if below_seg.width == 1 and self.check_reachable(below_seg):
                (reg, *route), confirm = below_seg.alloc(1, 1)
                confirm(self.segments)
                reg.state = SCPatch(SCPatch.REG)
                self.reg_allocated += reg.width
                if route:
                    route[0].state = SCPatch(SCPatch.ROUTE)
                    route[0].allocated = True
                return

            reg.allocated = False
            (single, reg), confirm = reg.alloc(1, 1)
            confirm(self.segments)
            single.state = SCPatch(SCPatch.ROUTE)
            single.debug_name = '(280)'
            reg.state = SCPatch(SCPatch.REG)
            reg.allocated = True
            self.reg_allocated -= 1
            assert self.check_free_reachable(below_seg)

    def place_reg_isolated(self, seg):
        self.global_left_merge()
        seg = self.get_free_segments()[0]

        # Abandon if seg width is 1
        if seg.width == 1:
            seg.allocated = True
            seg.state = SCPatch(SCPatch.ROUTE)
            return
        
        (reg, *_), confirm = seg.alloc(1, 1)
        confirm(self.segments)
        reg.state = SCPatch(SCPatch.REG)

        if not self.check_reachable(reg):  
            below_seg = next(iter(reg.below))
            assert self.check_reachable(below_seg)
            assert not below_seg.allocated

            below_seg.allocated = True
            below_seg.state = SCPatch(SCPatch.ROUTE)


    def place_reg_route_below(self, seg):
        # First check left edge
        left_edge = next(iter(s 
                                for s in seg.left 
                                if s.y_0 <= seg.y_0 + 1 <= s.y_1
                                and s.state.state == SCPatch.ROUTE), None)
        right_edge = next(iter(s 
                            for s in seg.right 
                            if s.y_0 <= seg.y_0 + 1 <= s.y_1
                            and s.state.state == SCPatch.ROUTE), None)
        if left_edge or right_edge:
            # Don't need drop
            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)
            reg.state = SCPatch(SCPatch.REG)
            self.reg_allocated += reg.width
        else:
            # Need a center drop
            drop_x = min((s.x_0 
                        for s in seg.above 
                        if s.state.state == SCPatch.ROUTE), default=None)
            
            if not drop_x:
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
                    return self.place_reg_isolated(seg)
             
            drop_x = max(drop_x, seg.x_0)

            (row, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.segments)

            row.allocated = False
            print(row, drop_x)
            (drop, *regs), confirm = row.split(drop_x, row.y_0, 1, 1)
            confirm(self.segments)

            drop.allocated = True
            drop.state = SCPatch(SCPatch.ROUTE)

            for r in regs:
                r.allocated = True
                r.state = SCPatch(SCPatch.REG)
                self.reg_allocated += r.width

        (route, *_), confirm = seg.alloc(seg.width, 1)
        confirm(self.segments)
        route.state = SCPatch(SCPatch.ROUTE)
        return


    def place_reg(self):
        seg = next(iter(self.get_free_segments()), None)
        if not seg:
            raise AllocatorError('No free space for registers left')


        if seg.y_0 == 0:
            print(seg)
            return self.place_reg_top(seg)
        
        if all(s.state.state == SCPatch.ROUTE for s in seg.above):
            return self.place_reg_top_routable(seg)
        
        elif seg.height >= 2:
            return self.place_reg_route_below(seg)
        
        self.global_top_merge()
        seg = self.get_free_segments()[0]
        if all(s.state.state == SCPatch.ROUTE for s in seg.above):
            return self.place_reg_top_routable(seg)
        
        elif seg.height >= 2:
            return self.place_reg_route_below(seg)
        else:            
            return self.place_reg_one_high(seg)

 

    def place_reg_one_high(self, seg):
        fill_top_x = min((s for s in seg.above), key=lambda s: s.x_0, default=None)
        if not fill_top_x:
            # This is topmost block
            (block, *_), confirm = seg.alloc(1, 1)
            if self.check_reg_valid(block):
                confirm(self.segments)
                block.state = SCPatch(SCPatch.REG)
                self.reg_allocated += block.width
            elif self.check_reachable(block):
                confirm(self.segments)
                block.state = SCPatch(SCPatch.ROUTE)
            else:
                confirm(self.segments)
                block.debug_name = 'useless'
            return
        
        fill_bottom_x = min((s for s in seg.below), key=lambda s: s.x_0, default=None)
        if fill_bottom_x and fill_bottom_x.state.state == SCPatch.ROUTE:
            fill_x = fill_top_x if fill_top_x.x_1 <= fill_bottom_x.x_1 else fill_bottom_x
        else:
            fill_x = fill_top_x

        split_x = min(fill_x.x_1, seg.x_1)
        
        (block, *_), confirm = seg.alloc(split_x - seg.x_0 + 1, 1)
        if self.check_reg_valid(block):
            confirm(self.segments)
            block.state = SCPatch(SCPatch.REG)
            self.reg_allocated += block.width
        elif self.check_reachable(block):
            confirm(self.segments)
            block.state = SCPatch(SCPatch.ROUTE)
            block.debug_name = 'bail'
        else:
            confirm(self.segments)
            block.debug_name = 'useless'

    def allocate(self):
        self.place_io()

        msfs = self.msfs_templates
        if msfs:
            self.place_first_msf(msfs[0])
            self.msfs.append(msfs[0])
            self.global_left_merge()
            self.global_top_merge()

            for i, msf in enumerate(msfs[1:]):
                self.place_msf(msf)
                self.msfs.append(msf)
                self.global_left_merge()
                self.global_top_merge()

            self.route_msf_to_io()

        self.global_top_merge()
        self.global_left_merge()

        while self.reg_allocated < self.reg_quota:
            print(f"Current reg: {self.reg_allocated}/{self.reg_quota}")
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

        



