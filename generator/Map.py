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
            if "highway" in w.tags.keys():
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
    def __init__(self, obj):
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
    def __init__(self, obj):
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

        self.nodes = []
        for n in obj.nodes:
            #self.nodes.append(NodeRef(n))
            self.nodes.append(n.ref)

    def __repr__(self):
        return ("w{}: nodes={} tags={}".format(self.id, self.nodes, self.tags))

    #def __repr__(self):
    #    return str(self.__dict__)

class NodeRef():
    def __init__(self, obj):
        self.ref = obj.ref
        self.location = obj.location
        self.x = obj.x
        self.y = obj.y
    def __repr__(self):
        return str(self.ref)
