import numpy as np
import queue
from qcb import SCPatch
from typing import *
from utils import log

class ANC():
    def __init__(self, nodes, expiry, inst):
        self.nodes = nodes
        self.expiry = expiry
        self.inst = inst

    def start(self):
        for s in self.nodes:
            s.anc = self

    def end(self):
        for s in self.nodes:
            s.anc = None
    
    def __repr__(self):
        return f"ANC({repr(self.nodes)}, exp={self.expiry}, inst={self.inst})"

class GraphNode():
    def __init__(self, 
                 graph,
                 i,
                 j,
                #  underlying: SCPatch,
                 data=None, 
                 anc=None,
                 ):
        self.graph = graph
        self.x = i
        self.y = j
        self.data = None
        self.anc = None
        self.underlying = None
    
    def set_underlying(self, type):
        self.underlying = type

    def adjacent(self):
        return self.graph.adjacent(self.x, self.y)

    def __gt__(self, *args):
        return 1

    def in_use(self) -> bool:
        return self.data or self.anc
    def __repr__(self):
        return str('[{}, {}]'.format(self.x, self.y))
    def __str__(self):
        return self.__repr__()

    def cost(self):
        return 1

class Graph():
    def __init__(self, shape):
        self.graph = np.array([[GraphNode(self, j, i) for i in range(shape[1])] for j in range(shape[0])])
        self.shape = shape
        self.time = 0
        self.locks: Dict[int, Set[ANC]] = {}

    def __getitem__(self, *args) -> GraphNode:
        return self.graph.__getitem__(*args)

    def lock(self, nodes: List[GraphNode], duration: int, inst):
        anc = ANC(nodes, self.time + duration, inst)
        anc.start()
        self.locks[anc.expiry] = self.locks.get(anc.expiry, set()) | {anc}
        log(f"lock {anc=}")
        return anc
    
    def advance(self):
        if not self.locks:
            raise Exception('Routing failed, no available gates to route')
        time_next = min(self.locks)
        self.time = time_next
        completed = self.locks[self.time]
        for anc in completed:
            anc.end()
        del self.locks[self.time]
        return completed

    
    def step(self, inc=1):
        self.time += inc
        completed = set()
        while self.locks and min(self.locks) < self.time:
            completed.update(self.locks[self.time])
            for anc in self.locks[self.time]:
                anc.end()
            del self.locks[self.time]
        return completed

    def adjacent(self, i, j):
        opt = []
        if i + 1 < self.shape[0]:
            opt.append([i + 1, j])
        if i - 1 >= 0:
            opt.append([i - 1, j])
        
        if j + 1 < self.shape[1]:
            opt.append([i, j + 1])
        if j - 1 >= 0:
            opt.append([i, j - 1])

        for i in opt:
            if not self[tuple(i)].in_use():
                yield self[tuple(i)]
        return
   
    def path(self, start, end, heuristic=None):
        if start.in_use() or end.in_use():
            return []
        
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
                if (i == end and current != start) or i.underlying == SCPatch.ROUTE:
                    cost = path_cost[current] + i.cost()
                    if i not in path_cost or cost < path_cost[i]:
                        path_cost[i] = cost
                        frontier.put((cost + heuristic(i, end), i))
                        path[i] = current
        else:
            return []

        def traverse(path, end):
            next_end = path[end]
            if next_end is not None:
                return [next_end] + traverse(path, next_end)
            return []
        return traverse(path, end)[::-1] + [end]

    @staticmethod
    def heuristic(a, b):
        return abs(a.x - b.x) + 1.01 * abs(a.y - b.y)
