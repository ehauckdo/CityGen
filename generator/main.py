import os
import osmium
import random
import copy
from Map import *
from lib.NZRenderer import render
from lib.NZMap import readFile
random.seed(1)

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

# params: the path to an osm file in the system
# returns: a list of node objects and a list of ways objects from the file
def extract_data(input):
    reader = Map()
    reader.apply_file(input)
    return reader.nodes, reader.ways

# params: a path/name for the file, a list of nodes and list of ways
# writes the osm XML file for the list of nodes and ways
# returns: None
def write(filename, nodes, ways):
    try:
        os.remove(filename) #clean file if exists
    except: pass
    writer = osmium.SimpleWriter(filename)
    for n in nodes: writer.add_node(n)
    for w in ways:  writer.add_way(w)

# params: list of way objects and list of node objects
# returns: list of ways with "hihghway" tag, list of nodes from those ways
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

# params: list of nodes
# returns: min_lat, min_lon, max_lat, max_lon
def get_bounds(nodes):
    from decimal import Decimal
    min_lat, min_lon, max_lat, max_lon = Decimal('Inf'), Decimal('Inf'), 0, 0
    for n in nodes:
        try:
            if n.location[0] < min_lon: min_lon = n.location[0]
            if n.location[0] > max_lon: max_lon = n.location[0]
            if n.location[1] < min_lat: min_lat = n.location[1]
            if n.location[1] > max_lat: max_lat = n.location[1]
        except:
            if n.location.lon < min_lon: min_lon = n.location.lon
            if n.location.lon > max_lon: max_lon = n.location.lon
            if n.location.lat < min_lat: min_lat = n.location.lat
            if n.location.lat > max_lat: max_lat = n.location.lat
    # add some extra to the bounds to improve visualization
    ex = 0.002
    return min_lat-ex, min_lon-ex, max_lat+ex, max_lon+ex

# building...
def generate(ways, nodes, iterations=10):
    id_count = 0
    generated_ways = {}
    generated_nodes = {}
    used_ways = []

    def select(ways, nodes):
        selected_way = ways[random.choice(list(ways.keys()))]
        selected_nodes = get_way_nodes(selected_way, nodes)
        return copy.deepcopy(selected_way), copy.deepcopy(selected_nodes)

    initial_way, initial_nodes = select(ways, nodes)
    used_ways.append(initial_way.id)
    initial_way.id = id_count
    id_count += 1
    generated_ways[initial_way.id] = initial_way
    for n in initial_nodes: generated_nodes[n.id] = n
    print("Initial way: {}".format(initial_way))

    for i in range(iterations):
        selected_way, selected_nodes = select(ways, nodes)
        used_ways.append(selected_way.id)
        selected_way.id = id_count
        id_count += 1

        pivot_way = random.choice(list(generated_ways.items()))[1]
        pivot_nodes = get_way_nodes(pivot_way, generated_nodes)

        print("Pivot way: {}, Selected way: {}".format(pivot_way.id, selected_way.id))

        selected_way, selected_nodes = adjust(pivot_way, pivot_nodes, selected_way, selected_nodes)
        print("Current nodes:")
        for key, value in generated_nodes.items():
            print(key, value)
        print("Selected nodes:")
        for n in selected_nodes:
            print(n.id, n)

        generated_ways[selected_way.id] = selected_way

        for n in selected_nodes:
            generated_nodes[n.id] = n

    return generated_ways, generated_nodes, used_ways

# params: a way object and its list of nodes (to serve as pivot) and
#          a way object  and its list to be shifted in relation to the first
# returns: shifted second way and its nodes
def adjust(way1, nodes1, way2, nodes2):
    print("Merging w{} and w{}".format(way1.id, way2.id))
    pivot_index = random.randint(0, len(nodes1)-1)
    pivot = nodes1[pivot_index]
    print("pivot node way1", pivot.location[1],
                             pivot.location[0])
    adjust_node_index = random.randint(0, len(nodes2)-1)
    adjust_node = nodes2[adjust_node_index]
    print("adjust node way2", adjust_node.location[1],
                              adjust_node.location[0])
    lat_adjust = pivot.location[1] - adjust_node.location[1]
    lon_adjust = pivot.location[0] - adjust_node.location[0]

    way2.nodes = []

    nodes2.pop(adjust_node_index)
    for n in nodes2:
        n.location = (n.location[0]+lon_adjust, n.location[1]+lat_adjust)
        way2.nodes.append(n.id)

    way2.nodes.insert(adjust_node_index, pivot.id)
    nodes2.insert(adjust_node_index, pivot)

    return way2, nodes2

input_file = "portland.osm"
output_file = "output.osm"

nodes, ways = extract_data(input_file)
highway_ways = get_ways_by_tag(ways, "highway")
highway_ways, highway_nodes = get_highways(ways, nodes)

gen_ways, gen_nodes, used_ways_list = generate(copy.deepcopy(highway_ways), copy.deepcopy(highway_nodes), 40)
min_lat, min_lon, max_lat, max_lon = get_bounds(list(gen_nodes.values()))

write(output_file, list(gen_nodes.values()), list(gen_ways.values()))
insert_bounds(output_file, min_lat, min_lon, max_lat, max_lon)

used_ways = {}
for w_id in used_ways_list:
    used_ways[w_id] = ways[w_id]

used_nodes = {}
for way in used_ways.values():
    for n_id in way.nodes:
        used_nodes[n_id] = nodes[n_id]

min_lat, min_lon, max_lat, max_lon = get_bounds(list(used_nodes.values()))

write("unmerged.osm", list(used_nodes.values()), list(used_ways.values()))
insert_bounds("unmerged.osm", min_lat, min_lon, max_lat, max_lon)

map = readFile(output_file)
render(map)
