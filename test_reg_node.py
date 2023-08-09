import unittest
from utils import consume
from functools import reduce
from symbol import Symbol

from mapping_tree import RouteNode, RegNode, ExternRegNode, IntermediateRegWrapper, IntermediateRegNode
from qcb import SCPatch


def bounded_difference(val, targ, eps=0.1):
    return abs(val - targ) < eps

def tree_legal_types(*leaves):
    fringe = set(leaves)
    legal_types = (RegNode, IntermediateRegNode)

    while len(fringe) > 1:
        for element in fringe:
            if type(element) not in legal_types:
                print("FAILED: ", element)
                return False
        fringe = set(map(lambda x: x.parent, (i for i in fringe if i.parent is not i)))
    return True

def tree_iteration(fringe):

        joint_nodes = set()
        starter = fringe
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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



class GraphNodeInterface:
    def __init__(self, string, n_slots=1):
        self.string = string
        self.n_slots = n_slots

    def get_symbol(self):
        return self
    def get_segment(self):
        return self
    def get_n_slots(self):
        return self.n_slots
    def __repr__(self):
        return str(self.string)


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
        
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
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
        print('ROUTE PARENT', route.parent)
        assert type(route.parent) == IntermediateRegWrapper
        assert route.get_parent() in joint_nodes
        assert type(a.parent) == IntermediateRegWrapper
        assert type(b.parent) == IntermediateRegWrapper
        assert a.parent != b.parent
        assert a.get_parent() == b.get_parent()

        consume(map(lambda x: x.distribute(), fringe))
        assert bounded_difference(a.get_weight(), 0.5)
        assert bounded_difference(b.get_weight(), 0.5)
        
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
         fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        assert (a.get_weight() > 0.9) and (a.get_weight() < 1.1)
        assert (b.get_weight() > 0.4) and (b.get_weight() < 1.1)
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
        assert a.get_weight() > 0.9
        assert b.get_weight() > 0.9
        assert tree_legal_types(a, b)
        fringe, joint_nodes = tree_iteration(fringe)

        parents = set(map(lambda x : x.parent, fringe))
        assert (a.get_weight() > 1.4) and (a.get_weight() < 1.6)
        assert (b.get_weight() > 1.4) and (b.get_weight() < 1.6)
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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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
        assert(a.get_weight() > 1.9 and a.get_weight() < 2.1)
        assert(b.get_weight() > 1.9 and b.get_weight() < 2.1)
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
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
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

        assert(a.get_weight() > 1.3) and (a.get_weight() < 1.4)        
        assert(b.get_weight() > 1.3) and (b.get_weight() < 1.4)        
        assert(c.get_weight() > 1.3) and (c.get_weight() < 1.4)        
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
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
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

        assert(a.get_weight() > 1.24) and (a.get_weight() < 1.26)        
        assert(b.get_weight() > 1.24) and (b.get_weight() < 1.26)        
        assert(c.get_weight() > 1.24) and (c.get_weight() < 1.26)        
        assert(d.get_weight() > 1.24) and (d.get_weight() < 1.26)        
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
        fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

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

        assert (a.get_weight() > 1.4) and (a.get_weight() < 1.6)
        assert (b.get_weight() > 0.4) and (b.get_weight() < 0.6)

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
            print("UPDATE: ", fringe, parents)
        
        print("WEIGHTS:", a.get_weight(), b.get_weight())
        assert (a.get_weight() > 0.4) and (a.get_weight() < 0.6)
        assert (b.get_weight() > 1.4) and (b.get_weight() < 1.6)
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
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
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

        assert(a.get_weight() > 1.24) and (a.get_weight() < 1.26)        
        assert(b.get_weight() > 3.24) and (b.get_weight() < 3.26)        
        assert(c.get_weight() > 2.24) and (c.get_weight() < 2.26)        
        assert(d.get_weight() > 1.24) and (d.get_weight() < 1.26)        
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
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
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

        assert(bounded_difference(a.get_weight(), 3.5))
        assert(bounded_difference(b.get_weight(), 2.5))
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
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
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

        assert(bounded_difference(a.get_weight(), 3.5))
        assert(bounded_difference(b.get_weight(), 2.5))
        assert tree_legal_types(a, b)



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
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
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

        assert(bounded_difference(a.get_weight(), 4.5))
        assert(bounded_difference(b.get_weight(), 2.5))


#    def test_compiler_chain(self):
#        from graph_prune import QCBGraph
#        from mapping_tree import QCBTree
#        from allocator2 import Allocator
#        from qcb import QCB
#        from dag2 import DAG
#        from instructions import INIT, CNOT, T, Toffoli
#        from symbol import Symbol, ExternSymbol
#
#        g = DAG(Symbol('Test'))
#        g.add_gate(INIT('a', 'b', 'c', 'd'))
#        g.add_gate(CNOT('a', 'b'))
#        g.add_gate(CNOT('c', 'd'))
#        g.add_gate(T('a'))
#        g.add_gate(CNOT('a', 'b'))
#        g.add_gate(Toffoli('a', 'b', 'c'))
#        g.add_gate(T('a'))
#        g.add_gate(T('a'))
#        g.add_gate(T('c'))
#        g.add_gate(T('d'))
#        g.add_gate(CNOT('c', 'd'))
#        g.add_gate(CNOT('c', 'a'))
#        g.add_gate(CNOT('b', 'd'))
#        g.add_gate(T('a'))
#        g.add_gate(T('c'))
#        g.add_gate(Toffoli('a', 'b', 'c'))
#        g.add_gate(CNOT('c', 'd'))
#        g.add_gate(CNOT('c', 'a'))
#        g.add_gate(CNOT('b', 'd'))
#
#        sym = ExternSymbol('T_Factory')
#        factory_impl = QCB(3, 5, DAG(symbol=sym, scope={sym:sym}))
#
#        qcb_base = QCB(15, 10, g)
#        allocator = Allocator(qcb_base, factory_impl)
#        allocator.allocate()
#        allocator.optimise()
#
#        graph = QCBGraph(qcb_base)
#        tree = QCBTree(graph)
#
if __name__ == '__main__':
    unittest.main()
