import qcb

    
def make_segments(segments_raw):
    segments = []
    for i, c in enumerate(segments_raw):
        seg = qcb.Segment(*c[:4])
        if len(c) > 4:
            seg.allocated = c[4]
        seg.debug_name = str(i)
        segments.append(seg)
    qcb.Segment.link_edges(None, segments)
    return segments

def get_segment(segments: list[qcb.Segment], name: str):
    for s in segments:
        if s.debug_name == name:
            return s
    return None


def name_segments(segments: list[qcb.Segment], series=''):
    copy = sorted(segments, key=lambda s: (s.x_0, s.y_0))
    max_num = max(map(lambda s: int(s.debug_name) if s.debug_name else 0, copy))
    for s in copy:
        if not s.debug_name:
            s.debug_name = str(max_num) + series
            max_num += 1

def setup1():
    a = qcb.Segment(0, 0, 0, 0)
    b = qcb.Segment(1, 0, 1, 0)
    c = qcb.Segment(0, 1, 0, 1)
    d = qcb.Segment(1, 1, 1, 1)
    # a b
    # c d
    a.right.add(b)
    b.left.add(a)
    c.right.add(d)
    d.left.add(a)
    a.below.add(c)
    c.above.add(a)
    b.below.add(d)
    d.above.add(a)

    return a,b,c,d

def print_edges(segments):
    for s in segments:
        print(s.debug_name, s, end=" {")
        for label, ns in s.edges().items():
            print(f"'{label}': [", end="")
            for n in ns:
                print(n.debug_name if n.debug_name else "???", end=",")
            print("], ", end="")
        print('}')


def test1():
    # Test 1
    a,b,c,d = setup1()
    x = a.horizontal_merge(b)
    print(x)
    print(c)
    print(d)
    print(x.edges())

def test2():
    # Test 2
    p = qcb.Segment(0, 0, 2, 2)
    x = qcb.Segment(3, -1, 3, 1)
    x.debug_name = "X"
    p.right.add(x)
    new2 = p.split(1, 1, 1, 1)
    p._confirm_split(new2)
    
    name_segments(new2)
    print_edges(new2)

def print_latex(segments, file="latex.tex"):
    with open(file, "w") as f:
        print(r"""

\documentclass[preview, border=1pt, convert={outext=.png}]{standalone}
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
\usepackage{pgfplots} % for the axis environment
\usepackage[edges]{forest}
\usetikzlibrary{patterns, backgrounds, arrows.meta}

\pagecolor{white}

\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}

\begin{document}


\begin{tikzpicture}[scale=1,background rectangle/.style={fill=white},
    show background rectangle]
        """, file=f)


        for s in segments:
            print(f"\\draw ({s.x_0},-{s.y_0}) -- ({s.x_0},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_0}) -- cycle;", file=f)
            print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.debug_name}{'*'if s.allocated else ''}}};", file=f)

        print(r"""
\end{tikzpicture}


\end{document}
        """, file=f)

def print_repr(segments):
    min_x = min(s.x_0 for s in segments)
    max_x = max(s.x_1 for s in segments)
    min_y = min(s.y_0 for s in segments)
    max_y = max(s.y_1 for s in segments)
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    grid = [['.'] * 7 * width for _ in range(4 * height)]
    
    def set_cell(x, y, c):
        x -= min_x
        y -= min_y
        x *= 7
        y *= 4
        x += 3
        y += 2
        grid[y][x] = c[0] if c else "?"
        if len(c) > 1:
            grid[y][x+1] = c[1]
        else:
            grid[y][x+1] = ' '
        grid[y-1][x-1] = grid[y-1][x-2] = ' '
        grid[y+1][x-1] = grid[y+1][x-2] = ' '
        grid[y-1][x+2] = grid[y-1][x+3] = ' '
        grid[y+1][x+2] = grid[y+1][x+3] = ' '
        # grid[y][x-1] = grid[y][x+2] = ' '
        # grid[y-1][x+1] = grid[y+1][x+1] = ' '
        for i in range(x-2, x+4):
            grid[y-2][i] = '-'
        for j in range(y-1, y+2):
            grid[j][x-3] = '|'
        grid[y-2][x-3] = '+'


    def set_dir(x, y, c, dir):
        x -= min_x
        y -= min_y
        x *= 7
        y *= 4
        x += 3
        y += 2
        if dir == 'above':
            y -= 1
        elif dir == 'below':
            y += 1
        elif dir == 'left':
            x -= 2
        elif dir == 'right':
            x += 2
        grid[y][x] = c[0]
        if len(c) > 1:
            grid[y][x+1] = c[1]
        else:
            grid[y][x+1] = ' '

    r = {'left': 'right', 'right': 'left', 'above': 'below', 'below': 'above'}
    for s in segments:
        for i in range(s.x_0, s.x_1 + 1):
            for j in range(s.y_0, s.y_1 + 1):
                set_cell(i, j, s.debug_name)
                for label, edge in s.edges().items():
                    for n in edge:
                        if n.seg_adjacent(n, qcb.Segment(i, j, i, j), r[label]):
                            set_dir(i, j, n.debug_name.lower(), label)
        

    print('\n'.join(map(''.join, grid)))



def test3():
    # Test 3
    A = qcb.Segment(0, 1, 0, 3)
    B = qcb.Segment(1, 0, 1, 1)
    C = qcb.Segment(1, 2, 1, 2)
    D = qcb.Segment(1, 3, 1, 4)

    segments = [A,B,C,D]
    name_segments(segments)

    A.link_edges(segments)

    print_repr(segments)
    print('===================')
    new = A.left_merge()
    # for i, x in enumerate(new):
    #     x.debug_name = chr(ord('P') + i)
    name_segments(new, series='A')
    print_repr(new)


def testn(cells, n):
    cells1 = []
    for i, c in enumerate(cells):
        c1 = qcb.Segment(*c[:4])
        if len(c) > 4:
            c1.allocated = c[4]
        c1.debug_name = chr(ord('A') + i)
        cells1.append(c1)


    cells1[0].link_edges(cells1)
    print_latex(cells1, file=f"test{n}-1.tex")
    print('===================' * 4)

    new, confirm = cells1[0].left_merge()
    confirm(set())
    name_segments(new, "B")

    def neighbours(segs):
        out = set()
        for s in segs:
            out.update(s.left | s.right | s.below | s.above)
        return out

    n2 = set(new)
    while neighbours(n2) - n2:
        n2 |= neighbours(n2)

    n2 = sorted(n2, key=lambda x: (x.y_0, x.x_0))
    print_latex(n2, file=f"test{n}-2.tex")

    confirm_test(n2)

def confirm_test(output):
    all_cells = set.union(*map(lambda s: s.left | s.right | s.below | s.above, output)) | set(output)
    assert(len(all_cells) == len(output))
    cells_copy = []
    output_name = {}
    copy_name = {}
    for c in all_cells:

        copy = qcb.Segment(c.x_0, c.y_0, c.x_1, c.y_1)
        copy.allocated = c.allocated
        copy.debug_name = c.debug_name
        cells_copy.append(copy)
        if c.debug_name:
            output_name[c.debug_name] = c
            copy_name[c.debug_name] = copy
        
    cells_copy[0].link_edges(cells_copy)
    for n in output_name:
        cell = output_name[n]
        copy = copy_name[n]
        assert set(map(lambda s:s.debug_name, cell.above)) == set(map(lambda s:s.debug_name, copy.above)), print_repr([cell])
        assert set(map(lambda s:s.debug_name, cell.below)) == set(map(lambda s:s.debug_name, copy.below)), cell
        assert set(map(lambda s:s.debug_name, cell.left)) == set(map(lambda s:s.debug_name, copy.left)), cell
        assert set(map(lambda s:s.debug_name, cell.right)) == set(map(lambda s:s.debug_name, copy.right)), cell



# # Test 4
# cells = [
#     [1, 2, 1, 4],
#     [0, 2, 0, 2],
#     [0, 3, 0, 3],
#     [0, 4, 0, 4],
#     [1, 1, 1, 1],
#     [1, 5, 1, 5],
#     [1, 6, 1, 6],
#     [2, 0, 2, 0],
#     [2, 1, 3, 2, True],
#     [2, 3, 2, 3, True],
#     [2, 4, 2, 6],
#     [2, 7, 2, 7],
#     [3, 0, 3, 0],
#     [3, 3, 3, 3],
#     [3, 4, 3, 4],
#     [3, 5, 3, 5],
#     [3, 6, 3, 6],
#     [4, 1, 4, 1],
#     [4, 2, 4, 2]
# ]

# testn(cells, 4)


# cells = [
#     [0, 2, 0, 2],
#     [0, 3, 0, 3],
#     [0, 4, 0, 4],
#     [1, 1, 1, 1],
#     [1, 2, 1, 4],
#     [1, 5, 1, 5],
#     [1, 6, 1, 6],
#     [2, 0, 2, 0],
#     [2, 1, 2, 5],
#     [3, 0, 3, 0],
#     [3, 3, 3, 3],
#     [3, 4, 3, 4],
#     [3, 5, 3, 5],
#     [3, 6, 3, 6],
#     [3, 1, 4, 1],
#     [3, 2, 4, 2]
# ]
# testn(cells, 5)


# cells = [
#     [0, 0, 1, 3],
#     [2, 0, 2, 0],
#     [2, 1, 2, 1, True],
#     [2, 2, 2, 2, True],
#     [2, 3, 2, 3],
# ]
# testn(cells, 6)


cells = [
    [1,1,1,1],
    [0,1,0,1],
    [2,1,2,1],
    [3,1,3,1],
    [1,0,2,0],
    [1,2,2,2]
]


testn(cells, 10)
