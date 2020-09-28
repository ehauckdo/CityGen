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
import line
import math
from Node import Node
from lib.NZRenderer import render
from lib.NZMap import readFile
from Map import Cell, OSMWay, OSMNode
from preprocess import get_bounds


index = 0
total = 0
created = 0
colors = ["b","g","r","c","m","y"]

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
        type = "highway" if "highway" in w.tags.keys() else "other"
        for n_id in w.nodes:
            nodes[n_id].type = type

def color_nodes(nodes, color):
    for n in nodes:
        n.color = color

def color_ways(ways, nodes, ways_colors, nodes_colors, default="black"):

    for id, way in ways.items():
        for tag, color in ways_colors.items():
            if tag in way.tags.keys():
                way.color = color
                for n_id in way.nodes:
                    nodes[n_id].color = nodes_colors[tag]
                break
        else:
            way.color = default
            for n_id in way.nodes:
                nodes[n_id].color = default

def plot(nodes, ways):

    G = nx.Graph()
    pos = {}

    for n_id, n in nodes.items():
        G.add_node(n_id)
        pos[n_id] = n.location

    for w_id, way in ways.items():
        for i in range(len(way.nodes)-1):
            n1, n2 = way.nodes[i], way.nodes[i+1]
            G.add_edge(n1, n2, width=1, edge_color=way.color)

    options = { "node_size": 20, "linewidths": 0, }
    node_color = [x.color for x in nodes.values()]
    edges = G.edges()
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
    print("Checking neighbours")
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
def generate_building(lot, source_ways):
    print("Generating building inside of polygon with {} points".format(len(lot)))
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
        n.color = "red"
        return n

    def new_way():
        way = OSMWay()
        global id_counter
        way.id = id_counter
        way.color = next_color()
        id_counter += 1
        return way

    def order_edges_by_size(polygon):
        ordered = []
        for i in range(len(polygon)-1):
             n1 = lot[i]
             n2 = lot[i+1]
             x1, y1 = n1.location[0], n1.location[1]
             x2, y2 = n2.location[0], n2.location[1]
             dist = trig.dist(x1, y1, x2, y2) #math.sqrt((x2-x1)**2 + (y2-y1)**2)
             print("DIST: {}".format(dist))
             ordered.append((dist, (n1,n2)))
        print("Unordered list: ")
        for l in ordered:
            print(l)
        ordered = sorted(ordered, key = lambda x: x[0])
        return [x[1] for x in ordered]

    edges = order_edges_by_size(lot)
    for n1, n2 in edges:

        print("IDs: {} and {}".format(n1.id, n2.id))
        x1, y1 = n1.location[0], n1.location[1]
        x2, y2 = n2.location[0], n2.location[1]

        dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        # filter smaller edges
        if dist < 0.0004:
            continue

        print("Generating building between edges {} and {}".format((x1, y1), (x2, y2)))
        a, b, c = line.get_line_equation(x1, y1, x2, y2)
        u, v = line.get_unit_vector(a, b)
        #print("a: {}, b: {}, c: {}".format(a, b, c))
        #print("u: {}, v: {}".format(u, v))

        generate_n = 4
        div = generate_n*2+2
        x_range = np.linspace(x1, x2, div)
        x_values = [(x_range[i], x_range[i+1]) for i in range(div-1) if i % 2 == 1]
        y_range = np.linspace(y1, y2, div)
        y_values = [(y_range[i], y_range[i+1]) for i in range(div-1) if i % 2 == 1]

        def generate_parallel_building(x1, y1, x2, y2, u, v, dx, dy):
            global created, total
            created_nodes, created_ways = {}, {}
            x3, y3, x4, y4 = line.get_parallel_points(x1, y1, x2, y2, u, v, dx)
            print("p3 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x3,y3,x4,y4))
            x5, y5, x6, y6 = line.get_parallel_points(x1, y1, x2, y2, u, v, dy)
            print("p5 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x5,y5,x6,y6))

            n1 = new_node(x3, y3)
            n2 = new_node(x4, y4)
            n3 = new_node(x6, y6)
            n4 = new_node(x5, y5)

            lot_nodes = [x.location for x in lot]
            lot_nodes.append(lot_nodes[0]) # add last node as an edge
            building_nodes = [n1.location, n2.location, n3.location, n4.location, n1.location]
            total += 1

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
            dx, dy = 0.00005, 0.00020
            created_nodes, created_ways = generate_parallel_building(x1, y1, x2, y2, u, v, dx, dy)
            nodes.update(created_nodes)
            ways.update(created_ways)

            dx, dy = -0.00005, -0.00020
            created_nodes, created_ways = generate_parallel_building(x1, y1, x2, y2, u, v, dx, dy)
            nodes.update(created_nodes)
            ways.update(created_ways)

    ways_list = list(ways.items())
    for i in range(len(ways_list)-1, 0, -1):
        id_1, way_1 = ways_list[i]
        building1_nodes = [n.location for n in [nodes[id] for id in way_1.nodes]]
        for j in range(i-1, -1, -1):
            id_2, way_2 = ways_list[j]
            building2_nodes = [n.location for n in [nodes[id] for id in way_2.nodes]]
            print("COMPARING \nB1 ({}): {} \nB2 ({}): {}".format(id_1, building1_nodes, id_2, building2_nodes))
            if trig.has_intersection(building1_nodes, building2_nodes):
                print("COLLISION BETWEEN {} and {}".format(id_1, id_2))
                ways.pop(id_1)
                for n_id in way_1.nodes:
                    nodes.pop(n_id, None) # the last node in the way is repeated
                break

    print("Generated {} ways".format(len(ways.items())))
    return nodes, ways

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
    print("Reading from '{}'...".format(input))

    nodes, ways = handler.extract_data(input)

    # preprocess nodes, add some properties to them
    set_node_type(ways, nodes)
    color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    color_ways(ways, nodes, ways_colors, nodes_colors, default="black")

    # get all cycles in the graph
    cycles = get_cycles(input)

    # remove cycles that do not represent streets
    for i in range(len(cycles)-1, -1, -1):
        cycles[i].append(cycles[i][0])
        for n_id in cycles[i]:
            if nodes[n_id].type != "highway":
                cycles.pop(i)
                break

    # generate buildings for each cycle
    for cycle in cycles:
        # try:
        n, a = generate_building([nodes[x] for x in cycle], ways)
        nodes.update(n)
        ways.update(a)
        # except:
        #     print("Error at cycle: {}".format(cycle))
        #     sys.exit()

    print("Number of edges: {}".format(total))
    print("Created buildings: {}".format(created))

    plot(nodes, ways)

    save_data("output_{}".format(input), ways.values(), nodes.values())

if __name__ == '__main__':
    main()
