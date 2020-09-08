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
    try:
        os.remove(filename) #clean file if exists
    except: pass
    writer = osmium.SimpleWriter(filename)
    for n in nodes: writer.add_node(n)
    for w in ways:  writer.add_way(w)

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
