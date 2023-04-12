import numpy as np
import queue

class ANC():
    def __init__(self, nodes, time):
        self.nodes = nodes
        self.start = start
        self.end = end

    def start(self):
        for i in nodes:
            nodes.anc = True
    def end(self):
        for i in nodes:
            nodes.anc = False

class GraphNode():
    def __init__(self, 
                 graph,
                 i,
                 j,
                 data=False, 
                 anc=False
                 ):
        self.graph = graph
        self.x = i
        self.y = j
        self.data = data
        self.anc = anc
    
    def adjacent(self):
        return self.graph.adjacent(self.x, self.y)

    def __gt__(self, *args):
        return 1

    def in_use(self):
        return self.data or self.anc
    def __repr__(self):
        return str('[{}, {}]'.format(self.x, self.y))
    def __str__(self):
        return self.__repr__()

    def cost(self):
        return 1

class Graph():
    def __init__(self, size):
        self.graph = np.array([[GraphNode(self, j, i) for i in range(size)] for j in range(size)])
        self.size = size

    def __getitem__(self, *args):
        return self.graph.__getitem__(*args)

    def adjacent(self, i, j):
        opt = []
        if i + 1 == self.size:
            opt.append([i - 1, j])
        else:
            opt.append([i + 1, j])
        if i - 1 >= 0:
            opt.append([i - 1, j])
        
        if j + 1 == self.size:
            opt.append([i, j - 1])
        else:
            opt.append([i, j + 1])
        if j - 1 >= 0:
            opt.append([i, j - 1])

        for i in opt:
            if not self[tuple(i)].in_use():
                yield self[tuple(i)]
        return
   
    def path(self, start, end, heuristic=None):

        if heuristic is None:
            heuristic = self.heuristic

        frontier = queue.PriorityQueue()
        frontier.put((0, start))
        
        path = {}
        path_cost = {}
        path[start] = None
        path_cost[start] = 0

        while not frontier.empty():
            current = frontier.get()[1]

            if current == end:
                break

            for i in current.adjacent():
                cost = path_cost[current] + i.cost()
                if i not in path_cost or cost < path_cost[i]:
                    path_cost[i] = cost
                    frontier.put((cost + heuristic(i, end), i))
                    path[i] = current

        def traverse(path, end):
            next_end = path[end]
            if next_end is not None:
                return [next_end] + traverse(path, next_end)
            return []
        return traverse(path, end)[::-1] + [end]

    @staticmethod
    def heuristic(a, b):
        return abs(a.x - b.x) + 1.01 * abs(a.y - b.y)
