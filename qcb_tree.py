from qcb import SCPatch
from tree_slots import TreeSlots, SegmentSlot

from collections import deque as consume
from itertools import chain
from functools import reduce

from tikz_utils import tikz_qcb_tree

class QCBTree():
    def __init__(self, qcb_graph, construct=True, distribute=True):
        self.root = None
        self.graph_to_tree = dict()
        self.tree_to_graph = dict()
        self.leaves = set()
        self.nodes = set()
        self.graph = qcb_graph

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
        if construct:
           self.construct_spanning_tree()
        if distribute:
           self.distribute_slots()

    def get_qcb(self):
        return self.graph.get_qcb()

    def selector(self, vertex):
        if vertex.is_extern():
            return ExternRegNode
        if vertex.get_slot() == SCPatch.REG:
            return RegNode
        if vertex.get_slot() == SCPatch.ROUTE:
            return RouteNode 
        if vertex.get_slot() == SCPatch.IO:
            return RegNode 

    def construct_spanning_tree(self):

        fringe = self.leaves
        parents = fringe

        while len(parents) > 1: 
            joint_nodes = set()
            starter = fringe
            fringe = reduce(lambda a, b: a | b, 
                       map(lambda x: set(
                           i for i in x.get_adjacent() if i.get_parent() != x.get_parent()),
                           starter)
                       )
 
            for node in starter:

                for adjacent_node in node.get_adjacent():
                    parent = node.get_parent()
                    adj_parent = adjacent_node.get_parent()
                    if parent in joint_nodes:
                        joint_nodes.remove(parent)
                    if adj_parent in joint_nodes:
                        joint_nodes.remove(adj_parent)
                    joint_nodes.add(adj_parent.merge(parent))

            consume(map(lambda x: x.distribute(), fringe))
            consume(map(lambda x: x.bind(), joint_nodes))
            consume(map(lambda x: x.bind(), fringe))

            parents = set(map(lambda x : x.parent, fringe))
            consume(map(lambda x: x.bind(), parents)) 
        self.root = next(iter(self.leaves)).get_parent()
        return

    def alloc(self, *args, **kwargs):
        return self.root.alloc(*args, **kwargs)

    def distribute_slots(self):
        fringe = self.leaves
        while len(fringe) > 1:
            consume(map(lambda x: x.distribute_slots(), fringe))
            fringe = {node.parent for node in fringe}
        return 

    def __tikz__(self):
        return tikz_qcb_tree(self)


class TreeNode():
    def __init__(self, vertex):
        self.vertex = vertex
        self.neighbours = set()
        self.parent = self
        
    def get_symbol(self):
        return self.vertex.get_symbol()
    
    def get_state(self):
        return self.vertex.get_state()
    
    def get_slot(self):
        return self.vertex.get_slot()

    def get_slot_name(self):
        return self.vertex.get_slot_name()

    def is_extern(self):
        return self.vertex.is_extern()

    def get_segment(self):
        return self.vertex.get_segment()

    def get_adjacent(self):
        return self.neighbours

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
    
    def distributed(self):
        return False

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

    def get_bound_parent(self):
        parent = self
        while parent != parent.parent and not isinstance(parent.parent, IntermediateRegWrapper):
            parent = parent.parent
        return parent

    def alloc(self, *args, **kwargs):
        return

    def distribute(self, *args, **kwargs):
        pass
    
    def contains_leaf(self, leaf):
        return self is leaf


class RouteNode(TreeNode):
    def __init__(self, vertex):
        self.parents = set()
        self.weight_distributed = False
        super().__init__(vertex)

    def _merge(self, other):
        bind = IntermediateRegWrapper(other)
        self.parent = bind
        other.parent = bind
        return bind

    def bind(self):
        self.parent = self.get_parent()
        return set()

    def distribute(self):
        if self.distributed():
            return

        joining_nodes = set(i for i in self.get_adjacent() if (i.visited() and (i.get_parent() == self.get_parent()) and (type(i) is not RouteNode or type(i.parent) is not IntermediateRegWrapper)))


        #update_nodes = set(i for i in joining_nodes if not isinstance(i.get_bound_parent(), RouteNode))
        value = 1 / len(joining_nodes)

        for node in joining_nodes:
            node.get_bound_parent().distribute_weight(value)
        self.parents = joining_nodes
        self.weight_distributed = True
        return
       
    def distributed(self):
        '''
            Each route node can only be distributed once
        '''
        return self.weight_distributed

    def alloc(self, slot):
        return self.slots.alloc(slot)

class RegNode(TreeNode):
    def __init__(self, vertex, slot_type=SCPatch.REG):
        super().__init__(vertex)
        self.weight = 0
        self.slots = SegmentSlot(self)

    def distribute_weight(self, value):
        self.weight += value

    def distribute_slots(self):
        self.parent.merge_slot(self.slots)

    def get_weight(self):
        return self.weight

    def alloc(self, slot):
        return self.slots.alloc(slot)

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

    def distribute_weight(self, value):
        value /= len(self.children)
        for child in self.children:
            child.distribute_weight(value)

    def bind(self):
        self.flatten()
       
        # Single child and top level
        if len(self.children) == 1 and self.parent == self:
            child = next(iter(self.children))
            self.parent = child
            self.intermediate_register = child
            child.parent = child
            return child

        # Single child, promote them 
        if len(self.children) == 1:
            child = next(iter(self.children))
            self.intermediate_register = child
            for child in self.children:
                child.parent = self.parent
            self.parent = child
            return self.children

        # Top level node, promote children
        if self.parent == self:
            self.parent = self.intermediate_register
            self.parent.children = self.children
            for child in self.children:
                child.parent = self.parent
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
        self.slots = TreeSlots(self)
        self.parent = self

    def get_segment(self):
        return None

    def get_slot(self):
        return SCPatch.INTERMEDIARY

    def bind(self):
        for child in self.children:
            child.parent = self
        return {self}

    def merge_slot(self, slot):
        '''
            Binds a slots from a RegNode
        '''
        self.slots.bind_slot(slot)

    def distribute_slots(self):
        '''
            Dispatch method for distributing to the parent
        '''
        self.parent.merge_slots(self.slots)

    def merge_slots(self, slots):
        '''
            Merges a selection of slots from Intermediate Nodes
        '''
        self.slots.distribute_slots(slots)


    def __repr__(self):
        return "[[INTERMEDIATE]]"

    def __contains__(self, other):
        return other in self.children

    def distribute_weight(self, value):
        value /= len(self.children)
        for child in self.children:
            child.distribute_weight(value)

    def contains_leaf(self, leaf):
        '''
            Returns if it is a leaf
        '''
        return leaf in self.children or any(map(lambda x: x.contains_leaf(leaf), self.children))

