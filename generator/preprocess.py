
# Finds the bounding box that encompasses all the nodes
# in the list. The border coordinates are given an extract
# margin to help with visualization.
# params: list of nodes, extra margin for the bounds
# returns: min_lat, min_lon, max_lat, max_lon
def get_bounds(nodes, ex=0.002):
    base_lon, base_lat = list(nodes)[0].location
    min_lat, min_lon, max_lat, max_lon = base_lat, base_lon, base_lat, base_lon
    for n in nodes:
        # there are two possible formating options for Location
        # this try catch block tries to handle both
        try:
            lon, lat = n.location[0], n.location[1]
        except:
            lon, lat = n.location.lon, n.location.lat

        if lon < min_lon: min_lon = lon
        if lon > max_lon: max_lon = lon
        if lat < min_lat: min_lat = lat
        if lat > max_lat: max_lat = lat
    #print(min_lat, min_lon, max_lat, max_lon, ex)
    return min_lat-ex, min_lon-ex, max_lat+ex, max_lon+ex

# params: list of way objects and list of node objects
# returns: list of dicts with "hihghway" tag, dict of nodes from those ways
def get_highways(ways, nodes):
    highway_ways = {}
    highway_nodes = {}
    for way in get_ways_by_tag(ways, "highway"):
        highway_ways[way.id]  = way

    for way in highway_ways.values():
        for node_id in way.nodes:
            highway_nodes[node_id] = nodes[node_id]

    return highway_ways, highway_nodes

# params: a list of way objcets, a certain tag (string)
# returns: a list of ways objects containing the tag
def get_ways_by_tag(ways, tag):
    tagged_ways = []
    for id, w in ways.items():
        if "highway" in w.tags.keys():
            tagged_ways.append(w)
    return tagged_ways

# params: a way object, a list of all nodes in an osm filename
# returns: list of nodes belonging to the way object
def get_way_nodes(way, nodes):
    way_nodes = []
    for n_id in way.nodes:
        way_nodes.append(nodes[n_id])
    return way_nodes
