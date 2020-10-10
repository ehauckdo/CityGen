from Map import *
import osmium
import os

# params: the path to an osm file in the system
# returns: a list of node objects and a list of ways objects from the file
def extract_data(input):
    reader = Map()
    reader.apply_file(input)
    return reader.nodes, reader.ways

# params: a path/name for the file, a list of nodes and list of ways
# writes the osm XML file for the list of nodes and ways
# returns: None
def write_data(filename, nodes, ways):
    delete_file(filename)
    writer = osmium.SimpleWriter(filename)
    for n in nodes: writer.add_node(n)
    for w in ways:  writer.add_way(w)

    min_lat, min_lon, max_lat, max_lon = get_bounds(nodes)
    insert_bounds(filename, min_lat, min_lon, max_lat, max_lon)

def delete_file(filename):
    try:
        os.remove(filename) #clean file if exists
    except: pass

# params: a filename and the bounds of a osm file
# rewrites the osm XML file containing the bounds tag
# returns: None
def insert_bounds(filename, min_lat, min_lon, max_lat, max_lon):
    lines = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            lines.append(line)
    bounds = "  <bounds minlat=\"{}\" minlon=\"{}\" maxlat=\"{}\" maxlon=\"{}\"/>  \n"
    lines.insert(2, bounds.format(min_lat, min_lon, max_lat, max_lon))
    with open(filename, 'w') as f:
        for line in lines:
            f.write(line)

# Finds the bounding box that encompasses all the nodes
# in the list. The border coordinates are given an extra
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
