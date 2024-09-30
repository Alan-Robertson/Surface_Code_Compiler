import unittest
from surface_code_routing.utils import consume
from functools import reduce
from surface_code_routing.symbol import Symbol

from surface_code_routing.dag import DAG
from surface_code_routing.instructions import INIT, CNOT, MEAS, X, Hadamard
from surface_code_routing.symbol import Symbol, ExternSymbol
from surface_code_routing.lib_instructions import T_Factory, T, Toffoli


from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.allocator import Allocator
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.mapper import QCBMapper
from surface_code_routing.circuit_model import PatchGraph

from surface_code_routing.qcb_tree import RouteNode, RegNode, ExternRegNode, IntermediateRegWrapper, IntermediateRegNode
from surface_code_routing.qcb import SCPatch
from test_utils import GraphNodeInterface


def bounded_difference(val, targ, eps=0.1):
    return abs(val - targ) < eps

def tree_legal_types(*leaves):
    fringe = set(leaves)
    legal_types = (RegNode, IntermediateRegNode)

    while len(fringe) > 1:
        for element in fringe:
            if type(element) not in legal_types:
                return False
        fringe = set(map(lambda x: x.parent, (i for i in fringe if i.parent is not i)))
    return True

def tree_iteration(fringe):

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

        return fringe, joint_nodes




class RegNodeTest(unittest.TestCase):
    def test_reg_reg(self):
        '''
            reg - reg
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))

        fringe = {a, b}

        bind = a.merge(b)

        joints = {bind}

        assert (a in bind.children)
        assert (b in bind.children)
        assert (type(bind) is IntermediateRegWrapper)

        intermediate = bind.bind()
        assert (type(intermediate) is IntermediateRegNode)
        assert (a in intermediate.children)
        assert (b in intermediate.children)
        assert (a.get_parent() is intermediate)
        assert (b.get_parent() is intermediate)
        assert tree_legal_types(a, b)


    def test_reg_route(self):
        '''
            reg - route
        '''
        route = RouteNode(GraphNodeInterface('route'))
        reg = RegNode(GraphNodeInterface('reg'))

        bind = route.merge(reg)
        assert (type(bind) is IntermediateRegWrapper)
        assert (reg in bind)
        assert (route not in bind)
        
        intermediate = bind.bind()
        route.bind()
        assert (reg is intermediate)
        assert (reg.parent is reg)
        assert (route.parent is reg)
        assert (route.get_parent() is reg)

    def test_reg_route_reg(self):
        '''
            reg - route - reg
        '''
        route = RouteNode(GraphNodeInterface('route'))
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))

        a.neighbours = {route}
        b.neighbours = {route}
        route.neighbours = {a, b}

        fringe = {a, b}
        joint_nodes = set()
        starter = fringe
        
        fringe = reduce(lambda a, b: a | b, 
                       map(lambda x: set(
                           i for i in x.get_adjacent() if i.get_parent() != x.get_parent()),
                           starter)
                       )
 
        assert fringe == {route}
        for node in starter:
            for adjacent_node in node.get_adjacent():
                parent = node.get_parent()
                adj_parent = adjacent_node.get_parent()
                if parent in joint_nodes:
                    joint_nodes.remove(parent)
                if adj_parent in joint_nodes:
                    joint_nodes.remove(adj_parent)
                joint_nodes.add(adj_parent.merge(parent))

        assert len(joint_nodes) == 1
        assert type(a.parent) == IntermediateRegWrapper
        assert type(b.parent) == IntermediateRegWrapper
        assert type(route.parent) == IntermediateRegWrapper
        assert route.get_parent() in joint_nodes
        assert type(a.parent) == IntermediateRegWrapper
        assert type(b.parent) == IntermediateRegWrapper
        assert a.parent != b.parent
        assert a.get_parent() == b.get_parent()

        consume(map(lambda x: x.distribute(), fringe))
        #assert bounded_difference(a.get_weight(), 0.5)
        #assert bounded_difference(b.get_weight(), 0.5)
        
        consume(map(lambda x: x.bind(), joint_nodes))
        assert type(a.parent) == IntermediateRegNode
        assert type(b.parent) == IntermediateRegNode
 
        
        consume(map(lambda x: x.bind(), fringe))

        fringe, joint_nodes = tree_iteration({a, b})

        assert len(joint_nodes) == 1
        assert tree_legal_types(a, b) 
        assert a.get_parent() == b.get_parent()
        


    def test_reg_reg_reg(self):
        '''
            b - c - a
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))

        bind_ab = a.merge(b)
        bind = c.merge(a)
        assert (type(bind) is IntermediateRegWrapper)
        assert (c in bind)
        assert (a not in bind)
        assert (b not in bind)
        assert (bind_ab in bind)
        
        bind.bind()
        assert (type(bind) is IntermediateRegWrapper)
        assert (a in bind)
        assert (b in bind)
        assert (c in bind)
        assert (bind_ab not in bind)

        intermediate = bind.get_parent()
        assert (type(intermediate) is IntermediateRegNode)
        assert (a in intermediate)
        assert (b in intermediate)
        assert (c in intermediate)
        assert tree_legal_types(a, b, c)

    def test_int_int(self):
        '''
            a - b - route - c - d
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))
        route = RouteNode(GraphNodeInterface('route'))

        route.neighbours = {b, c}
        b.neighbours = {route, a}
        c.neighbours = {route, d}
        a.neighbours = {b}
        d.neighbours = {c}

        bind_ab = a.merge(b)
        bind_cd = c.merge(d)

        bind_ab.bind()
        bind_cd.bind()

        intermediate_ab = bind_ab.get_parent()
        intermediate_cd = bind_cd.get_parent()

        bind_route = route.merge(intermediate_ab)
        bind = bind_route.merge(intermediate_cd)

        assert (type(bind) is IntermediateRegWrapper)
        assert (bind_route in bind)
        assert (intermediate_cd in bind)

        intermediate = bind.bind()

        assert (intermediate_ab in bind)
        assert (intermediate_cd in bind)
        assert (intermediate_ab in intermediate)
        assert (intermediate_cd in intermediate)
        assert (route.get_parent() is intermediate)
        assert (route.parent is bind_route)

        route.bind()
        assert (route.get_parent() is intermediate)
        assert (route.parent is intermediate)
        assert tree_legal_types(a, b, c, d)


    def test_alloc_int(self):
         '''
             a - route - b
         '''

         a = RegNode(GraphNodeInterface('a'))
         b = RegNode(GraphNodeInterface('b'))
         route = RouteNode(GraphNodeInterface('route'))

         a.neighbours = {route}
         b.neighbours = {route}
         route.neighbours = {a, b}

         starter = {a, b}
         joint_nodes = set()        
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

         assert route.get_parent() in joint_nodes
         assert route.parent not in joint_nodes

         consume(map(lambda x: x.distribute(), fringe))
         consume(map(lambda x : x.bind(), joint_nodes))
         consume(map(lambda x : x.bind(), fringe))

         assert a.get_weight() > 0
         assert b.get_weight() > 0
         assert tree_legal_types(a, b)


    def test_alloc_int(self):
        '''
            c - route - a - route  - b
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        route_a = RouteNode(GraphNodeInterface('route'))
        route_b = RouteNode(GraphNodeInterface('route'))

        a.neighbours = {route_a, route_b}
        b.neighbours = {route_a}
        route_a.neighbours = {a, b}
        route_b.neighbours = {a, c}
        c.neighbours = {route_b}

        starter = {a, b, c}
        joint_nodes = set()
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

        assert(len(parents) == 1)
        assert a.get_weight() > 0
        assert b.get_weight() > 0
        assert tree_legal_types(a, b)

    def test_two_step(self):
        '''
            a - route - route  - b
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))

        a.neighbours = {route_a}
        b.neighbours = {route_b}
        route_a.neighbours = {a, route_b}
        route_b.neighbours = {b, route_a}

        starter = {a, b}
        joint_nodes = set()
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

        assert(len(parents) == 2)
        assert a.get_weight() > 0
        assert b.get_weight() > 0

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
        #assert (a.get_weight() > 0.9) and (a.get_weight() < 1.1)
        #assert (b.get_weight() > 0.4) and (b.get_weight() < 1.1)
        assert tree_legal_types(a, b)

    def test_three_step(self):
        '''
            a - route - route - route  - b
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))

        a.neighbours = {route_a}
        b.neighbours = {route_b}
        route_a.neighbours = {a, route_c}
        route_b.neighbours = {b, route_c}
        route_c.neighbours = {route_a, route_b}

        starter = {a, b}
        joint_nodes = set()
        
        fringe, joint_nodes = tree_iteration(starter)

        parents = set(map(lambda x : x.parent, fringe))

        assert(len(parents) == 2)
#        assert a.get_weight() > 0.9
#        assert b.get_weight() > 0.9
        assert tree_legal_types(a, b)
        fringe, joint_nodes = tree_iteration(fringe)

        parents = set(map(lambda x : x.parent, fringe))
#        assert (a.get_weight() > 1) and (a.get_weight() < 1)
#        assert (b.get_weight() > 1) and (b.get_weight() < 1)
        assert tree_legal_types(a, b)


    def test_four_step(self):
        '''
            a - route - route - route - route - b
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))

        a.neighbours = {route_a}
        b.neighbours = {route_d}
        route_a.neighbours = {a, route_b}
        route_b.neighbours = {route_a, route_c}
        route_c.neighbours = {route_b, route_d}
        route_d.neighbours = {route_c, b}

        starter = {a, b}
        joint_nodes = set()
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
        

        starter = fringe 
        joint_nodes = set()
        fringe = reduce(lambda a, b: a | b, 
                       map(lambda x: set(
                           i for i in x.get_adjacent() if i.get_parent() != x.get_parent()),
                           starter)
                       )
 


        for node in starter:
             for adjacent_node in node.get_adjacent():
                 parent = node.get_parent()
                 adj_parent = adjacent_node.get_parent()
                 if parent is not adj_parent:
                     if parent in joint_nodes:
                         joint_nodes.remove(parent)
                     if adj_parent in joint_nodes:
                         joint_nodes.remove(adj_parent)
                     joint_nodes.add(adj_parent.merge(parent))

        consume(map(lambda x: x.distribute(), fringe))
        consume(map(lambda x: x.bind(), joint_nodes))
        consume(map(lambda x: x.bind(), fringe))

        parents = set(map(lambda x : x.parent, fringe))
        
        starter = fringe 
        joint_nodes = set()
        fringe = reduce(lambda a, b: a | b, 
                       map(lambda x: set(
                           i for i in x.get_adjacent() if i.get_parent() != x.get_parent()),
                           starter)
                       )
 


        for node in starter:
             for adjacent_node in node.get_adjacent():
                 parent = node.get_parent()
                 adj_parent = adjacent_node.get_parent()
                 if parent is not adj_parent:
                     if parent in joint_nodes:
                         joint_nodes.remove(parent)
                     if adj_parent in joint_nodes:
                         joint_nodes.remove(adj_parent)
                     joint_nodes.add(adj_parent.merge(parent))

        consume(map(lambda x: x.distribute(), fringe))
        consume(map(lambda x: x.bind(), joint_nodes))
        consume(map(lambda x: x.bind(), fringe))

        parents = set(map(lambda x : x.parent, fringe))
        assert(len(parents) == 1)
        #assert(a.get_weight() > 1.9 and a.get_weight() < 2.1)
        #assert(b.get_weight() > 1.9 and b.get_weight() < 2.1)
        assert tree_legal_types(a, b)


    def test_three_reg_step(self):
        '''
            a - route - route - route - b
                        route
                          c
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))

        a.neighbours = {route_a}
        b.neighbours = {route_b}
        c.neighbours = {route_c}
        route_a.neighbours = {a, route_d}
        route_b.neighbours = {b, route_d}
        route_c.neighbours = {c, route_d}
        route_d.neighbours = {route_a, route_b, route_c}

        fringe = {a, b, c}
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
                     joint_nodes.add(adjacent_node.merge(parent))


            consume(map(lambda x: x.distribute(), fringe))
            consume(map(lambda x: x.bind(), joint_nodes))
            consume(map(lambda x: x.bind(), fringe))
            

            parents = set(map(lambda x : x.parent, fringe))

        #assert(a.get_weight() > 1.3) and (a.get_weight() < 1.4)        
        #assert(b.get_weight() > 1.3) and (b.get_weight() < 1.4)        
        #assert(c.get_weight() > 1.3) and (c.get_weight() < 1.4)        
        assert tree_legal_types(a, b, c)

    def test_four_reg_step(self):
        '''
                          d
                        route
            a - route - route - route - b
                        route
                          c
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))

        a.neighbours = {route_a}
        b.neighbours = {route_b}
        c.neighbours = {route_c}
        d.neighbours = {route_d}
        route_a.neighbours = {a, route_e}
        route_b.neighbours = {b, route_e}
        route_c.neighbours = {c, route_e}
        route_d.neighbours = {d, route_e}
        route_e.neighbours = {route_a, route_b, route_c, route_d}

        fringe = {a, b, c, d}
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

        #assert(a.get_weight() > 1.24) and (a.get_weight() < 1.26)        
        #assert(b.get_weight() > 1.24) and (b.get_weight() < 1.26)        
        #assert(c.get_weight() > 1.24) and (c.get_weight() < 1.26)        
        #assert(d.get_weight() > 1.24) and (d.get_weight() < 1.26)        
        assert tree_legal_types(a, b, c, d)


    def test_two_step_split(self):
        '''
            route - a - route  - b
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))

        a.neighbours = {route_a, route_b}
        b.neighbours = {route_b}
        route_a.neighbours = {a}
        route_b.neighbours = {a, b}

        starter = {a, b}
        joint_nodes = set()
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

        #assert (a.get_weight() > 1.4) and (a.get_weight() < 1.6)
        #assert (b.get_weight() > 0.4) and (b.get_weight() < 0.6)

    def test_two_step_other_split(self):
        '''
            a - route  - b - route
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))

        a.neighbours = {route_a}
        b.neighbours = {route_a, route_b}
        route_a.neighbours = {a, b}
        route_b.neighbours = {b}

        starter = {a, b}
        fringe = starter
        joint_nodes = set()
        
        parents = starter
        while len(parents) > 1: 

            fringe, joint_nodes = tree_iteration(fringe)

            parents = set(map(lambda x : x.parent, fringe))
        
        #assert (a.get_weight() > 0.4) and (a.get_weight() < 0.6)
        #assert (b.get_weight() > 1.4) and (b.get_weight() < 1.6)
        assert tree_legal_types(a, b)

    def test_four_reg_step_splits(self):
        '''
                          d
                        route
            a - route - route - route - b - route - route
                        route
                          c
                        route
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_b_one = RouteNode(GraphNodeInterface('route_b_1'))
        route_b_two = RouteNode(GraphNodeInterface('route_b_2'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_c_one = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))

        a.neighbours = {route_a}
        b.neighbours = {route_b, route_b_one}
        c.neighbours = {route_c, route_c_one}
        d.neighbours = {route_d}
        route_a.neighbours = {a, route_e}
        route_b.neighbours = {b, route_e}
        route_b_one.neighbours = {b, route_b_two}
        route_b_two.neighbours = {route_b_one}
        route_c.neighbours = {c, route_e}
        route_c_one.neighbours = {c}
        route_d.neighbours = {d, route_e}
        route_e.neighbours = {route_a, route_b, route_c, route_d}

        fringe = {a, b, c, d}
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

        #assert(a.get_weight() > 1.24) and (a.get_weight() < 1.26)        
        #assert(b.get_weight() > 3.24) and (b.get_weight() < 3.26)        
        #assert(c.get_weight() > 2.24) and (c.get_weight() < 2.26)        
        #assert(d.get_weight() > 1.24) and (d.get_weight() < 1.26)        
        assert tree_legal_types(a, b, c, d)

    def test_two_join_same_origin(self):
        '''
                a        -  route_a
                route_b  -  route_c - route_d - route_e - route_f - b
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))
        route_f = RouteNode(GraphNodeInterface('route_f'))

        a.neighbours = {route_a, route_b}
        b.neighbours = {route_f}
        route_a.neighbours = {a, route_c}
        route_b.neighbours = {a, route_c}
        route_c.neighbours = {route_a, route_b, route_d}
        route_d.neighbours = {route_c, route_e}
        route_e.neighbours = {route_d, route_f}
        route_f.neighbours = {b, route_e}


        fringe = {a, b}
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

        #assert(bounded_difference(a.get_weight(), 3.5))
        #assert(bounded_difference(b.get_weight(), 2.5))
        assert tree_legal_types(a, b)


    def test_two_join_same_origin_par(self):
        '''
                a              -      route_a
                route_b               route_d - route_e - route_f - b
                route_c  - 
        '''

        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))
        route_f = RouteNode(GraphNodeInterface('route_f'))

        a.neighbours = {route_a, route_b}
        b.neighbours = {route_f}
        route_a.neighbours = {a, route_c}
        route_b.neighbours = {a, route_c}
        route_c.neighbours = {route_a, route_b, route_d}
        route_d.neighbours = {route_c, route_e}
        route_e.neighbours = {route_d, route_f}
        route_f.neighbours = {b, route_e}


        fringe = {a, b}
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
            assert tree_legal_types(a, b)

        #assert(bounded_difference(a.get_weight(), 3.5))
        #assert(bounded_difference(b.get_weight(), 2.5))


    def test_two_join_same_origin_par(self):
        '''
                a  route_a route_b               
                route_c    route_d - route_e - route_f -  - route_g - b
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))
        route_f = RouteNode(GraphNodeInterface('route_f'))
        route_g = RouteNode(GraphNodeInterface('route_g'))

        a.neighbours = {route_a, route_c}
        b.neighbours = {route_g}
        route_a.neighbours = {a, route_b}
        route_b.neighbours = {route_a, route_d}
        route_c.neighbours = {a, route_d}
        route_d.neighbours = {route_c, route_b, route_e}
        route_e.neighbours = {route_d, route_f}
        route_f.neighbours = {route_g, route_e}
        route_g.neighbours = {route_f, b} 

        fringe = {a, b}
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
            assert tree_legal_types(a, b)


        #assert(bounded_difference(a.get_weight(), 4.5))
        #assert(bounded_difference(b.get_weight(), 2.5))




    def test_merge_intermediates(self):
        '''
            a - route_a - b               c - route_f - d
                route_b - route_c - route_d - route_e
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))

        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))
        route_f = RouteNode(GraphNodeInterface('route_f'))

        a.neighbours = {route_a}
        b.neighbours = {route_a}
        c.neighbours = {route_f}
        d.neighbours = {route_f}
        route_a.neighbours = {a, b, route_b}
        route_b.neighbours = {route_a, route_c}
        route_c.neighbours = {route_b, route_d}
        route_d.neighbours = {route_c, route_e}
        route_e.neighbours = {route_d, route_f}
        route_f.neighbours = {c, d, route_e}

        fringe = {a, b, c, d}
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
            assert tree_legal_types(a, b)


        #assert(bounded_difference(a.get_weight(), 1.5))
        #assert(bounded_difference(b.get_weight(), 1.5))
        #assert(bounded_difference(c.get_weight(), 1.5))
        #assert(bounded_difference(d.get_weight(), 1.5))

    def test_merge_intermediates_odd_path(self):
        '''
            a - route_a - b                         c - route_f - d
                route_b - route_c - route_x - route_d - route_e
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))

        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))
        route_f = RouteNode(GraphNodeInterface('route_f'))

        route_x = RouteNode(GraphNodeInterface('route_x'))
 

        a.neighbours = {route_a}
        b.neighbours = {route_a}
        c.neighbours = {route_f}
        d.neighbours = {route_f}
        route_a.neighbours = {a, b, route_b}
        route_b.neighbours = {route_a, route_c}
        route_c.neighbours = {route_b, route_x}
        route_x.neighbours = {route_c, route_d}
        route_d.neighbours = {route_x, route_e}
        route_e.neighbours = {route_d, route_f}
        route_f.neighbours = {c, d, route_e}

        fringe = {a, b, c, d}
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
            assert tree_legal_types(a, b)


        #assert(bounded_difference(a.get_weight(), 1.75))
        #assert(bounded_difference(b.get_weight(), 1.75))
        #assert(bounded_difference(c.get_weight(), 1.75))
        #assert(bounded_difference(d.get_weight(), 1.75))

    def test_multi_merge_intermediates(self):
        '''
            a - route_a - b               c - route_f - d               e - route_j - f
                route_b - route_c - route_d - route_e - route_g - route_h - route_i
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))
        e = RegNode(GraphNodeInterface('e'))
        f = RegNode(GraphNodeInterface('f'))

        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))
        route_f = RouteNode(GraphNodeInterface('route_f'))
        route_g = RouteNode(GraphNodeInterface('route_g'))
        route_h = RouteNode(GraphNodeInterface('route_h'))
        route_i = RouteNode(GraphNodeInterface('route_i'))
        route_j = RouteNode(GraphNodeInterface('route_j'))

        a.neighbours = {route_a}
        b.neighbours = {route_a}
        c.neighbours = {route_f}
        d.neighbours = {route_f}
        e.neighbours = {route_j}
        f.neighbours = {route_j}

        route_a.neighbours = {a, b, route_b}
        route_b.neighbours = {route_a, route_c}
        route_c.neighbours = {route_b, route_d}

        route_d.neighbours = {route_c, route_e}
        route_e.neighbours = {route_d, route_f, route_g}
        route_f.neighbours = {c, d, route_e}
        route_g.neighbours = {route_e, route_h}

        route_h.neighbours = {route_g, route_i}
        route_i.neighbours = {route_h, route_j}
        route_j.neighbours = {e, f, route_i}

        fringe = {a, b, c, d, e, f}
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
            assert tree_legal_types(a, b)

        #assert(bounded_difference(a.get_weight(), 1.5))
        #assert(bounded_difference(b.get_weight(), 1.5))
        #assert(bounded_difference(c.get_weight(), 2))
        #assert(bounded_difference(d.get_weight(), 2))
        #assert(bounded_difference(e.get_weight(), 1.5))
        #assert(bounded_difference(f.get_weight(), 1.5))
 


    def test_larger(self):

        registers = {char:RegNode(GraphNodeInterface(char)) for char in 'abcdefghiijkl'}
        routes = {i:RouteNode(GraphNodeInterface(str(i))) for i in range(1, 29)}

        registers['a'].neighbours = {routes[7]}
        registers['b'].neighbours = {routes[1]}
        registers['c'].neighbours = {routes[16]}
        registers['d'].neighbours = {routes[17]}
        registers['e'].neighbours = {routes[18]}
        registers['f'].neighbours = {routes[3]}
        registers['g'].neighbours = {routes[6]}
        registers['h'].neighbours = {routes[6]}
        registers['i'].neighbours = {routes[8]}
        registers['j'].neighbours = {routes[19]}
        registers['k'].neighbours = {routes[21]}
        registers['l'].neighbours = {routes[20]}
       
        routes[1].neighbours = {registers['b'], routes[2], routes[4]}                  
        routes[2].neighbours = {routes[2], routes[3]}                  
        routes[3].neighbours = {registers['f'], routes[2]}                  
        routes[4].neighbours = {routes[1], routes[9]}                  
        routes[5].neighbours = {routes[2], routes[6], routes[10]}                  
        routes[6].neighbours = {registers['g'], registers['h'], routes[5]}
        routes[7].neighbours = {registers['a'], routes[8], routes[11]}                  
        routes[8].neighbours = {registers['i'], routes[7], routes[9]}                  
        routes[9].neighbours = {routes[8], routes[4]}                  
        routes[10].neighbours = {routes[5], routes[18], routes[19]}                  
        routes[11].neighbours = {routes[7], routes[20]}                  

        routes[16].neighbours = {registers['c'], routes[17]}                  
        routes[17].neighbours = {registers['d'], routes[16], routes[18]}                  
        routes[18].neighbours = {registers['e'], routes[17], routes[10]}                  
        routes[19].neighbours = {registers['j'], routes[10]}                  
        routes[20].neighbours = {registers['l'], routes[11], routes[21]}                  
        routes[21].neighbours = {registers['k'], routes[20]}                  

        fringe = set(registers.values())
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

    def test_reproducibility(self):
        def dag_fn(n_qubits, width, height): 
             dag = DAG(f'{n_qubits}_height')
             for i in range(n_qubits):
                 dag.add_gate(Hadamard(f'q_{i}'))
                 for j in range(i + 1, n_qubits):
                     dag.add_gate(CNOT(f'q_{j}', f'q_{i}'))
             return dag
        height = 5
        width = 5
        n_qubits = 6
        qcb_base = QCB(height, width, (dag_fn(n_qubits, height, width)))
        Allocator(qcb_base)
        graph_base = QCBGraph(qcb_base)
        nodes_base = list(graph_base.graph)
        nodes_base.sort(key=lambda node: node.segment.x_0 * height + node.segment.y_0)
        for i in range(20):
            qcb = QCB(height, width, (dag_fn(n_qubits, height, width)))
            Allocator(qcb)
            graph = QCBGraph(qcb)
            nodes = list(graph.graph)
            nodes.sort(key=lambda node: node.segment.x_0 * height + node.segment.y_0)
            assert(len(nodes_base) == len(nodes))
            for node, node_b in zip(nodes, nodes_base):
                assert(node.get_slot() == node_b.get_slot())



    def test_compiler_chain(self):
        g = DAG(Symbol('Test'))
        g.add_gate(INIT('a', 'b', 'c', 'd'))
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(T('a'))
        g.add_gate(CNOT('a', 'b'))
        g.add_gate(Toffoli('a', 'b', 'c'))
        g.add_gate(T('a'))
        g.add_gate(T('a'))
        g.add_gate(T('c'))
        g.add_gate(T('d'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))
        g.add_gate(T('a'))
        g.add_gate(T('c'))
        g.add_gate(Toffoli('a', 'b', 'c'))
        g.add_gate(CNOT('c', 'd'))
        g.add_gate(CNOT('c', 'a'))
        g.add_gate(CNOT('b', 'd'))

        sym = ExternSymbol('T_Factory')
        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))

        qcb_base = QCB(15, 10, g)
        allocator = Allocator(qcb_base, factory_impl)

        graph = QCBGraph(qcb_base)
        tree = QCBTree(graph)

if __name__ == '__main__':
    unittest.main()
