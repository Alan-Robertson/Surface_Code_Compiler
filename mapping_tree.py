


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
        visited = set()
        curr_fringe = self.leaves

        joint_nodes = dict()
        fringe = dict()

        while len(curr_fringe) > 0:
            # Update the fringe
            for node in curr_fringe:
                for adjacent_node in node.get_adjacent():

                    # Add unvisited node to the fringe
                    if not adjacent_node in visited:
                        if adjacent_node in fringe:
                            fringe[adjacent_node].append(node.get_parent())
                        else:
                            fringe[adjacent_node] = [node.get_parent()]

                    # Potential Simultaneous Expansion Event
                    else:
                        # Check if nodes do not share a parent
                        if adjacent_node.get_parent() != node.get_parent():

                            # Node is already being joined in this cycle
                            if node.get_parent() in joint_nodes:
                                joint_nodes[adjacent_node.get_parent()] = joint_nodes[node.get_parent()]

                            # Adjacent Node is already being joined in this cycle
                            elif adjacent_node.get_parent() in joint_nodes:
                                joint_nodes[node.get_parent()] = joint_nodes[adjacent_node.get_parent()]

                            # New Merging Event
                            else:
                                new_node = IntermediateRegWrapper(node.get_parent(), adjacent_node.get_parent())
                                joint_nodes[node] = new_node
                                joint_nodes[adjacent_node] = new_node

            for node in fringe:
                # Single element expansion, just incorporate it
                if len(fringe[node]) == 1:
                    node.parent = fringe[node][0]
                else:
                    # Span over the fringe
                    wrapper = IntermediateRegWrapper(*map(lambda x: x.get_parent(), fringe[node]))
                    for joining_node in fringe[node]:
                        if joining_node in joint_nodes:
                            wrapper.bind(joint_nodes[joining_node])
                        else:
                            joint_nodes[joining_node] = wrapper

            # Merge wrappers
            merge_nodes = set(map(lambda x: x.confirm(), joint_nodes.values()))
            x.nodes |= merge_nodes

            parents = set(map(lambda x : x.get_parent(), curr_fringe))

            curr_fringe = set()
            for node in fringe:
                visited.add(node)
                curr_fringe.add(node)
        return


        

    
class TreeNode():
    def __init__(self, vertex):
        self.vertex = vertex
        self.neighbours = set()
        self.weight = 0
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

    def __repr__(self):
        return repr(self.vertex)

    def get_parent(self):
        parent = self.parent
        while parent != parent.parent:
            parent = parent.parent
        return parent

class RouteNode(TreeNode):
    def __init__(self, vertex):
        super().__init__(vertex)

class RegNode(TreeNode):
    def __init__(self, vertex):
        self.slots = dict()
        super().__init__(vertex)

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
        self.children = set(children)
        self.intermediate_register = IntermediateRegNode()

    def confirm(self):
        self.intermediate_register.add_children(*self.children)
        return self.intermediate_register

    def bind(self, other):
        other.intermediate_register = self.intermediate_register

    def __repr__(self):
        return "[[BIND INTERMEDIATE]]"


class IntermediateRegNode(RegNode):
    def __init__(self, *children):
        self.children = set(children)
        self.slots = dict()
        self.parent = self

    def add_child(self, child):
        self.children.add(child)
        child.parent = self

    def add_children(self, *children):
        for child in children:
            self.add_child(child)

    def get_segment(self):
        return None

    def get_slot(self):
        return SCPatch.INTERMEDIARY

    def __repr__(self):
        return "[[INTERMEDIATE]]"




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