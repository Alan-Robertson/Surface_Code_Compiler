import numpy as np
import queue
from qcb import SCPatch
from typing import *
from utils import log

class PatchGraphNode():

    INITIAL_LOCK_STATE = object()

    def __init__(self, graph, i, j):
        self.graph = graph
        self.x = i
        self.y = j
        self.state = None
        self.lock = self.INITIAL_LOCK_STATE
    
    def set_underlying(self, state):
        self.state = state

    def adjacent(self):
        return self.graph.adjacent(self.x, self.y)

    def __gt__(self, *args):
        return 1

    def __repr__(self):
        return str('[{}, {}]'.format(self.x, self.y))

    def __str__(self):
        return self.__repr__()

    def cost(self):
        return 1

    def active_gates(self):
        return self.graph.active_gates()

    def valid_edge(self, other_patch, edge):
        return self.state.valid_edge(other_patch.state, edge)

    def lock(self, dag):
        # Gate has completed and is no longer active
        if self.locking_dag not in self.active_gates():
            self.locking_dag = dag
            return True

        if self.locking_dag is dag:
            return True

        return False 

class PatchGraph():
    def __init__(self, shape, environment):
        self.graph = np.array([[PatchGraphNode(self, j, i) for i in range(shape[1])] for j in range(shape[0])])
        self.shape = shape
        self.time = 0
        self.locks: Dict[int, Set[ANC]] = {}
        self.environment = environment

    def __getitem__(self, *args) -> GraphNode:
        return self.graph.__getitem__(*args)

    def lock(self, nodes: List[GraphNode], duration: int, inst):
        anc = ANC(nodes, self.time + duration, inst)
        anc.start()
        self.locks[anc.expiry] = self.locks.get(anc.expiry, set()) | {anc}
        log(f"lock {anc=}")
        return anc

    def active_gates(self):
        return self.environment.active_gates

    
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
                if (i == end and current != start) or i.state == SCPatch.ROUTE:
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
