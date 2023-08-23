from qcb import SCPatch

COLOUR_REG = 'red!20'
COLOUR_EXTERN = 'blue!20'
COLOUR_ROUTE = 'green!20'
COLOUR_IO = 'blue!50!red!50!'
COLOUR_NONE = 'black!20'
COLOUR_DEBUG = 'yellow!30'

colour_map = {
    SCPatch.IO : COLOUR_IO,
    SCPatch.ROUTE : COLOUR_ROUTE,
    SCPatch.EXTERN : COLOUR_EXTERN,
    SCPatch.REG : COLOUR_REG,
    SCPatch.INTERMEDIARY : COLOUR_NONE, 
    SCPatch.NONE : COLOUR_NONE,
    'debug' : COLOUR_DEBUG
}

def tikz_str(fn):
    def wrapper(*args, **kwargs):
        tikz_str = tikz_header()
        tikz_str += fn(*args, **kwargs)
        tikz_str += tikz_footer()
        return tikz_str
    return wrapper

def tikz(obj):
    return obj.__tikz__()

def tex(obj, *args, **kwargs):
    return tex_file(obj.__tikz__, *args, **kwargs)


def dag_colour_map(node):
    if node.is_extern():
        return COLOUR_EXTERN
    return colour_map[node.get_slot()]

def tikz_sanitise(string):
    return string.replace('_', '\\_')

def tikz_argparse(*args, **kwargs):
    arg_str = ','.join(map(tikz_sanitise, map(str, args)))
    kwarg_str = ','.join(map(lambda item: f"{tikz_sanitise(item[0])}={tikz_sanitise(item[1])}", kwargs.items()))
    if len(kwarg_str) == 0:
        return arg_str
    return f"{arg_str},{kwarg_str}"

def tex_header(*tiksargs):
    return r"""
%!TEX options=--shell-escape
\documentclass[tikz]{standalone}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{xcolor}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}
\usepackage{accsupp}    
\usepackage{graphicx}
\usepackage{mathtools}
\usepackage{pagecolor}
\usepackage{amsmath} % for \dfrac
\usepackage{tikz}
\tikzset{>=latex} % for LaTeX arrow head
\usepackage{pgfplots} 
\usepackage[edges]{forest}
\usetikzlibrary{patterns, backgrounds, arrows.meta}
\usepackage[export]{animate}


\pagecolor{white}

\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}

\begin{document}
"""

def tex_footer():
    return "\n\end{document}\n"

def tex_file(fn, *args, **kwargs):
    tex_file = tex_header()
    tex_file += fn(*args, **kwargs)
    tex_file += tex_footer()
    return tex_file


def tikz_header(*args, **kwargs):
    return f"\\begin{{tikzpicture}}[{tikz_argparse(*args, **kwargs)}]\n"

def tikz_footer():
    return "\n \\end{tikzpicture} \n"""

def tikz_rectangle(x_0, y_0, x_1, y_1, *args, **kwargs):
    return f"\\draw[{tikz_argparse(*args, **kwargs)}] \
({x_0},-{y_0}) -- ({x_0},-{y_1}) -- ({x_1},-{y_1}) -- ({x_1},-{y_0}) -- cycle;\n"

def tikz_node(x, y, label):
    return f"\\node at ({x},-{y}) {{{tikz_sanitise(label)}}};\n"

def tikz_circle(x, y, key, label, *args, **kwargs):
    return f"\\node[shape=circle \
{tikz_argparse(*args, **kwargs)}] \
({key}) at ({x}, -{y}) {{{tikz_sanitise(label)}}};\n"

def tikz_path(start, end):
    return f"\\path[->] ({start}) edge ({end});\n"




def tikz_obj_to_colour(obj):
    obj_id = id(obj)
    red = obj_id % 255
    green = (obj_id % (255 ** 2)) // 255
    blue = (obj_id % (255 ** 3)) // (255 ** 2)
    return f"{{rgb:red,{red};green,{green};blue,{blue}}}"


def animate_header():
    return "\\begin{animateinline}[]{1}\n"

def animate_footer():
    return "\\end{animateinline}\n"

def new_frame():
    return "\n \\newframe \n"


### TIKZ DAG ###

@tikz_str
def tikz_dag(dag):
    tikz_str = ""
    for layer_num, gates in enumerate(dag.layers):
        for gate_num, gate in enumerate(gates):
            tikz_str += tikz_dag_node(gate, 2 * gate_num, 2 * layer_num) 
            for prev_gate in gate.predicates:
                tikz_str += tikz_dag_edge(prev_gate, gate)
    tikz_str += tikz_footer()
    return tikz_str

def tikz_dag_node(node, x, y, *args, **kwargs):
    colour = dag_colour_map(node)
    return tikz_circle(x, y, key=hex(id(node)), label=node, draw=colour)

def tikz_dag_edge(node_start, node_end):
    return tikz_graph_edge(node_start, node_end)


### QCB Segments ###
@tikz_str
def tikz_qcb(qcb):    
    tikz_str = ""
    for segment in qcb.segments:
        tikz_str += tikz_qcb_segement(segment)    
    return tikz_str

@tikz_str
def tikz_pruned_qcb(pruned_qcb):    
    tikz_str = ""
    # Draw segments
    for vertex in pruned_qcb.graph:
        tikz_str += tikz_qcb_segement(vertex.get_segment())
    return tikz_str

def tikz_qcb_segement(segment):
    colour = colour_map[segment.get_state()]
    segment_str = tikz_segment_rectangle(segment, colour)
    sym = segment.get_symbol()
    segment_str += tikz_node(segment.x_0 + 0.5, segment.y_0 + 0.5, f"{segment}{sym}")
    return segment_str

def tikz_segment_rectangle(segment, colour, *args):
        return tikz_rectangle(
                segment.x_0, 
                segment.y_0, 
                segment.x_1 + 1, 
            segment.y_1 + 1, 
            f"fill={colour}",
            "opacity=0.5")

### TIKZ TREE ###
@tikz_str
def tikz_qcb_tree(tree, 
                  node_draw_fn=lambda node: str(node.get_slot()),
                  leaf_draw_fn=lambda node: str(node.get_slot())):
    tikz_str, _, _ = tikz_tree_nodes(tree.root, 
                                     node_draw_fn=node_draw_fn, 
                                     leaf_draw_fn=leaf_draw_fn)

    for node in tree.nodes:
        if node.parent is not node:
            tikz_str += tikz_tree_edge(node, node.parent) 
    return tikz_str


def tikz_tree_nodes(element,
                    node_draw_fn=lambda node: str(node.get_slot()),
                    leaf_draw_fn=lambda node: str(node.get_slot()),
                    ):
    x = 0
    y = 0
    tikz_str = ""
    if element.get_segment() is None: # Non-Leaf Node
        for child in element.children:
            node_tikz_str, x_val, y_val = tikz_tree_nodes(child,
                                             node_draw_fn=node_draw_fn, 
                                             leaf_draw_fn=leaf_draw_fn)
            tikz_str += node_tikz_str
            x += x_val
            y += y_val
        x /= len(element.children)
        y /= len(element.children)
        tree_tikz_str, x, y = tikz_tree_node(element, 
                                             round(x, 1), 
                                             round(y, 1), 
                                             node_draw_fn=node_draw_fn)
        tikz_str += tree_tikz_str

        for child in element.children:
            tikz_str += tikz_tree_edge(element, child)

        return tikz_str, x, y
    else: # Leaf Node
        leaf_tikz_str, x, y = tikz_tree_leaf(element, 
                                             colour=tikz_obj_to_colour(element.get_parent()),
                                             leaf_draw_fn=leaf_draw_fn)
        tikz_str += leaf_tikz_str
        return tikz_str, x, y

def tikz_tree_node(node, x, y, node_draw_fn=lambda node: str(node.get_slot())):
    return tikz_circle(x, y, hex(id(node)), node_draw_fn(node), draw=tikz_obj_to_colour(node.get_parent())), x, y 

def tikz_tree_parent_edge(node):
    if node is not node.parent:
        return tikz_path(hex(id(node)), hex(id(node.parent)))
    return ""

def tikz_tree_leaf(node, colour=None, leaf_draw_fn = lambda node: str(node.get_slot())):
    if colour is None:
        colour = dag_colour_map(node)

    return (tikz_circle(
            node.get_segment().x_0,
            node.get_segment().y_0,
            hex(id(node)), 
            leaf_draw_fn(node),
            draw=colour, fill=colour), 
    node.get_segment().x_0,
    node.get_segment().y_0)

def tikz_tree_edge(parent, child):
    return tikz_path(hex(id(parent)), hex(id(child)))



### TIKZ GRAPH ###

def tikz_graph_qcb(graph_qcb):
    tikz_str = tikz_header()
    # Draw segments
    for vertex in graph_qcb:
        tikz_str += tikz_segment_graph_node(vertex.segment)

    # Draw edges
    for vertex in graph_qcb:
        for neighbour in vertex.get_adjacent():
            tikz_str += tikz_graph_edge(vertex.segment, neighbour.segment)

    tikz_str += tikz_footer()
    return tikz_str


def tikz_graph_edge(node_start, node_end):
    return tikz_path(hex(id(node_start)), hex(id(node_end)))

def tikz_segment_graph_node(segment, *args, **kwargs):
    colour = colour_map.get(segment.get_symbol(), colour_map[SCPatch.EXTERN])
    return tikz_circle(segment.x_0, segment.y_0, hex(id(segment)), f"{segment.x_0}, {segment.y_0}", fill=colour, draw=colour)



