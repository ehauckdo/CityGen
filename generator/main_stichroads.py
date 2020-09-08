import os, sys
import random
import optparse
import copy
from Map import Cell
from lib.NZRenderer import render
from lib.NZMap import readFile
from handler import extract_data, write_data, insert_bounds
from preprocess import get_bounds, get_highways, get_way_nodes

# params: a way object and its list of nodes (to serve as pivot) and
#          a way object  and its list to be shifted in relation to the first
# returns: shifted second way and its nodes
def adjust(way1, nodes1, way2, nodes2):
    print("Merging w{} and w{}".format(way1.id, way2.id))
    #pivot_index = random.randint(0, len(nodes1)-1)
    pivot_index = random.choice([0, len(nodes1)-1])
    pivot = nodes1[pivot_index]
    print("pivot node way1", pivot.location[1],
                             pivot.location[0])
    #adjust_node_index = random.randint(0, len(nodes2)-1)
    adjust_node_index = random.choice([0, len(nodes2)-1])
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

def get_random_way(ways, nodes):
    selected_way = ways[random.choice(list(ways.keys()))]
    selected_nodes = get_way_nodes(selected_way, nodes)
    return copy.deepcopy(selected_way), copy.deepcopy(selected_nodes)

# Generate a road network by stringing multiple ways together
def generate_roads(ways, nodes, iterations=10):
    id_count = 0
    generated_ways, generated_nodes = {}, {}
    used_ways = []

    initial_way, initial_nodes = get_random_way(ways, nodes)
    used_ways.append(initial_way.id)
    initial_way.id = id_count
    id_count += 1
    generated_ways[initial_way.id] = initial_way
    for n in initial_nodes: generated_nodes[n.id] = n
    print("Initial way: {}".format(initial_way))

    for i in range(iterations):
        selected_way, selected_nodes = get_random_way(ways, nodes)
        used_ways.append(selected_way.id)
        selected_way.id = id_count
        id_count += 1

        pivot_way = random.choice(list(generated_ways.items()))[1]
        pivot_nodes = get_way_nodes(pivot_way, generated_nodes)

        print("Pivot way: {}, Selected way: {}".format(pivot_way.id, selected_way.id))

        selected_way, selected_nodes = adjust(pivot_way, pivot_nodes, selected_way, selected_nodes)
        generated_ways[selected_way.id] = selected_way

        for n in selected_nodes:
            generated_nodes[n.id] = n

    return generated_ways, generated_nodes, used_ways

def parseArgs(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="TX-To-TU.osm")
	return parser.parse_args()

def main():
    opt, args = parseArgs(sys.argv[1:])
    input = opt.filename
    output_file = "output_{}".format(input)

    nodes, ways = extract_data(input)
    highway_ways, highway_nodes = get_highways(ways, nodes)

    gen_ways, gen_nodes, used_ways_list = generate_roads(copy.deepcopy(highway_ways), copy.deepcopy(highway_nodes), 100)
    min_lat, min_lon, max_lat, max_lon = get_bounds(list(gen_nodes.values()))

    write_data(output_file, list(gen_nodes.values()), list(gen_ways.values()))
    insert_bounds(output_file, min_lat, min_lon, max_lat, max_lon)

    map = readFile(output_file)
    render(map)

if __name__ == '__main__':
    main()
