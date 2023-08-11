from qcb import SCPatch
from tree_slots import TreeSlots

class Mapper():

    def __init__(self, scope, mapping_tree):
        self.map = dict()

        self.scope = scope
        self.mapping_tree = mapping_tree
        self.construct_map()

    def construct_map(self):
        for symbol in scope:
            if symbol.is_extern():
                leaf = self.mapping_tree.alloc(symbol)
            else:
                leaf = self.mapping_tree.alloc(SCPatch.REG)
            if leaf == TreeSlots.NO_CHILDREN_ERROR:
                raise Exception(f"Could not allocate {symbol}")
            self.map[symbol] == leaf.get_segment()

