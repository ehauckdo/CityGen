import os
import sys
import random
import copy
import handler
import optparse
import osmnx as ox
import networkx as nx
import numpy as np
from Node import Node
from lib.NZRenderer import render
from lib.NZMap import readFile
from Map import Cell, OSMWay, OSMNode
from preprocess import get_bounds
import parallel_line

index = 0
total = 0
created = 0
colors = ["b","g","r","c","m","y"]

def save_data(filename, ways, nodes):
    handler.write_data(filename, nodes, ways)
    min_lat, min_lon, max_lat, max_lon = get_bounds(nodes)
    handler.insert_bounds(filename, min_lat, min_lon, max_lat, max_lon)

def next_color():
    global index
    global colors
    index += 1
    if index >= len(colors):
        index = 0
    return colors[index]

# I got this implementation from the internet and it appears to work
# I can implement my own using the cross product vector based approach
# where p * tr = q * us
def intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    def ccw(x1, y1, x2, y2, x3, y3):
        return (y3-y1) * (x2-x1) > (y2-y1) * (x3-x1)
    return (ccw(x1,y1, x3,y3, x4,y4) != ccw(x2,y2, x3,y3, x4,y4) and
           ccw(x1,y1, x2,y2, x3,y3) != ccw(x1,y1, x2,y2, x4,y4))

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
    import networkx as nx
    import matplotlib.pyplot as plt
    G = nx.Graph()
    pos = {}

    for n_id, n in nodes.items():
        G.add_node(n_id)
        pos[n_id] = n.location

    for w_id, way in ways.items():
        for i in range(len(way.nodes)-1):
            n1, n2 = way.nodes[i], way.nodes[i+1]
            G.add_edge(n1, n2, width=1, edge_color=way.color)

    options = {
    #"node_color": "black",
    "node_size": 20,
    "linewidths": 0,
    #"width": 0.1,
    }
    # for x in nodes.values():
    #     print(x.id, x.location)
    #     print(x.color)
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
    # print("Original cycles: ")
    # for c in cycles:
    #    print(c)
    # cycles = [set(cycle) for cycle in cycles if len(cycle) > 2] # Turn the lists into sets for next loop.
    # print("Set cycles: ")
    # for c in cycles:
    #     print(c)
    return cycles

id_counter = 993
def generate_building(lot):
    print("Generating building inside of {} points".format(len(lot)))
    if len(lot) <= 0:
        return {}, {}

    lat, lon = lot[0].location[1], lot[0].location[0]
    min_lat, min_lon, max_lat, max_lon = lat, lon, lat, lon
    for node in lot:
        lat, lon = node.location[1], node.location[0]
        min_lat = lat if lat < min_lat else min_lat
        min_lon = lon if lon < min_lon else min_lon
        max_lat = lat if lat > max_lat else max_lat
        max_lon = lon if lon > max_lon else max_lon

    print("Min/Max Lat/Lon: {}".format([min_lat, min_lon, max_lat, max_lon]))

    latspace = np.linspace(min_lat, max_lat, 6)
    min_lat, max_lat = latspace[2], latspace[3]
    lonspace = np.linspace(min_lon, max_lon, 6)
    min_lon, max_lon = lonspace[2], lonspace[3]
    print("Building Coordinates: {}\n".format([min_lat, min_lon, max_lat, max_lon]))

    way = OSMWay()
    global id_counter
    way.id = id_counter
    way.color = "red"
    id_counter += 1

    def new_node(lon, lat):
        global id_counter
        n = OSMNode()
        n.id = id_counter
        id_counter += 1
        n.location = (lon, lat)
        n.color = "red"
        return n

    n1 = new_node(min_lon, min_lat)
    n2 = new_node(max_lon, min_lat)
    n3 = new_node(max_lon, max_lat)
    n4 = new_node(min_lon, max_lat)
    nodes = {n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4}

    way.nodes = [n1.id, n2.id, n3.id, n4.id, n1.id]
    way.tags = {"building":"residential"}
    ways = {way.id:way}

    return nodes, ways

def is_inside(polygon1, polygon2):
    #print("Checking if poylgon1: \n {}".format(polygon1))
    #print("is inside polygon2: \n {}".format(polygon2))

    # Check if there is any intersection between pairs of edges of polygons
    for i in range(len(polygon1)-1):
        x1, y1 = polygon1[i]
        x2, y2 = polygon1[i+1]
        for j in range(len(polygon2)-1):
            x3, y3 = polygon2[j]
            x4, y4 = polygon2[j+1]
            if intersect(x1, y1, x2, y2, x3, y3, x4, y4):
                print("HAS INTERSECTION")
                return False
    print("NO INTERSECTION")

    def point_inside_polygon(x, y, polygon):
        count = 0
        for i in range(len(polygon)-1):
            x1, y1 = polygon[i]
            x2, y2 = polygon[i+1]
            if (y > y1 and y < y2) or (y > y2 and y < y1):
                m = (y2-y1)/(x2-x1)
                ray_x = x1 + (y - y1)/m
                if ray_x > x:  count +=1
        return count % 2 == 1

    # If no intersection is found, we just need to check that at least
    # 1 point of pol1 is within pol2, we do this approximately here
    for x, y in polygon1:
        if point_inside_polygon(x, y, polygon2):
            return True
    return False


def generate_building_parallel(lot, source_ways):
    print("Generating building inside of polygon with {} points".format(len(lot)))
    global created, total
    if len(lot) <= 0:
        return {}, {}
    nodes, ways = {}, {}

    # the cycles don't have the edges ordered, so this function is required
    def are_neighbours(n1, n2, ways):
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

    for i in range(len(lot)-1):

        n1 = lot[i]
        n2 = lot[i+1]
        print("IDs: {} and {}".format(n1.id, n2.id))
        x1, y1 = n1.location[0], n1.location[1]
        x2, y2 = n2.location[0], n2.location[1]
        #if not are_neighbours(n1, n2, source_ways):
        #    continue

        print("Generating building between {} and {}".format((x1, y1), (x2, y2)))
        a, b, c = parallel_line.get_line_equation(x1, y1, x2, y2)
        u, v = parallel_line.get_unit_vector(a, b)
        print("a: {}, b: {}, c: {}".format(a, b, c))
        print("u: {}, v: {}".format(u, v))

        # decrease the width of the building to 1/3 of the edge
        temp = np.linspace(x1, x2, 4)
        x1, x2 = temp[1], temp[2]
        temp = np.linspace(y1, y2, 4)
        y1, y2 = temp[1], temp[2]

        d = 0.00005
        x3, y3, x4, y4 = parallel_line.get_parallel_points(x1, y1, x2, y2, u, v, d)
        print("p3 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x3,y3,x4,y4))
        d = 0.00050
        x5, y5, x6, y6 = parallel_line.get_parallel_points(x1, y1, x2, y2, u, v, d)
        print("p5 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x5,y5,x6,y6))

        n1 = new_node(x3, y3)
        n2 = new_node(x4, y4)
        n3 = new_node(x6, y6)
        n4 = new_node(x5, y5)

        lot_nodes = [x.location for x in lot]
        lot_nodes.append(lot_nodes[0]) # add last node as an edge
        building_nodes = [n1.location, n2.location, n3.location, n4.location, n1.location]
        total += 1
        if is_inside(building_nodes, lot_nodes):

            nodes.update({n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4})
            way = new_way()
            way.nodes = [n1.id, n2.id, n3.id, n4.id, n1.id]
            way.tags = {"building":"residential"}
            ways.update({way.id:way})
            created +=1

        d = -0.00005
        x3, y3, x4, y4 = parallel_line.get_parallel_points(x1, y1, x2, y2, u, v, d)
        print("p3 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x3,y3,x4,y4))
        d = -0.00020
        x5, y5, x6, y6 = parallel_line.get_parallel_points(x1, y1, x2, y2, u, v, d)
        print("p5 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x5,y5,x6,y6))

        # temp = np.linspace(x3, x4, 4)
        # x3, x4 = temp[1], temp[2]
        # # temp = np.linspace(y3, y4, 4)
        # # y3, y4 = temp[1], temp[2]
        # temp = np.linspace(x5, x6, 4)
        # x5, x6 = temp[1], temp[2]
        # # temp = np.linspace(y5, y6, 4)
        # # y6, y5 = temp[1], temp[2]

        n1 = new_node(x3, y3)
        n2 = new_node(x4, y4)
        n3 = new_node(x6, y6)
        n4 = new_node(x5, y5)
        lot_nodes = [x.location for x in lot]
        lot_nodes.append(lot_nodes[0]) # add last node as an edge
        building_nodes = [n1.location, n2.location, n3.location, n4.location, n1.location]
        if is_inside(building_nodes, lot_nodes):

            nodes.update({n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4})
            way = new_way()
            way.nodes = [n1.id, n2.id, n3.id, n4.id, n1.id]
            way.tags = {"building":"residential"}
            ways.update({way.id:way})
            created +=1


        #break

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

    set_node_type(ways, nodes)
    color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    color_ways(ways, nodes, ways_colors, nodes_colors, default="black")

    cycles = get_cycles(input)

    # remove cycles that do not represent streets
    for i in range(len(cycles)-1, -1, -1):
        for n_id in cycles[i]:
            if nodes[n_id].type != "highway":
                cycles.pop(i)
                break

    for cycle in cycles:
        # n, a = generate_building([nodes[x] for x in cycle])
        n, a = generate_building_parallel([nodes[x] for x in cycle], ways)
        nodes.update(n)
        ways.update(a)

    print("Number of edges: {}".format(total))
    print("Created buildings: {}".format(created))

    plot(nodes, ways)

    save_data("output_{}".format(input), ways.values(), nodes.values())

if __name__ == '__main__':
    main()
