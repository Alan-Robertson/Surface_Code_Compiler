import unittest
from utils import consume
from functools import reduce

class SymbolTest(unittest.TestCase):
    def test_reg_reg(self):
        '''
            reg - reg
        '''
        a = RegNode(None)
        b = RegNode(None)

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

    def test_reg_route(self):
        '''
            reg - route
        '''
        route = RouteNode(None)
        reg = RegNode(None)

        bind = route.merge(reg)
        assert (type(bind) is IntermediateRegWrapper)
        assert (reg in bind)
        assert (route not in bind)
        
        intermediate = bind.bind()
        assert (reg is intermediate)
        assert (reg.parent is reg)
        assert (route.parent is reg)
        assert (route.get_parent() is reg)

    def test_reg_reg_reg(self):
        '''
            b - c - a
        '''

        a = RegNode(None)
        b = RegNode(None)
        c = RegNode(None)

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

    def test_int_int(self):
        '''
            a - b - route - c - d
        '''

        a = RegNode('a')
        b = RegNode('b')
        c = RegNode('c')
        d = RegNode('d')
        route = RouteNode('route')

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
        assert (route.parent is intermediate_ab)

        route.bind()
        assert (route.get_parent() is intermediate)
        assert (route.parent is intermediate)


    def test_alloc_int(self):
         '''
             a - route - b
         '''

         a = RegNode('a')
         b = RegNode('b')
         route = RouteNode('route')

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

         assert a.get_route_weight() > 0
         assert b.get_route_weight() > 0

         fringe = {RouteNode('Route')}


    def test_alloc_int(self):
        '''
            c - route - a - route  - b
        '''

        a = RegNode('a')
        b = RegNode('b')
        c = RegNode('c')
        route_a = RouteNode('route')
        route_b = RouteNode('route')

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

        parents = set(map(lambda x : x.get_parent(), fringe))

        assert(len(parents) == 1)
        assert a.get_route_weight() > 0
        assert b.get_route_weight() > 0

    def test_two_step(self):
        '''
            a - route - route  - b
        '''
        a = RegNode('a')
        b = RegNode('b')
        route_a = RouteNode('route_a')
        route_b = RouteNode('route_b')

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
        

        parents = set(map(lambda x : x.get_parent(), fringe))

        assert(len(parents) == 2)
        assert a.get_route_weight() > 0
        assert b.get_route_weight() > 0

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

        parents = set(map(lambda x : x.get_parent(), fringe))
        assert (a.get_route_weight() > 0.9) and (a.get_route_weight() < 1.1)
        assert (b.get_route_weight() > 0.4) and (b.get_route_weight() < 1.1)

    def test_three_step(self):
        '''
            a - route - route - route  - b
        '''
        a = RegNode('a')
        b = RegNode('b')
        route_a = RouteNode('route_a')
        route_b = RouteNode('route_b')
        route_c = RouteNode('route_c')

        a.neighbours = {route_a}
        b.neighbours = {route_b}
        route_a.neighbours = {a, route_c}
        route_b.neighbours = {b, route_c}
        route_c.neighbours = {route_a, route_b}

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

        parents = set(map(lambda x : x.get_parent(), fringe))


        assert(len(parents) == 2)
        assert a.get_route_weight() > 0.9
        assert b.get_route_weight() > 0.9

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

        parents = set(map(lambda x : x.get_parent(), fringe))
        assert (a.get_route_weight() > 1.4) and (a.get_route_weight() < 1.6)
        assert (b.get_route_weight() > 1.4) and (b.get_route_weight() < 1.6)


    def test_four_step(self):
        '''
            a - route - route - route - route - b
        '''

        a = RegNode('a')
        b = RegNode('b')
        route_a = RouteNode('route_a')
        route_b = RouteNode('route_b')
        route_c = RouteNode('route_c')
        route_d = RouteNode('route_d')

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

        parents = set(map(lambda x : x.get_parent(), fringe))
        

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

        parents = set(map(lambda x : x.get_parent(), fringe))
        
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

        parents = set(map(lambda x : x.get_parent(), fringe))
        assert(len(parents) == 1)
        assert(a.get_route_weight() > 1.9 and a.get_route_weight() < 2.1)
        assert(b.get_route_weight() > 1.9 and b.get_route_weight() < 2.1)

    def test_three_reg_step(self):
        '''
            a - route - route - route - b
                        route
                          c
        '''

        a = RegNode('a')
        b = RegNode('b')
        c = RegNode('c')
        route_a = RouteNode('route_a')
        route_b = RouteNode('route_b')
        route_c = RouteNode('route_c')
        route_d = RouteNode('route_d')

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
            

            parents = set(map(lambda x : x.get_parent(), fringe))

        assert(a.get_route_weight() > 1.3) and (a.get_route_weight() < 1.4)        
        assert(b.get_route_weight() > 1.3) and (b.get_route_weight() < 1.4)        
        assert(c.get_route_weight() > 1.3) and (c.get_route_weight() < 1.4)        

    def test_four_reg_step(self):
        '''
                          d
                        route
            a - route - route - route - b
                        route
                          c
        '''

        a = RegNode('a')
        b = RegNode('b')
        c = RegNode('c')
        d = RegNode('d')
        route_a = RouteNode('route_a')
        route_b = RouteNode('route_b')
        route_c = RouteNode('route_c')
        route_d = RouteNode('route_d')
        route_e = RouteNode('route_e')

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

            parents = set(map(lambda x : x.get_parent(), fringe))

        assert(a.get_route_weight() > 1.24) and (a.get_route_weight() < 1.26)        
        assert(b.get_route_weight() > 1.24) and (b.get_route_weight() < 1.26)        
        assert(c.get_route_weight() > 1.24) and (c.get_route_weight() < 1.26)        
        assert(d.get_route_weight() > 1.24) and (d.get_route_weight() < 1.26)        



from mapping_tree import RouteNode, RegNode, ExternRegNode, IntermediateRegWrapper, IntermediateRegNode
from qcb import SCPatch

if __name__ == '__main__':
    unittest.main()
