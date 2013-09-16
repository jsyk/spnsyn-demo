import ftl.dbgtim as dbgtim


class TarjanSCC:
    """ Tarjan's strongly connected components algorithm
        http://en.wikipedia.org/wiki/Tarjan%E2%80%99s_strongly_connected_components_algorithm
    """

    def __init__(self):
        # INPUT: list of all nodes in the graph
        self.nodes = []
        # OUTPUT: list of components. Each component is a list of nodes.
        self.sccl = []

    def run_on(self, nodes):
        """ Given a set of nodes, compute a list of lists of strongly connected components (SCC).
            [ [n1, n2, ...],    # scc 1
              [n3, n4, ...],    # scc 2
              ...
            ]
        """
        _tim = dbgtim.Timing('TarjanSCC')
        self.nodes = nodes
        self.index = 0
        self.S = []
        for v in self.nodes:
            if v.tarjan_index is None:
                self.strongconnect(v)
        _tim.fin()
        return self.sccl

    def strongconnect(self, v):
        # Set the depth index for v to the smallest unused index
        v.tarjan_index = self.index
        v.tarjan_lowlink = self.index
        self.index += 1
        self.S.append(v)

        # Consider successors of v
        for w in v.succ():
            if w.tarjan_index is None:
                # Successor w has not yet been visited; recurse on it
                self.strongconnect(w)
                v.tarjan_lowlink = min(v.tarjan_lowlink, w.tarjan_lowlink)
            else:
                if w in self.S:
                    # Successor w is in stack S and hence in the current SCC
                    v.tarjan_lowlink = min(v.tarjan_lowlink, w.tarjan_index)

        # If v is a root node, pop the stack and generate an SCC
        if v.tarjan_lowlink == v.tarjan_index:
            # start a new strongly connected component
            scc = []
            while True:
                w = self.S.pop()
                scc.append(w)
                if w == v:
                    break
            # output the current strongly connected component
            self.sccl.append(scc)


class TopoSort:
    """ Topological sort of an acyclic graph using DFS.
        It seems to have been first described in print by Tarjan (1976). ;-)
    """
    def __init__(self):
        self.tslist = []        # OUTPUT: top-sorted list
        self.no_mark = set()    # INPUT: set of (unmarked) nodes
        self.tmp_mark = set()
        self.perm_mark = set()

    def run_on(self, nodes):
        self.no_mark = set(nodes)
        while self.no_mark:
            n = self.no_mark.pop()
            self.visit(n)

        return self.tslist

        # L ← Empty list that will contain the sorted nodes
        # while there are unmarked nodes do
        #     select an unmarked node n
        #     visit(n) 

    def visit(self, n):
        if n in self.tmp_mark:
            assert False, "Graph is not acyclic!"
        if n not in self.perm_mark:
            self.tmp_mark.add(n)
            for m in n.pred():
                self.visit(m)
            self.tmp_mark.remove(n)
            self.perm_mark.add(n)
            self.tslist.append(n)

        # if n has a temporary mark then stop (not a DAG)
        # if n is not marked (i.e. has not been visited yet) then
        #     mark n temporarily
        #     for each node m with an edge from n to m do
        #         visit(m)
        #     mark n permanently
        #     add n to L

