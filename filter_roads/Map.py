import osmium

class MapReader(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.highway_nodes = []

    def node(self, n):
        pass

    def way(self, w):
        if w.tags.get("highway"):
            for n in w.nodes:
                self.highway_nodes.append(n.ref)

    def relation(self, r):
        pass

class MapWriter(osmium.SimpleHandler):
    def __init__(self, node_ids, writer):
        osmium.SimpleHandler.__init__(self)
        self.writer = writer
        self.highway_nodes = node_ids

    def node(self, n):
        if n.id in self.highway_nodes:
            self.writer.add_node(n)

    def way(self, w):
        if w.tags.get("highway"):
            self.writer.add_way(w)

    def relation(self, r):
        pass
