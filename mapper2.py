
from qcb import Segment, SCPatch
from typing import *
from allocator2 import AllocatorError, QCB
import numpy as np
from collections import defaultdict
from dag2 import DAG 
from utils import log
from symbol import Symbol, ExternSymbol # annotation only


# debug_count = 0
class RegNode():

    REGISTER = Symbol('REG')

    def __init__(self, seg: 'Segment|None', children: 'Set[RegNode]|None'=None, pred_sym:'Symbol|None' = None):
        assert seg or children
        # global debug_count
        # self.debug = debug_count
        # debug_count += 1
        if seg and pred_sym is None:
            self.seg = seg
            self.slots = {self.REGISTER: seg.width * seg.height}
            self.weight = 0
            self.children = set()            
            self.visited = {seg}
            self.fringe = {seg}
            self.parent = self
            self.pred_sym = pred_sym
        elif seg and pred_sym is not None:
            self.seg = seg
            self.slots = {pred_sym: 1}
            self.weight = 0
            self.children = set()
            self.visited = {seg}
            self.fringe = {seg}
            self.parent = self
            self.pred_sym = pred_sym
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
            self.pred_sym = pred_sym
        
        self.qubits: List[int] = []
        self.child_used: \
            dict[RegNode, DefaultDict[Symbol, int]] \
                = {c: defaultdict(int) for c in self.children}
        self.child_max: \
            dict[RegNode, DefaultDict[Symbol, int]] \
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

    def alloc_qubit(self, qubit: 'Symbol|ExternSymbol'):
        pred = qubit.predicate
        

        if self.seg:
            if len(self.qubits) < self.slots.get(pred, 0):
                self.qubits.append(qubit)
                return self
            else:
                raise AllocatorError("Can't map qubit, slots exhausted!")
            
        ordering = sorted(self.children, 
                        key=lambda c: 
                            (self.child_used[c].get(pred, 0), 
                            -c.weight, 
                            -self.child_max[c].get(pred, 0)
                            )
                        )
        for c in ordering:
            if self.child_used[c].get(pred, 0) < self.child_max[c].get(pred, 0):
                alloc = c.alloc_qubit(qubit)
                self.child_used[c][pred] += 1
                self.qubits.append(qubit)
                return alloc
        print(self, qubit, 
              {c: self.child_used[c].get(pred, 0) for c in self.child_used}, 
              {c: self.child_max[c].get(pred, 0) for c in self.child_max}
              )
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



class QCBMapper:
    def __init__(self, grid_segments: List[Segment]):
        self.grid_segments = grid_segments


        # mapping tree variables
        self.mapping_forest: Set[RegNode] = set()
        self.mapping: 'Dict[Segment, RegNode]' = {}
        self.root: RegNode|None = None
        self.qubit_mapping: 'Dict[int, RegNode]' = {}
    
    def map_all(self, g: DAG):
        # TODO rewrite
        conj, _ = g.calculate_physical_conjestion()
        prox, _ = g.calculate_physical_proximity()

        lookup = g.lookup()

        self.map_symbols(conj, prox, _, lookup)

        # Here we map msfs
        self.map_extern_syms(conj, prox, _, lookup)

        self.labels = None

        return self.generate_mapping_dict()
    
    def generate_mapping_dict(self):
        mapping = {}
        for qubit, node in self.qubit_mapping.items():
            if node.pred_sym is not None:
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

    def map_symbols(self, conj, prox, sym2idx, idx2sym: dict[int, Symbol|ExternSymbol]):
        self.allocated: Set[int] = set()
        total_conj = np.sum(conj, axis=1)
        sym_indices = np.argsort(total_conj)[::-1]
        for row_idx in sym_indices:
            row_sym = idx2sym[row_idx]

            if row_sym in self.allocated or row_sym.is_extern():
                continue
            self.qubit_mapping[row_sym] = self.root.alloc_qubit(row_sym)
            log("map row_sym", row_sym, self.qubit_mapping[row_sym].seg)
            self.allocated.add(row_sym)
            
            row_order = sorted((-cj, px, idx) for idx, (cj, px) in enumerate(zip(conj[row_idx,:], prox[row_idx,:])))
            for neg_cj, px, idx in row_order:
                curr_sym = idx2sym[idx]
                if -neg_cj <= 0:
                    # Row done, out of positive conj
                    break
                elif curr_sym not in self.allocated and not curr_sym.is_extern():
                    self.qubit_mapping[curr_sym] = self.root.alloc_qubit(curr_sym)
                    log("map inner_sym", curr_sym, self.qubit_mapping[curr_sym].seg)

                    self.allocated.add(curr_sym)

        # self.root.print()
        log("finished sym alloc", self.allocated)
            
    def map_extern_syms(self, conj, prox, sym2idx, idx2sym: dict[int, Symbol|ExternSymbol]):
        total_prox = np.sum(prox, axis=1)
        sym_indices = np.argsort(total_prox)
        for row_idx in sym_indices:
            sym = idx2sym[row_idx]
            if sym in self.allocated or not sym.is_extern():
                continue

            print("alloc extern_sym", sym)
            self.qubit_mapping[sym] = self.root.alloc_qubit(sym)
            print("map extern", sym, self.qubit_mapping[sym].seg)
            self.allocated.add(sym)
        
        self.root.print()     

    def generate_mapping_tree(self):
        for s in self.grid_segments:
            if s.state.state == SCPatch.REG:
                n = RegNode(seg=s)
                self.mapping_forest.add(n)
                self.mapping[s] = n
            elif s.state.state == SCPatch.EXTERN:
                n = RegNode(seg=s, pred_sym=s.state.msf.symbol.predicate)
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
        new_fringes = {root: set() for root in self.mapping_forest}
        merge = defaultdict(set)
        to_process = defaultdict(set)
        for root in self.mapping_forest:
            for seg in root.get_mapping_neighbours():
                if seg not in self.mapping:
                    new_fringes[root].add(seg)
                    to_process[seg].add(root)
                else:
                    merge[root].add(root) 
                    merge[root].add(self.mapping[seg].root())
    
        
        for seg, rootset in to_process.items():
            self.mapping[seg] = next(iter(rootset))
            for root in rootset:
                root.distribute(1 / len(rootset))
                merge[root].add(root)
                merge[root] |= rootset
        
        if debug:
            print(merge)

        for root, new_fringe in new_fringes.items():
            root.fringe = new_fringe

        assignment = {}
        numbered_groups = {}
        max_assignment = 0

        for root, group in merge.items():
            max_assignment += 1
            assignment[root] = max_assignment
            numbered_groups[max_assignment] = {root}
            for root2 in group:
                if root2 not in assignment:
                    assignment[root2] = max_assignment
                    numbered_groups[max_assignment].add(root2)
                elif assignment[root2] != max_assignment:
                    old_number = assignment[root2]
                    for r3 in numbered_groups[old_number]:
                        assignment[r3] = max_assignment
                        numbered_groups[max_assignment].add(r3)
                    del numbered_groups[old_number]

        for root in self.mapping_forest:
            if root not in assignment:
                max_assignment += 1
                assignment[root] = max_assignment
                numbered_groups[max_assignment] = {root}

        new_forest = set()
        for group in numbered_groups.values():
            if len(group) == 1:
                new_forest.add(group.pop())
            else:
                new_forest.add(RegNode(None, children=group))
        self.mapping_forest = new_forest



            

