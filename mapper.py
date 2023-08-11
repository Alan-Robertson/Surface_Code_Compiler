from qcb import SCPatch
from tree_slots import TreeSlots

class Mapper():

    def __init__(self, dag, mapping_tree):
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
