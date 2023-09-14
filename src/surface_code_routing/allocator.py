from surface_code_routing.qcb import Segment, SCPatch, QCB
from surface_code_routing.dag import DAG
from typing import *
import copy
class AllocatorError(Exception):
    pass

class Allocator:
    def __init__(self, qcb: QCB, *extern_templates, optimise=True):
        self.qcb = qcb

        self.extern_templates = sorted(extern_templates, 
                                     key=lambda extern: (extern.width, extern.height),
                                     reverse=True)
        self.qcb.extern_templates = {x.symbol:x for x in self.extern_templates}

        self.height = qcb.height
        self.width = qcb.width
        
        self.io_width = len(qcb.io)
        self.reg_allocated = 0
        self.reg_quota = len(qcb.operations.internal_scope())

        # optimise variables
        self.msfs = []
        self.n_channels = 1
        self.test = 0
        self.allocate()
        if optimise:
           self.optimise()

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
                #import traceback
                #traceback.print_exc()
                #print("Opt channel failed, bailing...")
                return False
            new_req = self.reg_allocated - self.reg_quota - len(affected_regs)

        for r in affected_regs:
            r.allocated = False
            (route, *parts), confirm = r.split(split_x, r.y_0, 1, 1)
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
        if not self.get_free_segments(self.qcb):
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
        dag = self.qcb.operations
        while self.try_optimise():
            pass

        while self.try_opt_channel():
            self.n_channels += 1
            pass


        n_layers, compiled_layers = dag.compile(self.n_channels, *self.msfs)
        self.qcb.compiled_layers = compiled_layers

        self.global_top_merge()
        self.global_left_merge()

        free = self.get_free_segments(self.qcb)
        if free:
            last = next((s for s in free 
                         if s.x_1 == self.width - 1 
                         and s.y_1 == self.height - 1), None)
            if last and last.height >= 2:
                (bottom_block, *_), confirm = last.split(last.x_0, last.y_1-1, last.width, 2)
                confirm(self.qcb.segments)
                
                (route, reg), confirm = bottom_block.alloc(bottom_block.width, 1)
                confirm(self.qcb.segments)
                
                route.state = SCPatch(SCPatch.ROUTE)
                reg.state = SCPatch(SCPatch.REG) 
                reg.allocated = True


        self.global_merge_tl()
        for seg in self.get_free_segments(self.qcb):
            if not all(l.state.state == SCPatch.ROUTE for l in seg.left):
                (left, main), confirm = seg.alloc(1, seg.height)
                confirm(self.qcb.segments)
                left.state = SCPatch(SCPatch.ROUTE)

        # TODO add reg before flood
        while self.get_free_segments(self.qcb):
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
            

    def place_io(self):
        if self.io_width == 0:
            return

        segs, confirm = self.get_free_segments(self.qcb)[0].split(0, self.height - 1, self.io_width, 1)
        if not confirm:
            raise AllocatorError("IO placement failed")

        confirm(self.qcb.segments)

        io, *main = segs
        io.allocated = True
        io.state = SCPatch(SCPatch.IO)
        
        above_block = next(iter(io.above))
        (route, *_), confirm = above_block.split(0, self.height - 2, self.io_width, 1)
        route.allocated = True
        route.state = SCPatch(SCPatch.ROUTE)
        confirm(self.qcb.segments)

        if io.width < self.width:
            self.global_top_merge()
            self.global_left_merge()
            right_block = next(iter(io.right))
            (route, *_), confirm = right_block.alloc(1, 2)
            route.state = SCPatch(SCPatch.ROUTE)
            confirm(self.qcb.segments)

    def get_free_segments(self, qcb: QCB):
        return sorted((s for s in qcb.segments if not s.allocated), key=Segment.y_position)


    # def place_first_extern(self, extern):
    #     # Merge sequence
    #     _, confirm = self.get_free_segments(self.qcb)[0].top_merge()
    #     confirm(self.qcb.segments)
    #     _, confirm = self.get_free_segments(self.qcb)[0].left_merge()
    #     confirm(self.qcb.segments)

    #     # Attempt 1
    #     segs, confirm = self.get_free_segments(self.qcb)[0].alloc(extern.width, extern.height + 1)
    #     if not confirm:
    #         # Try to merge again
    #         _, confirm = self.get_free_segments(self.qcb)[0].top_merge()
    #         confirm(self.qcb.segments)

    #         # Attempt 2
    #         segs, confirm = self.get_free_segments(self.qcb)[0].alloc(extern.width, extern.height + 1)
    #         if not confirm:
    #             raise AllocatorError("First MSF placement failed")
        
    #     confirm(self.qcb.segments)

    #     extern_block, *others = segs
    #     extern_block.allocated = False

    #     # Split block into MSF and routing
    #     (extern_seg, route_seg), confirm = extern_block.alloc(extern.width, extern.height)
    #     confirm(self.qcb.segments)

    #     extern_seg.allocated = True
    #     extern_seg.state = SCPatch(extern)
    #     route_seg.allocated = True
    #     route_seg.state = SCPatch(SCPatch.ROUTE)

    def try_place_msf(self, msf, fringe: Tuple[int, int]) \
            -> Tuple[bool, Tuple[int, int]]:
        
        first = next((s for s in self.get_free_segments(self.qcb) if s.y_position() > fringe), None)
        if not first:
            raise AllocatorError(f"MSF placement failed: all blocks exhausted for {msf}")
        
        # Merge sequence
        segs, confirm = first.top_merge()
        confirm(self.qcb.segments)
        first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]
        segs, confirm = first.left_merge()
        confirm(self.qcb.segments)
        first = segs[0] if segs[0].y_position() == first.y_position() else segs[1]

        # Check top drop
        if first.x_0 == 0 and first.y_0 != 0: # Connect to msf routing net in row above
            bounds = (msf.width + 1, msf.height + 1)
        else:
            bounds = (msf.width, msf.height + 1) # No connection needed

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
        if msf_block.x_0 == 0 and msf_block.y_0 != 0:
            (msf_block, right_drop), confirm = msf_block.alloc(msf.width, msf.height + 1)
            confirm(self.qcb.segments)

            right_drop.allocated = True
            right_drop.state = SCPatch(SCPatch.ROUTE)

            msf_block.allocated = False

        # Add route layer below
        (msf_seg, route_seg), confirm = msf_block.alloc(msf.width, msf.height)
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

                segs, confirm = drop_block.alloc(1, drop_height)
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
                
                segs, confirm = drop_block.split(route_seg.x_0 - 1, left_route.y_1 + 1, 1, drop_height)
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
    

    def route_msf_to_io(self):
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
        if not bottom_free.state.state == SCPatch.IO:
            segs, confirm = bottom_free.alloc(1, self.height - bottom_route.y_1 - 3)
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


        (reg, seg), confirm = seg.alloc(seg.width, 1)
        confirm(self.qcb.segments)
        reg.state = SCPatch(SCPatch.REG)
        out.append(reg)
        self.reg_allocated += reg.width

        (route, *_), confirm = seg.alloc(seg.width, 1)
        confirm(self.qcb.segments)
        route.state = SCPatch(SCPatch.ROUTE)

        if route.y_0 < left_route.y_0:
            # self.global_top_merge()
            # self.global_left_merge()
            seg = next(iter(route.below))

            (drop, *_), confirm = seg.alloc(1, left_route.y_0 - route.y_0)
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
        (row, *_), confirm = seg.alloc(seg.width, 1)
        return self.check_reachable(row)
    
    def place_reg_top_routable(self, seg):
        out = []

        (reg, *_), confirm = seg.alloc(seg.width, 1)
        confirm(self.qcb.segments)
        reg.state = SCPatch(SCPatch.REG)
        out.append(reg)
        self.reg_allocated += reg.width
        self.global_left_merge()
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
        seg = self.get_free_segments(self.qcb)[0]

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
        if left_edge or right_edge:
            # Don't need drop
            (reg, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.qcb.segments)
            reg.state = SCPatch(SCPatch.REG)
            out.append(reg)
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
                    return out + self.place_reg_isolated(seg)
             
            drop_x = max(drop_x, seg.x_0)

            (row, seg), confirm = seg.alloc(seg.width, 1)
            confirm(self.qcb.segments)

            row.allocated = False
            (drop, *regs), confirm = row.split(drop_x, row.y_0, 1, 1)
            confirm(self.qcb.segments)

            drop.allocated = True
            drop.state = SCPatch(SCPatch.ROUTE)

            for r in regs:
                r.allocated = True
                r.state = SCPatch(SCPatch.REG)
                out.append(r)
                self.reg_allocated += r.width

        (route, *_), confirm = seg.alloc(seg.width, 1)
        confirm(self.qcb.segments)
        route.state = SCPatch(SCPatch.ROUTE)
        return out


    def place_reg(self) -> List[Segment]:
        seg = next(iter(self.get_free_segments(self.qcb)), None)
        if not seg:
            raise AllocatorError('No free space for registers left')


        if seg.y_0 == 0:
            return self.place_reg_top(seg)
        
        if all(s.state.state == SCPatch.ROUTE for s in seg.above):
            return self.place_reg_top_routable(seg)
        elif seg.height >= 2:
            return self.place_reg_route_below(seg)
        
        self.global_top_merge()
        seg = self.get_free_segments(self.qcb)[0]

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
        
        (block, *_), confirm = seg.alloc(split_x - seg.x_0 + 1, 1)
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

    def allocate(self):
        '''
            Perform initial allocation
        '''
        self.place_io()

        externs = self.extern_templates
        if len(externs) > 0:
            # self.place_first_extern(externs[0])
            self.place_msf(externs[0])
            self.msfs.append(externs[0])
            self.global_merge_lt()

            for i, extern in enumerate(externs[1:]):
                self.place_msf(extern)
                self.msfs.append(extern)
                self.global_merge_lt()

            self.route_msf_to_io()

        self.global_merge_tl()

        while self.reg_allocated < self.reg_quota:
            self.place_reg()
            self.global_merge_tl()
        

    def global_merge_tl(self):
        self.global_top_merge()
        self.global_left_merge()

    def global_merge_lt(self):
        self.global_left_merge()
        self.global_top_merge()

    def global_top_merge(self):
        offset = 0
        queue = self.get_free_segments(self.qcb)
        while offset < len(queue):
            _, confirm = queue[-offset-1].top_merge()
            confirm(self.qcb.segments)
            queue = self.get_free_segments(self.qcb)
            offset += 1

    def global_left_merge(self):
        offset = 0
        queue = self.get_free_segments(self.qcb)
        queue.sort(key=lambda s: (s.x_0, s.y_0))
        while offset < len(queue):
            _, confirm = queue[-offset-1].left_merge()
            confirm(self.qcb.segments)
            queue = self.get_free_segments(self.qcb)
            queue.sort(key=lambda s: (s.x_0, s.y_0))
            offset += 1
