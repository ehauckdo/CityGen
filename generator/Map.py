import osmium
import copy

class Map(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.nodes = {}
        self.ways = {}

    def node(self, n):
        node = OSMNode(n)
        #print("Original: {} \nCopied:   {}".format(n, node))
        self.nodes[node.id] = node

    def way(self, w):
        way = OSMWay(w)
        #print("Original: {} \nCopied:   {}".format(w, way))
        self.ways[way.id] = way

    def relation(self, r):
        pass

    def get_ways_by_tag(self, tag):
        ways = []
        for id, w in self.ways.items():
            if tag in w.tags.keys():
                ways.append(w)
        return ways

    def get_highways(self):
        highway_ways = self.get_ways_by_tag("highway")
        highway_nodes = []
        for way in highway_ways:
            for node_id in way.nodes:
                highway_nodes.append(self.nodes[node_id])

        return highway_ways, highway_nodes

class OSMNode():
    def __init__(self, obj=None):
        if obj == None: return
        copyable_attributes = ['id', 'version','visible', 'changeset',
                               'timestamp', 'uid']#, 'location']
        for attr in copyable_attributes:
            setattr(self, attr, getattr(obj, attr))

        non_copyable_attributes = ['tags']
        for attr in non_copyable_attributes:
            copy = {}
            for key, value in getattr(obj, attr):
                copy[key] = value
            setattr(self, attr, copy)
        self.location = (obj.location.lon, obj.location.lat)
        #self.lon = osmNode.location.lon

    def __repr__(self):
        return str(self.__dict__)

class OSMWay():
    def __init__(self, obj=None):
        self.nodes = []
        if obj == None: return
        copyable_attributes = ('id', 'version','visible', 'changeset',
                               'timestamp', 'uid')
        for attr in copyable_attributes:
            setattr(self, attr, getattr(obj, attr))

        non_copyable_attributes = ['tags']
        for attr in non_copyable_attributes:
            copy = {}
            for key, value in getattr(obj, attr):
                copy[key] = value
            setattr(self, attr, copy)


        for n in obj.nodes:
            #self.nodes.append(NodeRef(n))
            self.nodes.append(n.ref)

    def __repr__(self):
        return ("w{}: nodes={} tags={}".format(self.id, self.nodes, self.tags))

    #def __repr__(self):
    #    return str(self.__dict__)

class Cell():
    def __init__(self, ways={}, nodes={}):
        self.ways = ways
        self.nodes = nodes
        self.r = None
        self.l = None
        self.u = None
        self.d = None
        if len(nodes) > 0:
            self.set_connectors()
        # print("Connectors defined: ")
        # print("u: {}".format(self.u.location))
        # print("d: {}".format(self.d.location))
        # print("r: {}".format(self.r.location))
        # print("l: {}".format(self.l.location))

    def set_ways_nodes(self, ways, nodes):
        self.ways = ways
        self.nodes = nodes
        self.set_connectors()
        print("u: {}".format(self.u.location))
        print("d: {}".format(self.d.location))
        print("r: {}".format(self.r.location))
        print("l: {}".format(self.l.location))

    def set_connectors(self):
        #lon, lat = self.nodes[0].location[0], self.nodes[0].location[1]
        n = self.nodes[list(self.nodes.keys())[0]]
        min_lat, min_lon, max_lat, max_lon = n, n, n, n

        # try to get only nodes belonging to roads
        nodes = []
        for w in self.ways.values():
            if "highway" in w.tags.keys():
                nodes.extend([self.nodes[x] for x in w.nodes])
        # default to any node if no roads are identified
        if len(nodes) == 0: nodes = self.nodes

        for n in nodes:
            if n.location[0] < min_lon.location[0]: min_lon = n
            if n.location[0] > max_lon.location[0]: max_lon = n
            if n.location[1] < min_lat.location[1]: min_lat = n
            if n.location[1] > max_lat.location[1]: max_lat = n
        self.r = max_lon
        self.l = min_lon
        self.u = max_lat
        self.d = min_lat
