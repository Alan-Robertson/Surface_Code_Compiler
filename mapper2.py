from qcb import Segment, SCPatch
from typing import *
from allocator2 import AllocatorError, QCB
import numpy as np
from collections import defaultdict
from dag2 import DAG 
from utils import log
from symbol import Symbol, ExternSymbol # annotation only

from mapping_tree import RegNode, ExternRegNode, IntermediateNode
from test_tikz_helper2 import tikz_mapping_tree

class QCBMapper:
    def __init__(self, segments: List[Segment]):
        self.segments = segments

        # mapping tree variables
        self.mapping_forest: Set[RegNode] = set()
        self.mapping: 'Dict[Segment, RegNode]' = {}
        self.node_to_segment = dict()
        self.segment_to_node = dict()
        self.root: RegNode|None = None
        self.qubit_mapping: 'Dict[int, RegNode]' = {}

    def __tikz__(self):
        return tikz_mapping_tree(self)
    
    def map_all(self, dag: DAG):
        # TODO rewrite
        conj, _ = dag.calculate_physical_conjestion()
        prox, _ = dag.calculate_physical_proximity()

        lookup = dag.lookup()

        self.map_symbols(conj, prox, _, lookup)

        self.map_extern_syms(conj, prox, _, lookup)

        return self.generate_mapping_dict()
    
    def generate_mapping_dict(self) -> dict[Symbol|ExternSymbol, tuple[int, int]]:
        mapping = {}
        for sym, node in self.qubit_mapping.items():
            if sym.is_extern():
                # Extern Symbol
                mapping[sym] = (node.seg.x_0, node.seg.y_1)
            else:
                # Register Symbol
                index = node.qubits.index(sym)
                if index == len(node.qubits) - 1:
                    offset = node.slots[RegNode.REGISTER] - 1
                else:
                    offset = (index * (node.slots[RegNode.REGISTER] - 1)) // (len(node.qubits) - 1) 
                mapping[sym] = (node.seg.x_0 + offset, node.seg.y_0)
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
        for segment in self.segments:
            if segment.get_symbol() == SCPatch.REG:
                node = RegNode(segment)
                #self.mapping_forest.add(node)
                self.segment_to_node[segment] = node
                self.node_to_segment[node] = segment

            elif segment.get_symbol().is_extern():
                node = ExternRegNode(segment, segment.get_symbol().predicate)
                #self.mapping_forest.add(node)
                self.segment_to_node[segment] = node
                self.node_to_segment[node] = segment

                while len(self.mapping_forest) > 1:
                    self.grow_mapping_forest()
                
                self.root = next(iter(self.mapping_forest))

        return self.root
        

    def construct_spanning_tree(self, tikz=False):

        fringe = dict()
        visited = set()
        curr_mapping = mapping


        # Update the fringe
        for element in curr_mapping:
            for adjacent_node in element.get_adjacent():
                if adjacent_node not in visited:
                    if adjacent_node in fringe:
                        fringe[adjacent_node].append(element)
                    else:
                        fringe[adjacent_node] = [element]


        # Resolve expansion of the fringe
        joint_nodes = dict()
        for element in fringe:
            # Single element expansion, just incorporate it
            if len(fringe[element]) == 1:
                pass
            else:
                multi_join = False
                for joint_element in fringe[element]:
                    if joint_element in joint_nodes:
                        multi_join = True
                        break
                        
                if not multi_join:
                    new_node = IntermediateNode(fringe[element])
                    for child in fringe[element]:
                        joint_nodes[child] = new_node







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
                new_forest.add(IntermediateNode(group))
        self.mapping_forest = new_forest



            

