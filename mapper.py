from qcb import SCPatch
from tree_slots import TreeSlots

class QCBMapper():

    def __init__(self, dag, mapping_tree):
        self.dag = dag
        self.map = {symbol:None for symbol in dag.lookup()}
        self.mapping_tree = mapping_tree
        self.construct_map()

    def construct_map(self):
        for symbol in self.map:
            if symbol.is_extern():
                leaf = self.mapping_tree.alloc(symbol.predicate)
            else:
                leaf = self.mapping_tree.alloc(SCPatch.REG)
            if leaf == TreeSlots.NO_CHILDREN_ERROR:
                raise Exception(f"Could not allocate {symbol}")
            self.map[symbol] = leaf.get_segment()

    def dag_symbol_to_segment(self, symbol):
        if symbol.is_extern():
           symbol = self.dag.scope[symbol.get_parent()].symbol.get_parent() 
        return self.map[symbol] 

    def dag_node_to_segments(self, dag_node):
        return [self.dag_symbol_to_segment(symbol) for symbol in dag_node.get_symbol().io.keys()]

    def dag_node_to_coordinates(self, dag_node):
        segments = self.dag_node_to_segments(dag_node)
        coordinates = []
        for node, segment in zip(dag_node.scope, segments):
            print(node, segment, segment.state)
            if segment.get_state() != SCPatch.EXTERN:
                coordinates.append((segment.x_0, segment.y_0)) 
            elif node.io_element is not None:
                print("IO:", node.io_element)
                offset = segment.get_slot().io[node.io_element]
                coordinates.append((segment.x_0 + offset, segment.y_1))
            else:
                coordinates.append((segment.x_0, segment.y_1))
        print(dag_node, coordinates)
        return coordinates 

    def __getitem__(self, dag_node):
        return self.dag_node_to_coordinates(dag_node)

    def __call__(self, dag_node):
        return self.__getitem__(dag_node)
