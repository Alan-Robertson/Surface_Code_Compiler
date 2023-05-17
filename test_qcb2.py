import qcb


def setup():
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

# Test 1
# a,b,c,d = setup()
# print(a.edges())
# x = a.horizontal_merge(b)
# print(x)
# print(c)
# print(d)
# print(x.edges())

# Test 2
# p = qcb.Segment(0, 0, 2, 2)
# x = qcb.Segment(3, -1, 3, 1)
# x.test = "X"
# p.right.add(x)
# new2 = p.split(1, 1, 1, 1)
# p.confirm_split(new2)
# for s in new2:
#     s.test = chr(ord('A') + s.x_0 + s.y_0 * 3)
# for s in new2:
#     print(s.test, s, end=" {")
#     for label, ns in s.edges().items():
#         print(f"'{label}': {set(map(lambda x:x.test, ns))}", end=", ")
#     print('}')

# print(next(iter(new2[7].right)).left)



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
        grid[y][x] = c[0]
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
                set_cell(i, j, s.test)
                for label, edge in s.edges().items():
                    for n in edge:
                        if n.seg_adjacent(n, qcb.Segment(i, j, i, j), r[label]):
                            set_dir(i, j, n.test.lower(), label)
        

    print('\n'.join(map(''.join, grid)))


# Test 3
# A = qcb.Segment(0, 1, 0, 3)
# A.test = 'A'
# B = qcb.Segment(1, 0, 1, 1)
# B.test = 'B'
# C = qcb.Segment(1, 2, 1, 2)
# C.test = 'C'
# D = qcb.Segment(1, 3, 1, 4)
# D.test = 'D'

# A.link_edges([A,B,C,D])

# print_repr([A,B,C,D])
# print('===================')
# new = A.left_merge()
# for i, x in enumerate(new):
#     x.test = chr(ord('P') + i)

# print_repr(new)

# Test 4
cells = [
    [0, 2, 0, 2],
    [0, 3, 0, 3],
    [0, 4, 0, 4],
    [1, 1, 1, 1],
    [1, 2, 1, 4],
    [1, 5, 1, 5],
    [1, 6, 1, 6],
    [2, 0, 2, 0],
    [2, 1, 3, 2],
    [2, 3, 2, 3],
    [2, 4, 2, 6],
    [2, 7, 2, 7],
    [3, 0, 3, 0],
    [3, 3, 3, 3],
    [3, 4, 3, 4],
    [3, 5, 3, 5],
    [3, 6, 3, 6],
    [4, 1, 4, 1],
    [4, 2, 4, 2]
]
# Test5
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

cells1 = []
for i, c in enumerate(cells):
    c1 = qcb.Segment(*c)
    c1.test = chr(ord('A') + i)
    cells1.append(c1)


cells1[0].link_edges(cells1)
print_repr(cells1)
print('===================' * 4)

new = cells1[4].left_merge()
new.sort(key=lambda x: x.y_0)

for i, c in enumerate(new):
    c.test = chr(ord('T') + i) + '`'

def neighbours(segs):
    out = set()
    for s in segs:
        out.update(s.left | s.right | s.below | s.above)
    return out

n2 = sorted(set(new) | neighbours(new), key=lambda x: (x.y_0, x.x_0))
print_repr(n2)

for s in sorted(n2, key=lambda x:x.test):
    print(s.test, s, end=" {")
    for label, ns in s.edges().items():
        print(f"'{label}': {set(map(lambda x:x.test, ns))}", end=", ")
    print('}')