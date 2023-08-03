from qcb import SCPatch
from collections import deque as consume
from itertools import chain
from functools import reduce

class QCBTree():
    def __init__(self, qcb_graph):
        self.root = None
        self.graph_to_tree = dict()
        self.tree_to_graph = dict()
        self.leaves = set()
        self.nodes = set()

        # Create vertices for nodes in the tree
        for vertex in qcb_graph:
            constructor = self.selector(vertex)

            if constructor is not None:

                # Construct the tree node
                tree_node = constructor(vertex)
                
                # This one will be a leaf of the tree
                if constructor in (RegNode, ExternRegNode):
                    self.leaves.add(tree_node)
                self.graph_to_tree[vertex] = tree_node
                self.tree_to_graph[tree_node] = vertex
                self.nodes.add(tree_node)

        # Reconstruct adjacency
        for tree_node in self.nodes:
            tree_node.neighbours = set(map(self.graph_to_tree.__getitem__, tree_node.vertex.get_adjacent()))

    def selector(self, vertex):
        if vertex.is_extern():
            return ExternRegNode
        if vertex.get_slot() == SCPatch.REG:
            return RegNode
        if vertex.get_slot() == SCPatch.ROUTE:
            return RouteNode 
        return TreeNode # IO Nodes

    def construct_spanning_tree(self, tikz=False):
        
        fringe = self.leaves

        while len(fringe) > 0:
            
            curr_fringe = fringe
            joint_nodes = set()    
            fringe = set()

            # Merge on a shared intermediary
            for node in curr_fringe:
                for adjacent_node in node.get_adjacent():

                    # Add unvisited node to the fringe
                    if not adjacent_node.visited():
                        fringe.add(adjacent_node)
                        if (parent := node.get_parent()) in joint_nodes:
                            joint_nodes.remove(parent)
                        joint_nodes.add(adjacent_node.merge(parent))

                    # Potential merger
                    elif adjacent_node.get_parent() is not node.get_parent():
                        if (parent := node.get_parent()) in joint_nodes:
                            joint_nodes.remove(parent)
                        joint_nodes.add(adjacent_node.merge(parent))                   
                                                   
            # Merge wrappers
            consume(map(lambda x: x.flatten(), joint_nodes))
            consume(map(lambda x: x.alloc(), fringe))
            merged_nodes = set(map(lambda x: x.confirm(), joint_nodes))
            self.nodes |= merged_nodes

        self.root = next(iter(self.nodes)).get_parent()
        return
       
from test_tikz_helper2 import tikz_partial_tree
    
class TreeNode():
    def __init__(self, vertex):
        self.vertex = vertex
        self.neighbours = set()
        self.parent = self
        
    def get_symbol(self):
        return self.vertex.get_symbol()

    def is_extern(self):
        return self.vertex.is_extern()

    def get_segment(self):
        return self.vertex.get_segment()

    def get_adjacent(self):
        return self.neighbours

    def get_slot(self):
        return self.vertex.get_slot()

    def visited(self):
        return not (self.parent == self)

    def bind(self):
        '''
            Proxy for wrapper binding
        '''
        return {self}
    def distribute(self):
        '''
            Abstract interface
        '''
        pass

    def merge(self, other):
        '''
            Base case abstract method wrapper
        '''
        bind = self.get_parent()._merge(other.get_parent())
        if self.parent is self:
            bind = self.parent
        return bind

    def _merge(self, other):
        bind = IntermediateRegWrapper(self, other)
        self.parent = bind
        other.parent = bind
        return bind

    def __repr__(self):
        return repr(f"VERTEX: {self.vertex.__repr__()}")

    def get_parent(self):
        parent = self.parent
        while parent != parent.parent:
            parent = parent.parent
        return parent

    def alloc(self, *args, **kwargs):
        return

    def alloc_slots(self, *args, **kwargs):
        return self.parent.alloc_slots(*args, **kwargs)

    def contains_leaf(self, leaf):
        return self is leaf


class RouteNode(TreeNode):
    def __init__(self, vertex):
        self.parents = set()
        super().__init__(vertex)

    def _merge(self, other):
        bind = IntermediateRegWrapper(other)
        self.parent = other.get_parent()
        other.parent = bind
        return bind

    def bind(self):
        self.parent = self.get_parent()

    def distribute(self):
        joining_nodes = set(i for i in self.get_adjacent() if (i.visited() and (i.get_parent() == self.get_parent())))
        value = 1 / len(joining_nodes)
        for node in joining_nodes:
            node.parent.alloc_slots(SCPatch.ROUTE, value)
        self.parents = joining_nodes
        
    def alloc(self, slot):
        return False

class RegNode(TreeNode):
    def __init__(self, vertex):
        self.slots = dict()
        self.weight = 0
        super().__init__(vertex)

    def alloc_slots(self, slot, value):
        if slot in self.slots:
            self.slots[slot] += value
        else:
            self.slots[slot] = value

    def get_route_weight(self):
        return self.slots.get(SCPatch.ROUTE, 0)

    def alloc(self):
        pass

    def resolve_wrapper(self):
        return self

    def flatten(self):
        return {self}


class ExternRegNode(RegNode):
    def __init__(self, vertex):
        segment = None
        super().__init__(vertex)


class IntermediateRegWrapper(RegNode):
    '''
        Wrapper for an intermediate register
        Delays binding to the intermediate reg node
    '''
    def __init__(self, *children):
        self.parent = self
        self.children = set(children)
        self.intermediate_register = IntermediateRegNode()


    def add_child(self, child):
        self.children.add(child)
        child.parent = self

    def add_children(self, *children):
        for child in children:
            self.add_child(child)

    def flatten(self):
        flattened_children = set()
        for child in self.children:
            flattened_children |= child.bind()
            child.parent = self.parent
        self.children = flattened_children

    def alloc_slots(self, slot, value):
        value /= len(self.children)
        for child in self.children:
            child.alloc_slots(slot, value)

    def bind(self):
        self.flatten()
       
        # Single and Top
        if len(self.children) == 1 and self.parent == self:
            child = next(iter(self.children))
            self.parent = child
            self.intermediate_register = child
            self.parent.children = self.children
            child.parent = child
            return child

        # Single 
        if len(self.children) == 1:
            child = next(iter(self.children))
            self.intermediate_register = child
            for child in self.children:
                child.parent is self.parent
            self.parent = child
            return self.children

        # Top level node, promote children
        if self.parent == self:
            self.parent = self.intermediate_register
            self.parent.children = self.children
            return self.parent

        # Leave this for the garbage collector
        del self.intermediate_register
        self.intermediate_register = self.parent
        for child in self.children:
            child.parent = self.parent
        return self.children

    def __repr__(self):
        return "[[BIND INTERMEDIATE]]"

    def __contains__(self, other):
        '''
            Returns if it is an immediate child
        '''
        return other in self.children

    def contains(self, leaf):
        '''
            Returns if it is a leaf
        '''
        return (leaf is self) or (leaf in self.children) or (any(map(lambda x: x.contains_leaf(leaf), self.children)))

    def resolve_wrapper(self):
        return self.intermediate_register

class IntermediateRegNode(RegNode):
    def __init__(self, *children):
        self.children = set(children)
        self.slots = dict()
        self.parent = self

    def get_segment(self):
        return None

    def get_slot(self):
        return SCPatch.INTERMEDIARY

    def bind(self):
        for child in self.children:
            child.parent = self
        return {self}

    def __repr__(self):
        return "[[INTERMEDIATE]]"

    def __contains__(self, other):
        return other in self.children

    def contains_leaf(self, leaf):
        '''
            Returns if it is a leaf
        '''
        return leaf in self.children or any(map(lambda x: x.contains_leaf(leaf), self.children))


#from test_tikz_helper2 import tikz_partial_tree


# class RegNode():
#     def __init__(self, segment):
        
#         self.segment = segment
#         self.slots = {SCPatch.REG: segment.width * segment.height}
#         self.weight = 0
#         self.children = set()            
#         self.visited = {segment}
#         self.fringe = {segment}
#         self.parent = self

#         self.symbol = SCPatch.REG

#         self.qubits: List[int] = []
#         self.child_used = dict()
#         self.child_max = dict()


#     def get_symbol(self):
#         return self.symbol

#     def get_slot(self):
#         return self.segment.get_slot()

#     def get_patch_type(self):
#         return self.segment.state

#     def is_extern(self):
#         return self.get_slot().is_extern()

#     def root(self):
#         '''
#             Get root of tree
#         '''
#         curr = self
#         while curr.parent != curr:
#             curr = curr.parent
#         return curr

#     def distribute(self, value):
#         '''
#             Distribute weights between children
#         '''
#         self.weight += value

#     def get_mapping_neighbours(self) -> Set[Segment]:
#         neighbours = set()
#         for segment in self.fringe:
#             neighbours.update(segment.get_adjacent())
#         neighbours.difference_update(self.visited)
#         return neighbours

#     def get_adjacent(self):
#         return self.segment.get_adjacent()

#     def alloc(self, symbol: 'Symbol|ExternSymbol'):
#         slot_type = symbol.predicate
        
#         if self.segment is not None:
#             if len(self.qubits) < self.slots.get(pred, 0):
#                 self.qubits.append(qubit)
#                 return self
#             else:
#                 raise AllocatorError("Can't map qubit, slots exhausted!")
            
#         ordering = sorted(self.children, 
#                         key=lambda c: 
#                             (self.child_used[c].get(pred, 0), 
#                             -c.weight, 
#                             -self.child_max[c].get(pred, 0)
#                             )
#                         )
#         for c in ordering:
#             if self.child_used[c].get(pred, 0) < self.child_max[c].get(pred, 0):
#                 alloc = c.alloc(qubit)
#                 self.child_used[c][pred] += 1
#                 self.qubits.append(qubit)
#                 return alloc
#         print(self, qubit, 
#               {c: self.child_used[c].get(pred, 0) for c in self.child_used}, 
#               {c: self.child_max[c].get(pred, 0) for c in self.child_max}
#               )
#         raise AllocatorError("Can't map qubit, slots in children exhausted!")

#     def print(self): 
#         if self.seg:
#             print(f'Block {str(self.seg)} {self.weight=} {self.qubits=}')
#         else:
#             print(f'Begin {id(self)}')
#             for c in self.children:
#                 c.print()
#             print(f'End {id(self)}')


# class IntermediateNode(RegNode):
#     def __init__(self, children: 'Set[RegNode]'):
        
#         self.segment = None
#         self.symbol = None

#         self.slots = { # Union of all children's slots
#             slot_type: sum(child.slots.get(slot_type, 0) for child in children)
#             for slot_type in set.union(set(), *(child.slots.keys() for child in children))
#         }
#         self.weight = max(child.weight for child in children)
#         self.children = set(children)
#         self.visited = set.union(*(child.visited for child in children))
#         self.fringe = set.union(*(child.fringe for child in children))
#         self.parent = self

#         # Set parents of children
#         for child in children:
#             child.parent = self
        
#         self.qubits: List[int] = []
#         self.child_used: \
#             dict[RegNode, DefaultDict[Union[str, int], int]] \
#                 = {child: defaultdict(int) for child in self.children}
#         self.child_max: \
#             dict[RegNode, DefaultDict[Union[str, int], int]] \
#                 = {child: child.slots for child in self.children}

#         def add_children(self, children):
#             for child in children:
#                 self.add_child(child)

#         def add_child(self, child):
#             if child not in self.children:
#                 self.children.add(child)
#                 self.slots

#         def get_slot(self):
#             return SCPatch.INTERMEDIARY

#         def alloc(self, symbol: 'Symbol|ExternSymbol'):
#             slot_type = symbol.predicate
            
#             if self.segment is not None:
#                 if len(self.qubits) < self.slots.get(pred, 0):
#                     self.qubits.append(qubit)
#                     return self
#                 else:
#                     raise AllocatorError("Can't map qubit, slots exhausted!")
                
#             ordering = sorted(self.children, 
#                             key=lambda c: 
#                                 (self.child_used[c].get(pred, 0), 
#                                 -c.weight, 
#                                 -self.child_max[c].get(pred, 0)
#                                 )
#                             )
#             for c in ordering:
#                 if self.child_used[c].get(pred, 0) < self.child_max[c].get(pred, 0):
#                     alloc = c.alloc(qubit)
#                     self.child_used[c][pred] += 1
#                     self.qubits.append(qubit)
#                     return alloc
#             print(self, qubit, 
#                   {c: self.child_used[c].get(pred, 0) for c in self.child_used}, 
#                   {c: self.child_max[c].get(pred, 0) for c in self.child_max}
#                   )
#             raise AllocatorError("Can't map qubit, slots in children exhausted!")

#         def distribute(self, value):
#             '''
#                 Distribute weights between children
#             '''    
#             for child in self.children:
#                 child.distribute(value / len(self.children))
#             self.weight += value / len(self.children)

# class ExternRegNode(RegNode):

#     def __init__(self, vertex):
   
#         self.segment = segment
#         self.symbol = symbol

#         self.slots = {symbol: 1}
        
#         self.children = set()
#         self.visited = {segment}
#         self.fringe = {segment}
#         self.parent = self

#         self.weight = 0

#         self.qubits: List[int] = []
#         self.child_used = dict()
#         self.child_max = dict()
