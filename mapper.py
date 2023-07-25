
from qcb import Segment, SCPatch
from typing import *
from allocator2 import AllocatorError, QCB
import numpy as np
from collections import defaultdict
from dag2 import DAG 
from utils import log


# debug_count = 0
class RegNode():
    def __init__(self, seg: 'Segment|None', children: 'Set[RegNode]|None'=None, sym = None):
        assert seg or children
        # global debug_count
        # self.debug = debug_count
        # debug_count += 1
        if seg and not sym:
            self.seg = seg
            self.slots = {0: seg.width * seg.height}
            self.weight = 0
            self.children = set()            
            self.visited = {seg}
            self.fringe = {seg}
            self.parent = self
            self.sym = sym
        elif seg and sym:
            self.seg = seg
            self.slots = {sym: 1}
            self.weight = 0
            self.children = set()
            self.visited = {seg}
            self.fringe = {seg}
            self.parent = self
            self.sym = sym
        else:
            self.seg = None
            self.slots = {
                k: sum(c.slots.get(k, 0) for c in children)
                for k in set.union(set(), *(c.slots.keys() for c in children))
            }
            self.weight = max(c.weight for c in children)
            self.children = set(children)
            self.visited = set.union(*(c.visited for c in children))
            self.fringe = set.union(*(c.fringe for c in children))
            self.parent = self
            for c in children:
                c.parent = self
            self.sym = sym
        
        self.qubits: List[int] = []
        self.child_used: \
            dict[RegNode, DefaultDict[Union[str, int], int]] \
                = {c: defaultdict(int) for c in self.children}
        self.child_max: \
            dict[RegNode, DefaultDict[Union[str, int], int]] \
                = {c: c.slots for c in self.children}


    def root(self):
        curr = self
        while curr.parent != curr:
            curr = curr.parent
        return curr

    def distribute(self, value):
        if self.children:
            for c in self.children:
                c.distribute(value / len(self.children))
            self.weight += value / len(self.children)
        else:
            self.weight += value

    def get_mapping_neighbours(self) -> Set[Segment]:
        neighbours = set()
        for s in self.fringe:
            neighbours.update(s.above | s.below | s.left | s.right)
        neighbours.difference_update(self.visited)
        return neighbours

    def alloc_qubit(self, qubit):
        k = qubit_type(qubit)

        if self.seg:
            if len(self.qubits) < self.slots.get(k, 0):
                self.qubits.append(qubit)
                return self
            else:
                raise AllocatorError("Can't map qubit, slots exhausted!")
            
        ordering = sorted(self.children, 
                        key=lambda c: 
                            (self.child_used[c].get(k, 0), 
                            -c.weight, 
                            -self.child_max[c].get(k, 0)
                            )
                        )
        for c in ordering:
            if self.child_used[c].get(k, 0) < self.child_max[c].get(k, 0):
                alloc = c.alloc_qubit(qubit)
                self.child_used[c][k] += 1
                self.qubits.append(qubit)
                return alloc
        print(self, qubit, {c: self.child_used[c].get(k, 0) for c in self.child_used} , {c: self.child_max[c].get(k, 0) for c in self.child_max})
        raise AllocatorError("Can't map qubit, slots in children exhausted!")



    # def __repr__(self):
    #     return f'RegNode({self.debug})'
    # def __str__(self):
    #     return repr(self)
    def print(self): 
        if self.seg:
            print(f'Block {str(self.seg)} {self.weight=} {self.qubits=}')
        else:
            print(f'Begin {id(self)}')
            for c in self.children:
                c.print()
            print(f'End {id(self)}')


def qubit_type(sym):
    if isinstance(sym, int):
        return 0
    elif isinstance(sym, str):
        return sym.split('_#')[0]

class QCBMapper:
    def __init__(self, grid_segments):
        self.grid_segments = grid_segments


        # mapping tree variables
        self.mapping_forest: Set[RegNode] = set()
        self.mapping: 'Dict[Segment, RegNode]' = {}
        self.root: RegNode|None = None
        self.qubit_mapping: 'Dict[int, RegNode]' = {}
    
    def map_all(self, g: DAG, qcb: QCB):
        conj, conj_m, conj_minv = g.calculate_conjestion()
        prox, _, _ = g.calculate_proximity()

        self.map_qubits(conj, prox, conj_m, conj_minv)

        g.remap_externs(qcb.n_channels, qcb.externs)

        conj, conj_m, conj_minv = g.calculate_conjestion()
        prox, _, _ = g.calculate_proximity()

        # Here we map msfs
        self.map_msfs(conj, prox, conj_m, conj_minv)

        self.labels = conj_m

        return self.generate_mapping_dict()
    
    def generate_mapping_dict(self):
        mapping = {}
        for qubit, node in self.qubit_mapping.items():
            if node.sym:
                mapping[qubit] = (node.seg.x_0, node.seg.y_1)
            elif len(node.qubits) == 1:
                mapping[qubit] = (node.seg.x_0, node.seg.y_0)
            else:
                index = node.qubits.index(qubit)
                if index == len(node.qubits) - 1:
                    offset = node.slots[0] - 1
                else:
                    offset = (index * (node.slots[0] - 1)) // (len(node.qubits) - 1) 
                mapping[qubit] = (node.seg.x_0 + offset, node.seg.y_0)
        return mapping

    def map_qubits(self, conj, prox, m, minv):
        self.allocated: Set[int] = set()
        total_conj = np.sum(conj, axis=1)
        qubits = np.argsort(total_conj)[::-1]
        for q in qubits:
            if minv[q] in self.allocated or not isinstance(minv[q], int):
                continue
            self.qubit_mapping[minv[q]] = self.root.alloc_qubit(minv[q])
            log("map q", minv[q], self.qubit_mapping[minv[q]].seg)
            self.allocated.add(minv[q])
            
            row = sorted((-c, p, i) for i, (c, p) in enumerate(zip(conj[q,:], prox[q,:])))
            for negc, p, i in row:
                if negc >= 0:
                    break
                elif minv[i] not in self.allocated and isinstance(minv[i], int):
                    self.qubit_mapping[minv[i]] = self.root.alloc_qubit(minv[i])
                    log("map i", minv[i], self.qubit_mapping[minv[i]].seg)

                    self.allocated.add(minv[i])

        # self.root.print()
        log("finished alloc", self.allocated)
            
    def map_msfs(self, conj, prox, m, minv):
        total_prox = np.sum(conj, axis=1)
        qubits = np.argsort(total_prox)
        for q in qubits:
            if minv[q] in self.allocated:
                continue
            print("alloc msf", minv[q])
            self.qubit_mapping[minv[q]] = self.root.alloc_qubit(minv[q])
            print("map", minv[q], self.qubit_mapping[minv[q]].seg)
            self.allocated.add(minv[q])
            
            # row = sorted((-c, p, i) for i, (c, p) in enumerate(zip(conj[q,:], prox[q,:])))
            # for negc, p, i in row:
            #     if negc >= 0:
            #         break
            #     elif minv[i] not in self.allocated:
            #         self.qubit_mapping[minv[i]] = self.root.alloc_qubit(minv[i])
            #         print("map", minv[i], self.qubit_mapping[minv[i]].seg)

            #         self.allocated.add(minv[i])

        self.root.print()     


    def generate_mapping_tree(self):
        for s in self.grid_segments:
            if s.state.state == SCPatch.REG:
                n = RegNode(seg=s)
                self.mapping_forest.add(n)
                self.mapping[s] = n
            elif s.state.state == SCPatch.MSF:
                n = RegNode(seg=s, sym=s.state.msf.symbol)
                self.mapping_forest.add(n)
                self.mapping[s] = n

        # self.grow_mapping_forest()
        # self.grow_mapping_forest(debug=True)

        # maxiter = 1000
        # i = 0
        # while len(self.mapping) < len(self.grid_segments) and i < maxiter:
        #     self.grow_mapping_forest()
        #     i+=1
        
        # print(len(self.grid_segments))
        # while len(self.mapping) < len(self.grid_segments):
        while len(self.mapping_forest) > 1:
            self.grow_mapping_forest()
        # for s in self.mapping_forest:
        #     s.print()
        
        self.root = next(iter(self.mapping_forest))

        return self.root
        

    

    def grow_mapping_forest(self, debug=False):
        new_fringes = {r: set() for r in self.mapping_forest}
        merge = {}
        to_process = {}
        for r in self.mapping_forest:
            for seg in r.get_mapping_neighbours():
                if seg not in self.mapping:
                    new_fringes[r].add(seg)
                    to_process[seg] = to_process.get(seg, set()) | {r}
                else:
                    merge[r] = merge.get(r, {r}) | {self.mapping[seg].root()}
    
        
        for seg, rootset in to_process.items():
            self.mapping[seg] = next(iter(rootset))
            for r in rootset:
                r.distribute(1 / len(rootset))
                merge[r] = merge.get(r, {r}) | rootset
        
        if debug:
            print(merge)

        for r, new_fringe in new_fringes.items():
            r.fringe = new_fringe

        assignment = {}
        numbered_groups = {}
        max_assignment = 0

        for r, group in merge.items():
            max_assignment += 1
            assignment[r] = max_assignment
            numbered_groups[max_assignment] = {r}
            for r2 in group:
                if r2 not in assignment:
                    assignment[r2] = max_assignment
                    numbered_groups[max_assignment].add(r2)
                elif assignment[r2] != max_assignment:
                    old_number = assignment[r2]
                    for r3 in numbered_groups[old_number]:
                        assignment[r3] = max_assignment
                        numbered_groups[max_assignment].add(r3)
                    del numbered_groups[old_number]

        for r in self.mapping_forest:
            if r not in assignment:
                max_assignment += 1
                assignment[r] = max_assignment
                numbered_groups[max_assignment] = {r}

        new_forest = set()
        for group in numbered_groups.values():
            if len(group) == 1:
                new_forest.add(group.pop())
            else:
                new_forest.add(RegNode(None, children=group))
        self.mapping_forest = new_forest



            

