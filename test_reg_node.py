import unittest
from utils import consume
from functools import reduce

class SymbolTest(unittest.TestCase):
    def test_reg_reg(self):
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

    def test_reg_route(self):
        route = RouteNode(None)
        reg = RegNode(None)

        bind = route.merge(reg)
        assert (type(bind) is IntermediateRegWrapper)
        assert (reg in bind)
        assert (route not in bind)
        
        intermediate = bind.bind()
        assert (reg is intermediate)
        

    def test_reg_reg_reg(self):
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

    # def test_alloc_int(self):
    #     '''
    #         a - route - b
    #     '''

    #     a = RegNode('a')
    #     b = RegNode('b')
    #     route = RouteNode('route')

    #     a.neighbours = {route}
    #     b.neighbours = {route}
    #     route.neighbours = {a, b}

    #     starter = {a, b}
    #     joint_nodes = set()        
    #     fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

    #     for node in starter:
    #         for adjacent_node in node.get_adjacent():
    #             parent = node.get_parent()
    #             adj_parent = adjacent_node.get_parent()
    #             if parent in joint_nodes:
    #                 joint_nodes.remove(parent)
    #             if adj_parent in joint_nodes:
    #                 joint_nodes.remove(adj_parent)
    #             joint_nodes.add(adjacent_node.merge(parent))

    #     assert route.get_parent() in joint_nodes
    #     assert route.parent not in joint_nodes

    #     consume(map(lambda x : x.bind(), joint_nodes))

    #     parents = set(map(lambda x : x.get_parent(), fringe))

    #     consume(map(lambda x: x.alloc(), fringe))
    #     consume(map(lambda x: x.confirm(), joint_nodes))

    #     assert(len(parents)) == 1
    #     assert a.get_route_weight() == 0.5
    #     assert b.get_route_weight() == 0.5

    #     fringe = {RouteNode('Route')}


    # def test_alloc_int(self):
    #     '''
    #         c - route - a - route  - b
    #     '''

    #     a = RegNode('a')
    #     b = RegNode('b')
    #     c = RegNode('c')
    #     route_a = RouteNode('route')
    #     route_b = RouteNode('route')

    #     a.neighbours = {route_a, route_b}
    #     b.neighbours = {route_a}
    #     route_a.neighbours = {a, b}
    #     route_b.neighbours = {a, c}
    #     c.neighbours = {route_b}

    #     starter = {a, b, c}
    #     joint_nodes = set()
    #     fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))

    #     for node in fringe:
    #         for adjacent_node in node.get_adjacent():
    #             parent = node.get_parent()
    #             if parent in joint_nodes:
    #                 joint_nodes.remove(parent)
    #             joint_nodes.add(adjacent_node.merge(parent))

    #     consume(map(lambda x : x.bind(), joint_nodes))

    #     parents = set(map(lambda x : x.get_parent(), fringe))

    #     consume(map(lambda x: x.alloc(), fringe))

    #     assert(len(parents) == 2)
    #     assert a.get_route_weight() == 0
    #     assert b.get_route_weight() == 0

    #     fringe = {RouteNode('Route')}
                

from mapping_tree import RouteNode, RegNode, ExternRegNode, IntermediateRegWrapper, IntermediateRegNode
from qcb import SCPatch

if __name__ == '__main__':
    unittest.main()
