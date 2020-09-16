import os
import sys
import random
import copy
import handler
import optparse
from Node import Node
from lib.NZRenderer import render
from lib.NZMap import readFile
from Map import Cell, OSMWay, OSMNode
from preprocess import get_bounds
import osmnx as ox
import networkx as nx

index = 0
colors = ["b","g","r","c","m","y"]

def next_color():
    global index
    global colors
    index += 1
    if index >= len(colors):
        index = 0
    return colors[index]

def plot(nodes, adjacency):
    import networkx as nx
    import matplotlib.pyplot as plt
    G = nx.Graph()
    pos = {}
    labels = {}

    for n_id, n in nodes.items():
        G.add_node(n_id)
        pos[n_id] = n.location
        labels[n_id] = "{}".format(n_id)

    for n1_id, list in adjacency.items():
        for n2_id, attr in list:
            color = attr["color"]
            G.add_edge(n1_id, n2_id, width=1, edge_color=color)

    options = {
    #"node_color": "black",
    "node_size": 20,
    "linewidths": 0,
    #"width": 0.1,
    }

    node_color = [x.color for x in nodes.values()]
    edges = G.edges()
    edge_width = [G[u][v]['width'] for u,v in edges]
    edge_color = [G[u][v]['edge_color'] for u,v in edges]
    nx.draw(G, pos, node_color=node_color, edge_color=edge_color, width=edge_width, **options)
    plt.show()

def create_graph(nodes, ways):
    graph = {}
    adjacency = {}

    for id, node in nodes.items():
        graph[id] = Node(node)
        adjacency[id] = []

    for id, way in ways.items():
        #print(way.nodes)
        for i in range(len(way.nodes)-1):
            n1, n2 = nodes[way.nodes[i]], nodes[way.nodes[i+1]]
            #print("{} - {}".format(way.nodes[i], way.nodes[i+1]))
            graph[n1.id].apply_tag(way.tags)
            graph[n2.id].apply_tag(way.tags)
            color = "black"
            if ("building" in graph[n1.id].tags.keys() and
                "building" in graph[n2.id].tags.keys()):
                    color = "red"
            adjacency[n1.id].append((n2.id, {"color":color}))
            adjacency[n2.id].append((n1.id, {"color":color}))

    return graph, adjacency

def get_cycles(input_file):
    G = ox.graph.graph_from_xml(input_file, simplify=False, retain_all=True)

    H = nx.Graph(G) # make a simple undirected graph from G
    cycles = nx.cycles.cycle_basis(H) # I think a cycle basis should get all the neighborhoods, except
                                      # we'll need to filter the cycles that are too small.
    cycles = [set(cycle) for cycle in cycles if len(cycle) > 2] # Turn the lists into sets for next loop.
    return cycles

id_counter = 993
def generate_building(lot):
    print("Generating building inside {}".format(lot))
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
    import numpy as np
    latspace = np.linspace(min_lat, max_lat, 6)
    min_lat, max_lat = latspace[2], latspace[3]
    lonspace = np.linspace(min_lon, max_lon, 6)
    min_lon, max_lon = lonspace[2], lonspace[3]
    print("Building Coordinates: {}\n".format([min_lat, min_lon, max_lat, max_lon]))

    def new_node(lon, lat):
        global id_counter
        n = Node()
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

    c = "red"
    adjacencies = { n1.id: [(n2.id, {"color":c}), (n4.id, {"color":c})],
                    n2.id: [(n1.id, {"color":c}), (n3.id, {"color":c})],
                    n3.id: [(n2.id, {"color":c}), (n4.id, {"color":c})],
                    n4.id: [(n3.id, {"color":c}), (n1.id, {"color":c})] }
    return nodes, adjacencies

def to_osm(graph, adjacency):
    nodes, ways = {}

    for n_id, n in graph.items():
        node = OSMNode(n)
        node.tags = n.tags

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
    print("Reading from '{}'...".format(input))
    output = "output_{}".format(input)

    nodes, ways = handler.extract_data(input)

    graph, adjacency = create_graph(nodes,ways)
    cycles = get_cycles(input)

    # remove cycles that represent buildings
    for i in range(len(cycles)-1, -1, -1):
        for n_id in cycles[i]:
            if "building" in graph[n_id].tags.keys():
                cycles.pop(i)
                break

    for cycle in cycles:
        n, a = generate_building([graph[x] for x in cycle])
        graph.update(n)
        adjacency.update(a)

    plot(graph, adjacency)

if __name__ == '__main__':
    main()
