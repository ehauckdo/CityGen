import os, sys
import random
import copy
import handler
import optparse
import osmnx as ox
import networkx as nx
import numpy as np
import trigonometry as trig
import matplotlib.pyplot as plt
import logging
import line
import math
import time
import helper
from Node import Node
from lib.NZRenderer import render
from lib.NZMap import readFile
from Map import Cell, OSMWay, OSMNode
from preprocess import get_bounds
import building

total = 0
created = 0

tic = time.perf_counter()
logging.basicConfig(level=logging.DEBUG, filemode='w', filename='main.log')
#logging.getLogger().addHandler(logging.StreamHandler())

def elapsed(string=None):
    toc = time.perf_counter()
    return "{:.2f}s".format(toc-tic)

def log(string, level="INFO", show_time=True):
    logstring = ""
    if show_time: logstring += elapsed()
    logstring += " {}".format(string)
    if level == "INFO": logging.info(logstring)
    if level == "DEBUG": logging.debug(logstring)

def save_data(filename, ways, nodes):
    handler.write_data(filename, nodes, ways)
    min_lat, min_lon, max_lat, max_lon = get_bounds(nodes)
    handler.insert_bounds(filename, min_lat, min_lon, max_lat, max_lon)

def plot(nodes, ways, tags=None):

    G = nx.Graph()
    pos = {}

    for w_id, way in ways.items():
        parse_way = False
        if tags == None:
            parse_way = True
        else:
            for k, v in tags:
                if k in way.tags and (way.tags[k] == v or v == None):
                    parse_way = True
                    break

        if parse_way == False:
            continue

        log("Way accepted into plot with tags: {}".format(way.tags), "DEBUG")
        for i in range(len(way.nodes)-1):
            n1, n2 = way.nodes[i], way.nodes[i+1]
            if n1 not in pos:
                G.add_node(n1, node_color=nodes[n1].color)
                pos[n1] = nodes[n1].location
            if n2 not in pos:
                G.add_node(n2, node_color=nodes[n2].color)
                pos[n2] = nodes[n2].location
            G.add_edge(n1, n2, width=1, edge_color=way.color)

    options = { "node_size": 20, "linewidths": 0}
    edges = G.edges()
    node_color = nx.get_node_attributes(G,'node_color').values()
    edge_width = [G[u][v]['width'] for u,v in edges]
    edge_color = [G[u][v]['edge_color'] for u,v in edges]
    nx.draw(G, pos, node_color=node_color, edge_color=edge_color, width=edge_width, **options)
    plt.show()

def get_cycles(input_file):
    G = ox.graph.graph_from_xml(input_file, simplify=False, retain_all=True)
    H = nx.Graph(G) # make a simple undirected graph from G

    cycles = nx.cycles.cycle_basis(H) # I think a cycle basis should get all the neighborhoods, except
                                      # we'll need to filter the cycles that are too small.
    return cycles

def get_buildings_data(ways, nodes):
    number_edges = {}
    min_dist, max_dist = [], []

    for way_id, way in ways.items():
        if "building" in way.tags.keys():
            try:
                # -1 accounts for the extra repeated node in a way
                number_edges[len(way.nodes)-1] += 1
            except:
                number_edges[len(way.nodes)-1] = 1
                #number_edges.append(len(way.nodes))
            distances = []
            for i in range(len(way.nodes)-1):
                n1 = nodes[way.nodes[i]]
                n2 = nodes[way.nodes[i+1]]
                x1, y1 = n1.location[0], n1.location[1]
                x2, y2 = n2.location[0], n2.location[1]
                distances.append(trig.dist(x1, y1, x2, y2))
            distances.sort()
            min_dist.append(distances[0])
            max_dist.append(distances[-1])
    try:
        avg_min, avg_max = np.average(min_dist), np.average(max_dist)
        std_min, std_max = np.std(min_dist), np.std(max_dist)
    except:
        avg_min, avg_max = 0, 0
        std_min, std_max = 0, 0
    return number_edges, avg_min, std_min, avg_max, std_max

def get_cycles_data(nodes, cycles):
    areas = []
    log("Scanning cycles to fetch area...", "DEBUG")
    for c in cycles:
        points = [n.location for n_id, n in nodes.items() if n_id in c]
        area = helper.get_area(points)
        log("Area of cycle: {}".format(area), "DEBUG")
        areas.append(area)
    return min(areas), max(areas), np.average(areas), np.std(areas)

def remove_cycles_type(nodes, cycles, type):
    # remove cycles that do not represent streets
    for i in range(len(cycles)-1, -1, -1):
        cycles[i].append(cycles[i][0])
        for n_id in cycles[i]:
            if nodes[n_id].type != type:
                cycles.pop(i)
                break
    return cycles

def remove_nonempty_cycles(nodes, cycles, matrix, lon_range, lat_range):
    empty_cycles_count = 0
    empty_cycles = []
    for cycle in cycles:
        log("Nodes in Cycle:", "DEBUG")
        for n_id in cycle:
            log("{} - {}".format(n_id, nodes[n_id].location), "DEBUG")

        min_lat, min_lon, max_lat, max_lon = get_bounds([nodes[x] for x in cycle])
        log("Bounds of cycle: {}".format((min_lat, min_lon, max_lat, max_lon)))
        x_min, y_min, x_max, y_max = helper.nodes_in_area(min_lat, min_lon,
                                     max_lat, max_lon, lat_range, lon_range)
        detected_nodes = {}
        for x in range(x_min, x_max+1):
            for y in range(y_min, y_max+1):
                node_ids_list = matrix[x][y]
                for n_id in node_ids_list:
                    detected_nodes[n_id] = nodes[n_id]

        log("Detected nodes: ", "DEBUG")
        for n_id, n in detected_nodes.items():
            log("{} - {}".format(n_id, n.location), "DEBUG")

        cycle_polygon = [n.location for n in [nodes[id] for id in cycle]]

        for n_id in cycle[:-1]:
           log("Attempting to delete {} from detected_nodes".format(n_id), "DEBUG")
           del detected_nodes[n_id]

        log("Cycle polygon: {}".format(cycle_polygon))
        for id, n in detected_nodes.items():
           lon, lat = n.location
           if trig.point_inside_polygon(lon, lat, cycle_polygon):
               log("Node inside cycle detected!")
               break
        else:
            empty_cycles_count += 1
            empty_cycles.append(cycle)

    return empty_cycles, empty_cycles_count

def parseArgs(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="TX-To-TU.osm")
	return parser.parse_args()

def main():

    os.system('clear')
    opt, args = parseArgs(sys.argv[1:])
    input = opt.filename
    output = "output_{}".format(input)
    log("Reading OSM file '{}'...".format(input))

    nodes, ways = handler.extract_data(input)
    log("Data read sucessfully.")
    log("Total nodes: {}".format(len(nodes.values())))
    log("Total ways: {}".format(len(ways.values())))

    min_lat, min_lon, max_lat, max_lon = get_bounds(nodes.values())
    matrix, lon_range, lat_range = helper.split_into_matrix(min_lat,
                                            min_lon, max_lat, max_lon, nodes)

    number_edges, min_dist, std_min, max_dist, std_max = get_buildings_data(
                                                                   ways, nodes)
    edge_data = {"number_edges": number_edges,
            "min_dist": min_dist,
            "std_min": std_min,
            "max_dist": max_dist,
            "std_max": std_max}

    log("Building data collected succesfully.")
    log("Building data: min_dist:{:f}, std_min:{:f}".format(min_dist, std_min) +
        ", max_dist: {:f}, std_max:{:f}".format(max_dist, std_max))

    # preprocess nodes, add some properties to them
    helper.set_node_type(ways, nodes)
    helper.color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    helper.color_ways(ways, nodes, ways_colors, nodes_colors, default="black")
    log("Nodes preprocessed sucessfully.")

    # get all cycles in the graph
    cycles = get_cycles(input)
    total_cycles = len(cycles)

    cycles = remove_cycles_type(nodes, cycles, "highway")
    highway_cycles = len(cycles)
    log("{}/{} highway cycles were identified.".format(highway_cycles,
                                                    total_cycles))

    min_area, max_area, avg_area, std_area = get_cycles_data(nodes, cycles)
    cycle_data = {"min_area": min_area,
             "max_area": max_area,
             "avg_area": avg_area,
             "max_dist": max_dist,
             "std_area": std_area}
    log(cycle_data)

    cycles, empty_count = remove_nonempty_cycles(nodes, cycles, matrix, lon_range, lat_range)

    for cycle in cycles:
        #try:
        n, a = building.generate_in_cycle([nodes[x] for x in cycle], ways)
        nodes.update(n)
        ways.update(a)
       # except:
        #    print("Error at cycle: {}".format(cycle))
        #    sys.exit()

    log("Total cycles: {}".format(total_cycles))
    log("Highway cycles: {}".format(highway_cycles))
    log("Empty highway cycles: {}".format(empty_count))
    log("{} buildings were generated in {} edges.".format(created, total))

    save_data("output_{}".format(input), ways.values(), nodes.values())
    log("OSM file saved as 'output_{}'".format(input))
    #plot_tags = [("highway",None)]
                 #("highway","trunk"),
                 #("highway","residential")]
    plot_tags = None
    plot(nodes, ways, plot_tags)

if __name__ == '__main__':
    main()
