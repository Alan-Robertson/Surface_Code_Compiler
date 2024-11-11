from surface_code_routing.qcb import SCPatch

OFFSET = 0.1
BASE_STYLE = r"""
\tikzset{
->-/.style={-Stealth,line width = .5mm, draw=black!70,rounded corners=3pt},
background/.style={rounded corners=5pt, thick, draw=gray!60, fill=gray!20,fill opacity=0.5},
arbitrary/.style={rounded corners=5pt,thick, draw=black!70, fill=gray!40},
reg/.style= {rounded corners=5pt, thick,  draw=black!80, fill=red!40},
regsmall/.style= {line width=0,  draw=red!40, fill=red!10},
regnode/.style= {shape=circle, line width = 0.4mm, draw=red!60,fill=red!20},
route/.style= {rounded corners=5pt, thick,  draw=black!80,fill=green!20},
routenode/.style= {line width = 0.4mm, draw=black!70,fill=green!50!black!5, rounded corners = 3pt},
routeend/.style= {rounded corners=5pt, line width=0.35mm, draw=black!80,fill=green!60},
routeendnode/.style= {shape=circle, line width = 0.4mm, draw=black!70,fill=black!50!green!80},
extern/.style= {rounded corners=5pt, thick,  draw=black!80,fill=blue!40},
externnode/.style= {shape=circle, line width=0.4mm, draw=black!80,fill=blue!20},
io/.style= {rounded corners=5pt, thick,  draw=black!80,fill=purple!60},
ionode/.style= {shape=circle, line width=0.4mm, draw=black!80,fill=purple!20},
scmerge/.style= {line width=0.4mm, draw=black!80,fill=red!40!yellow!30},
teleport/.style= {line width=0.4mm, draw=black!80,fill=cyan!40},
}
"""

COLOUR_REG = 'reg'
COLOUR_EXTERN = 'extern'
COLOUR_ROUTE = 'routeend'
COLOUR_LOCAL_ROUTE = 'route'
COLOUR_IO = 'io'
COLOUR_NONE = 'arbitrary'
COLOUR_DEBUG = 'yellow!30'
COLOUR_JOIN = 'scmerge'
COLOUR_GRID = 'black!50!white'
COLOUR_TELEPORT = 'teleport'

TELEPORT_COLOUR = 'cyan!40'
JOIN_COLOUR = 'red!40!yellow!30'


colour_map = {
    SCPatch.IO : COLOUR_IO,
    SCPatch.ROUTE : COLOUR_ROUTE,
    SCPatch.LOCAL_ROUTE : COLOUR_LOCAL_ROUTE,
    SCPatch.EXTERN : COLOUR_EXTERN,
    SCPatch.REG : COLOUR_REG,
    SCPatch.INTERMEDIARY : COLOUR_NONE, 
    SCPatch.NONE : COLOUR_NONE,
    'debug' : COLOUR_DEBUG
}


def node_map(key):
    colour = colour_map.get(key, 'debug')
    if key in ['reg', 'route', 'extern', 'io']:
        colour += 'node'
    return colour


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
    args_str = f"{arg_str},{kwarg_str}"
    if args_str[0] == ',':
        args_str = args_str[1:]
    return args_str

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
\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}
\def\offset{0.1}
\begin{document}
"""

def tex_footer():
    return "\n \\end{document}\n"

def tex_file(fn, *args, **kwargs):
    tex_file = tex_header()
    tex_file += fn(*args, **kwargs)
    tex_file += tex_footer()
    return tex_file

def tikz_header(*args, **kwargs):
    return f"\\begin{{tikzpicture}}[{tikz_argparse(*args, **kwargs)}]\n" + BASE_STYLE 
def tikz_footer():
    return "\n \\end{tikzpicture} \n"""

def tikz_rectangle(x_0, y_0, x_1, y_1, *args, key=None, **kwargs):
    tikz_str = f"\\draw[rounded corners = 3pt, {tikz_argparse(*args, **kwargs)}] \
({x_0} + \\offset ,-{y_0} -\\offset) rectangle ({x_1} - \\offset,-{y_1} + \\offset);\n"
    if key is not None:
        tikz_str += f"\\node ({key}) at ({0.5 * (x_0 + x_1)}, -{0.5 * (y_0 + y_1)}) {{}};\n"
    return tikz_str

def tikz_node(x, y, label):
    return f"\\node at ({x},-{y}) {{{tikz_sanitise(label)}}};\n"

def tikz_circle(x, y, key, label, *args, **kwargs):
    return f"\\node[shape=circle, \
{tikz_argparse(*args, **kwargs)}] \
({key}) at ({x}, -{y}) {{{tikz_sanitise(label)}}};\n"

def tikz_edge(start, end):
    return f"\\path[->-] ({start}) edge ({end});\n"

def tikz_path(start, end, *args, style=None, **kwargs):
    return f"\\path[{style}] ({start}) edge[{tikz_argparse(*args, **kwargs)}] ({end});\n"

def tikz_grid(height, width):
    return f'\\draw[step=1.0,{COLOUR_GRID},thin] (0,0) grid {width,-height};'


def tikz_obj_to_colour(obj):
    obj_id = id(obj)
    red = obj_id % 255
    green = (obj_id % (255 ** 2)) // 255
    blue = (obj_id % (255 ** 3)) // (255 ** 2)
    return f"{{rgb:red,{red};green,{green};blue,{blue}}}"

def new_frame():
    return "\n \\newframe \n"

def new_page():
    return "\n \\newpage \n"


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
def tikz_qcb(*args, **kwargs):
    return tikz_qcb_no_header(*args, **kwargs)

def tikz_qcb_no_header(qcb, seg_label_fn=lambda seg: f"\\small {seg.get_symbol()}"):    
    tikz_str = ""
    tikz_str += tikz_rectangle(-1 * OFFSET, -1 * OFFSET, qcb.width + OFFSET,  qcb.height + OFFSET, 'background')
    for segment in qcb.segments:
        tikz_str += tikz_qcb_segment(segment, seg_label_fn=seg_label_fn)    
    return tikz_str

@tikz_str
def tikz_pruned_qcb(*args, **kwargs):    
    return tikz_pruned_qcb_no_header(*args, **kwargs)

def tikz_pruned_qcb_no_header(pruned_qcb, seg_label_fn=lambda seg: f"{seg.get_symbol()}"):    
    tikz_str = ""
    # Draw segments
    for vertex in pruned_qcb.graph:
        tikz_str += tikz_qcb_segment(vertex.get_segment(), seg_label_fn=seg_label_fn)
    return tikz_str

def tikz_qcb_segment(segment, seg_label_fn=lambda seg: f"{seg.get_symbol()}"):
    colour = colour_map[segment.get_state()]
    segment_str = tikz_segment_rectangle(segment, colour)
    segment_str += tikz_node(segment.x_0 + 0.5, segment.y_0 + 0.5, seg_label_fn(segment))
    return segment_str

def tikz_segment_rectangle(segment, colour, *args):
        return tikz_rectangle(
                segment.x_0, 
                segment.y_0, 
                segment.x_1 + 1, 
            segment.y_1 + 1, 
            f"{colour}",
            "opacity=0.5")

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
    return tikz_edge(hex(id(node_start)), hex(id(node_end)))

def tikz_segment_graph_node(segment, *args, **kwargs):
    style = colour_map.get(segment.get_symbol(), colour_map[SCPatch.EXTERN])
    return tikz_circle(segment.x_0, segment.y_0, hex(id(segment)), f"{segment.x_0}, {segment.y_0}", style)


### TIKZ TREE ###
@tikz_str
def tikz_qcb_tree(*args, **kwargs):
    return tikz_qcb_tree_no_header(*args, **kwargs) 


def tikz_qcb_tree_no_header(tree, 
                  node_draw_fn=lambda node: str(node.get_slot()),
                  leaf_draw_fn=lambda node: str(node.get_slot())):
    tikz_str, _, _ = tikz_tree_nodes(tree.root, 
                                     node_draw_fn=node_draw_fn, 
                                     leaf_draw_fn=leaf_draw_fn)

    curr_nodes = tree.leaves
    while len(curr_nodes) > 0: 
        next_layer = set()
        for node in curr_nodes:
            if node.parent is not node:
                tikz_str += tikz_tree_edge(node, node.parent) 
                next_layer.add(node.parent)
        curr_nodes = next_layer
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
                                             colour=colour_map[element.get_state()],
                                             leaf_draw_fn=leaf_draw_fn)
        tikz_str += leaf_tikz_str
        return tikz_str, x, y

def tikz_tree_node(node, x, y, node_draw_fn=lambda node: str(node.get_slot())):
    style = 'arbitrary' 
    return tikz_circle(
            x, 
            y, 
            hex(id(node)), 
            node_draw_fn(node), 
            style), x, y 

def tikz_tree_parent_edge(node):
    if node is not node.parent:
        return tikz_edge(hex(id(node)), hex(id(node.parent)))
    return ""

def tikz_tree_leaf(node, colour=None, leaf_draw_fn = lambda node: str(node.get_slot())):
    if colour is None:
        style = dag_colour_map(node)
    else:
        style = colour
    return (tikz_circle(
            node.get_segment().x_0,
            node.get_segment().y_0,
            hex(id(node)), 
            leaf_draw_fn(node),
            style), 
    node.get_segment().x_0,
    node.get_segment().y_0)

def tikz_tree_edge(parent, child):
    return tikz_edge(hex(id(parent)), hex(id(child)))

### TIKZ MAPPER ###

@tikz_str
def tikz_mapper(mapper):
    return tikz_mapper_no_header(mapper)

def tikz_mapper_no_header(mapper, qcb=True, tree=True):
       
    if qcb:
        tikz_str =  tikz_qcb_no_header(mapper.mapping_tree.graph.qcb, seg_label_fn=lambda x: '')
    else:
        tikz_str = ''
    if tree:
        tikz_str += tikz_qcb_tree_no_header(mapper.mapping_tree, 
                             node_draw_fn = lambda x: "", 
                             leaf_draw_fn = lambda x: "") 
    for symbol in mapper.map:
        if not symbol.is_extern():
            coordinates, rollback = mapper.dag_symbol_to_coordinates(symbol)
            tikz_str += tikz_mapper_label(*coordinates, label=str(symbol))
    return tikz_str

def tikz_mapper_label(y, x, label):
    return tikz_node(x + 0.5, y + 0.5, label)

### TIKZ CIRCUIT MODEL ###
@tikz_str
def tikz_patch_graph(graph):
    return tikz_patch_graph_no_header(graph) 

def tikz_patch_graph_no_header(graph):
    tikz_str = ""
    for row in graph.graph:
        for element in row:
            tikz_str += tikz_patch_node(element)
    tikz_str += tikz_mapper_no_header(graph.mapper, qcb=False, tree=False)
    return tikz_str

def tikz_patch_node(element, delta = 0.13, colour_map=colour_map):
    style = colour_map[element.state]
    return tikz_rectangle(element.x + delta,
                          element.y + delta,
                          element.x + 1 - delta,
                          element.y + 1 - delta,
                          style, key = hex(id(element))) 

### TIKZ ROUTER ###
def tikz_router(router):
    tikz_str = ""
    for layer in router.layers:
        tikz_str += tikz_route_layer(router, layer)
        tikz_str += new_page()
    return tikz_str


@tikz_str
def tikz_route_layer(router, layer):
    tikz_str = '\\pgfdeclarelayer{background}\n\\pgfsetlayers{background,main}\n'

    tikz_str = tikz_patch_graph_no_header(router.graph)
    tikz_str += '\\begin{pgfonlayer}{background}\n'
    tikz_str += tikz_grid(*router.qcb.shape)
    for gate in layer:
        route = router.routes[gate]
        tikz_str += tikz_route(route, router)
    tikz_str += '\\end{pgfonlayer}\n'
    return tikz_str

def tikz_route(route, router):
    STOP_ITERATION = object()
    tikz_str = ""
    element_iter = iter(route)
    # Resources
    while (element := next(element_iter, STOP_ITERATION)) is not STOP_ITERATION:
        if isinstance(element, tuple):
            tikz_str += tikz_circle(*element, hex(id(element)), " ") 
        else:
            curr_node = element
            break
    # Routes
    element_iter = iter(route)
    curr_node = None
    while (element := next(element_iter, STOP_ITERATION)) is not STOP_ITERATION:
        if curr_node is not None:
            style = COLOUR_JOIN
            colour = JOIN_COLOUR
            if (abs(curr_node.x - element.x) + abs(curr_node.y - element.y)) > 1:
                style = COLOUR_TELEPORT
                colour = TELEPORT_COLOUR
            tikz_str += tikz_path(hex(id(curr_node)), hex(id(element)),  style=style, **{'double distance': '0.5cm', 'double':colour})
        curr_node = element

    return tikz_str

