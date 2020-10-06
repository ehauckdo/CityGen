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

index = 0
total = 0
created = 0
colors = ["b","g","c","m","y"]
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

def next_color():
    global index, colors
    index += 1
    if index >= len(colors):
        index = 0
    return colors[index]

def set_node_type(ways, nodes):
    for n in nodes.values():
        n.type = "unspecified"

    for w_id, w in ways.items():
        type = "highway" if "highway" in w.tags else "other"
        for n_id in w.nodes:
            nodes[n_id].type = type

def color_nodes(nodes, color):
    for n in nodes:
        n.color = color

def color_ways(ways, nodes, ways_colors, nodes_colors, default="black"):

    for id, way in ways.items():
        for tag, color in ways_colors.items():
            if tag in way.tags:
                way.color = color
                for n_id in way.nodes:
                    nodes[n_id].color = nodes_colors[tag]
                break
        else:
            way.color = default
            for n_id in way.nodes:
                nodes[n_id].color = default

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

def are_neighbours(n1, n2, ways):
    # depending on how the cycles are passed, their edges may not be ordered
    # so it is useful to keep this function here just in case
    for id, w in ways.items():
        #print("Checking way {}".format(w.id))
        for i in range(len(w.nodes)-1):
            wn1, wn2 = w.nodes[i], w.nodes[i+1]
            #print("n1: {}, n2: {}, wn1:{}, wn2: {}".format(n1.id, n2.id, wn1, wn2))
            if (wn1 == n1.id and wn2 == n2.id) or (wn1 == n2.id and wn2 == n1.id):
                return True
        else:
            fn1, ln2 = w.nodes[0], w.nodes[-1]
            if (fn1 == n1.id and ln2 == n2.id) or (fn1 == n2.id and ln2 == n1.id):
                return True
    return False

id_counter = 993
def generate_building(lot, source_ways, data=None):
    global created, total
    nodes, ways = {}, {}

    if len(lot) <= 0:
        return nodes, ways

    def new_node(lon, lat):
        global id_counter
        n = OSMNode()
        n.id = id_counter
        id_counter += 1
        n.location = (lon, lat)
        n.color = "blue"
        return n

    def new_way():
        way = OSMWay()
        global id_counter
        way.id = id_counter
        way.color = "blue"
        id_counter += 1
        return way

    def order_edges_by_size(polygon):
        ordered = []
        for i in range(len(polygon)-1):
             n1 = lot[i]
             n2 = lot[i+1]
             x1, y1 = n1.location[0], n1.location[1]
             x2, y2 = n2.location[0], n2.location[1]
             dist = trig.dist(x1, y1, x2, y2)
             ordered.append((dist, (n1,n2)))
        ordered = sorted(ordered, key = lambda x: x[0])
        return [x[1] for x in ordered]

    def get_next_point(x1,y1,x2,y2,dist):
        d = trig.dist(x1,y1,x2,y2)
        x3 = (dist*(x2-x1))/d + x1
        y3 = (dist*(y2-y1))/d + y1
        return x3, y3

    edges = order_edges_by_size(lot)
    for n1, n2 in edges:

        log("Nodes: {} and {}".format(n1.id, n2.id), "DEBUG")
        x1, y1 = n1.location[0], n1.location[1]
        x2, y2 = n2.location[0], n2.location[1]
        dist = trig.dist(x1, y1, x2, y2)

        if dist < 0.0004:
            continue # filter smaller edges

        log("Generating building between edges {} and {}".format((x1, y1),
                                                        (x2, y2)), "DEBUG")
        total += 1
        a, b, c = line.get_line_equation(x1, y1, x2, y2)
        u, v = line.get_unit_vector(a, b)
        #print("a: {}, b: {}, c: {}".format(a, b, c))
        #print("u: {}, v: {}".format(u, v))

        def get_divisor2(x1, y1, x2, y2, maxdist, maxstd):
            threshold =random.uniform(maxdist-maxstd, maxdist+maxstd)
            n = 1
            div = n*2+2
            x_range = np.linspace(x1, x2, div)
            y_range = np.linspace(y1, y2, div)
            test_x1, test_x2 = x_range[0], x_range[1]
            test_y1, test_y2 = y_range[0], y_range[1]
            #dist = trig.dist(test_x1, test_y1, test_x2, test_y2)
            dist = math.sqrt((test_x2-test_x1)**2 + (test_y2-test_y1)**2)
            while dist > threshold:
                n += 1
                div = n*2+2
                x_range = np.linspace(x1, x2, div)
                y_range = np.linspace(y1, y2, div)
                test_x1, test_x2 = x_range[0], x_range[1]
                test_y1, test_y2 = y_range[0], y_range[1]
                dist = trig.dist(test_x1, test_y1, test_x2, test_y2)
                #dist = math.sqrt((test_x2-test_x1)**2 + (test_y2-test_y1)**2)
                print("{} - {}".format(n, dist))
            x_values = [(x_range[i], x_range[i+1]) for i in range(div-1) if i % 2 == 1]
            y_values = [(y_range[i], y_range[i+1]) for i in range(div-1) if i % 2 == 1]
            return x_values, y_values

        generate_n = 4
        div = generate_n*2+2
        x_range = np.linspace(x1, x2, div)
        x_values = [(x_range[i], x_range[i+1]) for i in range(div-1) if i % 2 == 1]
        y_range = np.linspace(y1, y2, div)
        y_values = [(y_range[i], y_range[i+1]) for i in range(div-1) if i % 2 == 1]
        dx, dy = 0.00010, 0.00010

        def generate_parallel_building(x1, y1, x2, y2, u, v, dx, dy):
            global created, total
            created_nodes, created_ways = {}, {}
            x3, y3, x4, y4 = line.get_parallel_points(x1, y1, x2, y2, u, v, dx)
            dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            x5, y5 = line.get_pont_in_line(x1,y1,x3,y3,dist)
            x6, y6 = line.get_pont_in_line(x2,y2,x4,y4,dist)
            #log("p3 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x3,y3,x4,y4))
            #x5, y5, x6, y6 = line.get_parallel_points(x1, y1, x2, y2, u, v, dy)
            #print("p5 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x5,y5,x6,y6))

            n1 = new_node(x3, y3)
            n2 = new_node(x4, y4)
            n3 = new_node(x6, y6)
            n4 = new_node(x5, y5)

            lot_nodes = [x.location for x in lot]
            lot_nodes.append(lot_nodes[0]) # add last node as an edge
            building_nodes = [n1.location, n2.location, n3.location, n4.location, n1.location]

            if trig.is_inside(building_nodes, lot_nodes):
                #nodes.update({n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4})
                way = new_way()
                way.nodes = [n1.id, n2.id, n3.id, n4.id, n1.id]
                way.tags = {"building":"residential"}
                #ways.update({way.id:way})
                created +=1
                created_nodes = {n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4}
                created_ways = {way.id:way}

            return created_nodes, created_ways

        for (x1, x2), (y1, y2) in zip(x_values, y_values):
            # dx = distance of the wall to the street
            # dy = distance of the front wall to the rear wall
            #dx, dy = 0.00005, 0.00020
            created_nodes, created_ways = generate_parallel_building(x1, y1, x2, y2, u, v, dx, dy)
            nodes.update(created_nodes)
            ways.update(created_ways)

            #dx, dy = -0.00005, -0.00020
            created_nodes, created_ways = generate_parallel_building(x1, y1, x2, y2, u, v, -dx, -dy)
            nodes.update(created_nodes)
            ways.update(created_ways)

    ways_list = list(ways.items())
    for i in range(len(ways_list)-1, 0, -1):
        id_1, way_1 = ways_list[i]
        building1_nodes = [n.location for n in [nodes[id] for id in way_1.nodes]]
        for j in range(i-1, -1, -1):
            id_2, way_2 = ways_list[j]
            building2_nodes = [n.location for n in [nodes[id] for id in way_2.nodes]]
            log("Comparing buildings \nb1 ({}): {} \nb2 ({}): {}".format(
                   id_1, building1_nodes, id_2, building2_nodes), "DEBUG")
            if trig.has_intersection(building1_nodes, building2_nodes):
                log("Overlap detected. Removing {}".format(id_1), "DEBUG")
                ways.pop(id_1)
                for n_id in way_1.nodes:
                    nodes.pop(n_id, None) # the last node in the way is repeated
                break

    log("Generated a total of {} ways".format(len(ways.items())), "DEBUG")
    return nodes, ways

def scan_buildings(ways, nodes):
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

def scan_cycles(nodes, cycles):
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

    number_edges, min_dist, std_min, max_dist, std_max = scan_buildings(ways, nodes)
    edge_data = {"number_edges": number_edges,
            "min_dist": min_dist,
            "std_min": std_min,
            "max_dist": max_dist,
            "std_max": std_max}

    log("Building data collected succesfully.")
    log("Building data: min_dist:{:f}, std_min:{:f}".format(min_dist, std_min) +
        ", max_dist: {:f}, std_max:{:f}".format(max_dist, std_max))

    # preprocess nodes, add some properties to them
    set_node_type(ways, nodes)
    color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    color_ways(ways, nodes, ways_colors, nodes_colors, default="black")
    log("Nodes preprocessed sucessfully.")

    # get all cycles in the graph
    cycles = get_cycles(input)
    total_cycles = len(cycles)

    cycles = remove_cycles_type(nodes, cycles, "highway")
    highway_cycles = len(cycles)
    log("{}/{} highway cycles were identified.".format(highway_cycles,
                                                    total_cycles))

    min_area, max_area, avg_area, std_area = scan_cycles(nodes, cycles)
    cycle_data = {"min_area": min_area,
             "max_area": max_area,
             "avg_area": avg_area,
             "max_dist": max_dist,
             "std_area": std_area}
    log(cycle_data)

    cycles, empty_count = remove_nonempty_cycles(nodes, cycles, matrix, lon_range, lat_range)

    for cycle in cycles:
        try:
            n, a = generate_building([nodes[x] for x in cycle], ways)
            nodes.update(n)
            ways.update(a)
        except:
            print("Error at cycle: {}".format(cycle))
            sys.exit()

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
