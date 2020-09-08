import os, sys
import osmium
import random
import copy
import optparse
from Map import *
from lib.NZRenderer import render
from lib.NZMap import readFile
from preprocess import get_highways, get_bounds, get_way_nodes
from handler import extract_data, write_data, insert_bounds
#random.seed(9)

i_id = 0

# params: the entire list of ways and nodes of an OSM area
# returns: a dict containing all the nodes that are part of an intersection_nodes
#          in the format node_id -> [way_id1, way_id2...]
def get_intersection_nodes(ways, nodes):
    highway_ways, highway_nodes = get_highways(ways, nodes)
    nodes_dict = {}

    for n in highway_nodes:
        nodes_dict[n] = []

    for way in highway_ways:
        for n in highway_ways[way].nodes:
            nodes_dict[n].append(way)

    intersection_nodes = {}
    for node_id, ways in nodes_dict.items():
        if len(ways) > 1:
            print(node_id, " belongs to ", ways)
            intersection_nodes[node_id] = ways
    return intersection_nodes

def angleFromCoordinate(lat1, long1, lat2, long2):
    import math
    dLon = (long2 - long1)

    y = math.sin(dLon) * math.cos(lat2);
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon);

    brng = math.atan2(y, x);
    return brng

    brng = math.degrees(brng);
    brng = (brng + 360) % 360;
    #brng = 360 - brng;

    return brng

def create_node(lon, lat):
    new_p_loc = osmium.osm.Location(lon, lat)
    new_p = osmium.osm.mutable.Node(location=new_p_loc)
    global i_id
    new_p.id = i_id
    i_id += 1
    return new_p

def generate_building(n1, n2, nodes, ways):

    building = osmium.osm.mutable.Way()
    global i_id
    building.id = i_id
    i_id += 1
    ways[building.id] = building

    new_n1 = create_node(n1.location[0]*1.000001, n1.location[1])
    nodes[new_n1.id] = new_n1

    new_n2 = create_node(n1.location[0]*1.000002, n1.location[1])
    nodes[new_n2.id] = new_n2

    new_n3 = create_node(n2.location[0]*1.000002, n2.location[1])
    nodes[new_n3.id] = new_n3

    new_n4 = create_node(n2.location[0]*1.000001, n2.location[1])
    nodes[new_n4.id] = new_n4

    building.nodes = [new_n1.id,new_n2.id,new_n3.id,new_n4.id,new_n1.id]
    building.tags = {"building":"house"}

    building2 = osmium.osm.mutable.Way()
    building2.id = i_id
    i_id += 1
    ways[building2.id] = building2
    new_n1 = create_node(n1.location[0]*0.999999, n1.location[1])
    nodes[new_n1.id] = new_n1

    new_n2 = create_node(n1.location[0]*0.999998, n1.location[1])
    nodes[new_n2.id] = new_n2

    new_n3 = create_node(n2.location[0]*0.999998, n2.location[1])
    nodes[new_n3.id] = new_n3

    new_n4 = create_node(n2.location[0]*0.999999, n2.location[1])
    nodes[new_n4.id] = new_n4

    building2.nodes = [new_n1.id,new_n2.id,new_n3.id,new_n4.id,new_n1.id]
    building2.tags = {"building":"house"}

def compute_slope(n1, n2):
    # a division by zero here indicates vertical line
    try:
        slope = (n2.location[1]-n1.location[1])/(n2.location[0]-n1.location[0])
    except ZeroDivisionError:
        print("ERROR: vertical line")
        sys.exit()
    return slope

def parseArgs(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="small_parcel.osm")
	return parser.parse_args()

def main():
    global i_id
    opt, args = parseArgs(sys.argv[1:])
    input_file = opt.filename
    output_file = "output_{}".format(input_file)

    nodes, ways = extract_data(input_file)
    highway_ways, highway_nodes = get_highways(ways, nodes)

    if len(highway_ways) == 0: sys.exit()

    # Trim down the ways down to only 1 so we can visualize better
    random_way_id = random.choice(list(highway_ways.keys()))
    random_way = highway_ways[random_way_id]

    highway_ways = {random_way_id:random_way}
    selected_nodes = {}
    for n in random_way.nodes:
        selected_nodes[n] = highway_nodes[n]

    highway_nodes = selected_nodes

    # Iterate through every pair of nodes in a way
    # and place buildings in both sides of them
    nodes = list(highway_nodes.values())
    for i in range(len(nodes)-1):
        n1 = nodes[i]
        n2 = nodes[i+1]
        print("Node1: ", nodes[i].location)
        print("Node2: ", nodes[i+1].location)

        new_lon = n1.location[0]*1.00001
        new_lat = n1.location[1]

        new_location = (new_lon, new_lat)
        new_node = osmium.osm.mutable.Node(location=new_location)
        new_node.id = i_id
        i_id += 1

        generate_building(n1, n2, highway_nodes, highway_ways)

    min_lat, min_lon, max_lat, max_lon = get_bounds(list(highway_nodes.values()))

    write_data(output_file, list(highway_nodes.values()), list(highway_ways.values()))
    insert_bounds(output_file, min_lat, min_lon, max_lat, max_lon)

    map = readFile(output_file)
    render(map)

if __name__ == '__main__':
    main()

# # Find intersection points as ways sharing the same node
# # Simplifies the whole graph with only the intersection nodes
# intersection_nodes = get_intersection_nodes(ways, nodes)
# for node_id, ways in intersection_nodes.items():
#     print(node_id, " belongs to ", ways)
#
# def update_highways(highway_ways, intersection_nodes):
#     new_ways = {}
#     for id, way in highway_ways.items():
#         way.nodes = []
#         new_ways[id] = way
#     for node_id, ways in intersection_nodes.items():
#         for way_id in ways:
#             new_ways[way_id].nodes.append(node_id)
#
#     return new_ways
#
# print("==========Highways Before Update==========")
# for id, way in highway_ways.items():
#     print(id, way.nodes)
#
# highway_ways = update_highways(highway_ways, intersection_nodes)
#
# print("==========Highways After Update==========")
# for id, way in highway_ways.items():
#     print(id, way.nodes)
