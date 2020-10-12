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
import math
import time
import helper
from lib.NZRenderer import render
from lib.NZMap import readFile
from Map import Cell, OSMWay, OSMNode
import building
import obb
from pyobb.obb import OBB

total = 0
created = 0

tic = time.perf_counter()
logging.basicConfig(level=logging.DEBUG, filemode='w', filename='_main.log')
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
    if level == "WARN": logging.warn(logstring)

def plot(nodes, ways, tags=None, ways_labels=None):

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
    nx.draw(G, pos, node_color=node_color, edge_color=edge_color,
                width=edge_width, **options)

    if ways_labels != None:
        h2 = nx.draw_networkx_edges(G, pos=pos, edge_color=edge_color)

        def make_proxy(clr, mappable, **kwargs):
            from matplotlib.lines import Line2D
            return Line2D([0, 1], [0, 1], color=clr, **kwargs)

        # generate proxies with the above function
        proxies = [make_proxy(clr, h2, lw=5) for clr in list(ways_labels.values())]
        edge_labels = ["{}".format(tag) for tag, color in ways_labels.items()]
        plt.legend(proxies, edge_labels)

    plt.show()

def get_cycles(input_file):
    G = ox.graph.graph_from_xml(input_file, simplify=False, retain_all=True)
    H = nx.Graph(G) # make a simple undirected graph from G

    cycles = nx.cycles.cycle_basis(H) # I think a cycle basis should get all the neighborhoods, except
                                      # we'll need to filter the cycles that are too small.
    return cycles

def filter_by_tag(nodes, ways, tags):
    _nodes, _ways = {}, {}
    for way in ways.values():
        intersection = set(way.tags.keys()) & set(tags.keys())
        if intersection:
            for key in intersection:
                if tags[key] == None:
                    _ways[way.id] = way
                    for n_id in way.nodes:
                        _nodes[n_id] = nodes[n_id]
                elif way.tags[key] in tags[key]:
                    _ways[way.id] = way
                    for n_id in way.nodes:
                        _nodes[n_id] = nodes[n_id]

    return _nodes, _ways

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

        min_lat, min_lon, max_lat, max_lon = handler.get_bounds(
                                                    [nodes[x] for x in cycle])
        log("Bounds of cycle: {}".format((min_lat, min_lon, max_lat, max_lon)))
        x_min, y_min, x_max, y_max = helper.nodes_in_area(min_lat, min_lon,
                                     max_lat, max_lon, lat_range, lon_range)
        detected_nodes = {}
        for x in range(x_min, x_max+1):
            for y in range(y_min, y_max+1):
                node_ids_list = matrix[x][y]
                for n_id in node_ids_list:
                    detected_nodes[n_id] = nodes[n_id]

        log("Nodes inside matrix area of cycle: ", "DEBUG")
        for n_id, n in detected_nodes.items():
            log("{} - {}".format(n_id, n.location), "DEBUG")

        cycle_polygon = []
        for n_id in cycle:
            cycle_polygon.append(nodes[n_id].location)

        # we use set(cycle) in case the cycle list has the same node at
        # the beginning and end of the list
        for n_id in set(cycle):
           log("Attempting to delete {} from detected_nodes".format(n_id)
                    , "DEBUG")
           del detected_nodes[n_id]

        log("Cycle polygon: {}".format(cycle_polygon))
        for id, n in detected_nodes.items():
           lon, lat = n.location
           if trig.point_inside_polygon(lon, lat, cycle_polygon):
               log("Node inside cycle detected! Coord: {}".format((lon,lat)))
               break
        else:
            empty_cycles_count += 1
            empty_cycles.append(cycle)

    return empty_cycles, empty_cycles_count

def f1(nodes, ways, cycle, cycle_data):
    # TODO: use a more intelligent approach like the one in this answer to get
    # a minimum size for our pacels: https://stats.stackexchange.com/a/49823
    def get_lower(avg, std, multiplier=0.5):
        lower_a = -1
        while lower_a < 0:
            lower_a = avg - std*multiplier
            multiplier -= 0.05
            if multiplier < 0: raise Exception
        return lower_a

    lower_a = get_lower(cycle_data["avg_area"],cycle_data["std_area"]) * 3
    upper_a = lower_a * 1.5
    _nodes, _ways = {}, {}
    log("\nLower area bound: {}\nUpper area bound: {}".format(lower_a, upper_a))
    points = [n.location for n_id, n in nodes.items() if n_id in cycle]
    area = helper.get_area(points)

    print("Processing cycle: ")
    polygon = []
    for n_id in cycle:
        print("id {}: \t{}".format(n_id, nodes[n_id].location))
        polygon.append(nodes[n_id].location)
    log("\nCurrent cycle area: {:.10f}".format(area))

    # returns 2D obb, uses the PCA/covariance/eigenvector method
    # good results for general shapes but TERRIBLE for rectangles/squares
    #box = obb.get_OBB(polygon)

    #  returns 3D obb, uses the PCA/covariance/eigenvector method
    # good results for general shapes but TERRIBLE for rectangles/squares
    #obb = OBB.build_from_points(polygon)
    #indexes = range(8)#[1, 2, 5, 6]
    #box = [(obb.points[i][0],obb.points[i][1]) for i in indexes]

    # returns 2D obb, uses convex hulls
    # yields decent results for symmetric shapes such as rectangles/squares
    box = obb.minimum_bounding_rectangle(np.array(polygon))
    #print("Box: {}".format(box))

    # ==== plot nodes from obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n_ids = []
    # for lon, lat in box:
    #     n = building.new_node(lon, lat)
    #     n_ids.append(n.id)
    #     _nodes[n.id] = n
    # w = building.new_way(n_ids + n_ids[:1], {"highway":"primary"})
    # _ways[w.id] = w
    # ====

    def largest_edge(polygon):
        if len(polygon) < 2: return None
        largest = (0, None)
        p_size = len(polygon)
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i+1)%p_size]
            dist = trig.dist(p1[0], p1[1], p2[0], p2[1])
            #print("Length {}: between points {}".format(dist, (p1,p2)))
            if dist > largest[0]:
                largest = (dist, (p1, p2), (polygon[(i+2)%p_size], polygon[(i+1+2)%p_size]))
        return *largest[1], *largest[2]

    def get_midpoint(p1, p2):
        x = p1[0] + (p2[0] - p1[0])/2
        y = p1[1] + (p2[1] - p1[1])/2
        return x, y

    p1, p2, p1_opposite, p2_opposite = largest_edge(box)
    # print("Largest: {}".format((p1, p2)))
    # print("Opposite: {}".format((p1_opposite, p2_opposite)))

    midpoint = get_midpoint(p1, p2)
    midpoint_opposite = get_midpoint(p1_opposite, p2_opposite)
    # print("Midpoint: {}".format(midpoint))
    # print("Midpoint Opposite: {}".format(midpoint_opposite))

    # extend the lines a little bit just to make sure they will
    # intersect with the edges of the polygon
    midpoint_opposite = trig.extend_line(*midpoint, *midpoint_opposite)
    midpoint = trig.extend_line(*midpoint_opposite, *midpoint)

    # ==== plot nodes from the perpendicular line to obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n1 = building.new_node(*midpoint)
    # _nodes[n1.id] = n1
    # n2 = building.new_node(*midpoint_opposite)
    # _nodes[n2.id] = n2
    # w = building.new_way([n1.id, n2.id], {"highway":"primary"})
    # _ways[w.id] = w
    # ====

    p3 = midpoint
    p4 = midpoint_opposite
    p_size = len(polygon)
    intersected = []

    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i+1)%p_size]

        intersect = trig.my_intersect(*p1, *p2, *p3, *p4)
        if intersect:
            # print("Intersected point {} between nodes {} and {}".format(
            #     intersect, p1, p2))
            intersected.append((intersect,i))

    if len(intersected) > 2:
        return   # this polygon is a bit more complex
                 # than what we hoped for, so just skip it

    if len(intersected) < 2:
        # for some reason we did not manage to find the two edges of the
        # polygon that intersect with the line splitting the OBB in two.
        # this is not meant to happen
        log("Partitioning with OBB failed for cycle {}".format(cycle), "WARN")
        return

    # get the two edges that intersect with the line dividing the OBB
    # and create two nodes and a way connecting them
    pos, polygon_index = intersected[0]
    n1 = building.new_node(*pos)
    nodes[n1.id] = n1
    polygon.insert((polygon_index+1)%len(polygon), pos)

    pos, polygon_index = intersected[1]
    n2 = building.new_node(*pos)
    nodes[n2.id] = n2
    polygon.insert((polygon_index+2)%len(polygon), pos)

    w = building.new_way([n1.id, n2.id], {"highway":"primary"})
    ways[w.id] = w

    #_nodes.update(nodes)
    #_ways.update(ways)

    print("New Polygon: ")
    for point in polygon:
        print(point)

    p1_index = intersected[0][1]+1
    p2_index = (intersected[1][1]+1)%(len(cycle))
    print("P1: {}, P2: {}".format(p1_index, p2_index))

    subcycle1 = [n1.id]
    it = p1_index
    while it != p2_index:
        subcycle1.append(cycle[it])
        it = (it+1)%len(cycle)
    subcycle1.append(n2.id)

    subcycle2 = [n2.id]
    it = p2_index
    while it != p1_index:
        subcycle2.append(cycle[it])
        it = (it+1)%len(cycle)
    subcycle2.append(n1.id)

    print("Subcycle1: ")
    subpolygon1 = []
    for n_id in subcycle1:
        print("{}: {}".format(n_id, nodes[n_id].location))
        #subpolygon1.append(nodes[n_id].location)

    print("Subcycle2: ")
    subpolygon2 = []
    for n_id in subcycle2:
        print("{}: {}".format(n_id, nodes[n_id].location))
        #subpolygon2.append(nodes[n_id].location)


    colored_labels = helper.color_highways(ways,nodes)
    plot(nodes, ways, tags=None, ways_labels=colored_labels)

    #input("Press any key to continue...")

    import copy
    #backup_nodes = copy.deepcopy(_nodes)
    #backup_ways = copy.deepcopy(_ways)

    #points = [n.location for n_id, n in _nodes.items() if n_id in subcycle1]
    points = []
    for n_id in subcycle1:
        points.append(nodes[n_id].location)
    print("Subcycle Points for Area Calculation:")
    for p in points:
        print(p)
    area = helper.get_area(points)
    print("Area of Subycle1: {:.10f} (lower_a: {:.10f})".format(area, lower_a))
    if area > lower_a:
        print("Executing recursion Sub1...")
        #backup_nodes = {}
        #for n_id, n in _nodes.items(): backup_nodes[n_id] = n
        #backup_ways = {}
        #for w_id, w in _ways.items(): backup_ways[w_id] = w
        f1(nodes, ways, subcycle1, cycle_data)

    #points = [n.location for n_id, n in _nodes.items() if n_id in subcycle2]
    points = []
    for n_id in subcycle1:
        points.append(nodes[n_id].location)
    area = helper.get_area(points)
    print("Area of Subycle2: {:.10f} (lower_a: {:.10f})".format(area, lower_a))
    if area > lower_a:
        print("Executing recursion Sub2...")
        f1(nodes, ways, subcycle2, cycle_data)

def parseArgs(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="_TX-To-TU.osm")
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

    min_lat, min_lon, max_lat, max_lon = handler.get_bounds(nodes.values())
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
    log("Building data min_dist:{:f}, std_min:{:f}".format(min_dist, std_min) +
        ", max_dist: {:f}, std_max:{:f}".format(max_dist, std_max))

    # preprocess nodes, add some properties to them
    helper.set_node_type(ways, nodes)
    helper.color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    helper.color_ways(ways, nodes, ways_colors, nodes_colors, default="black")
    colored_labels = helper.color_highways(ways, nodes)
    log("Nodes preprocessed sucessfully.")

    #tags = {"highway":["trunk","primary","secondary","tertiary"]}
    #tags = {"highway":None}
    tags = {"highway":["residential","unclassified"]}
    _nodes, _ways = filter_by_tag(nodes, ways, tags)

    # get all cycles in the graph
    _output = "_temp.osm"
    handler.write_data(_output, _nodes.values(), _ways.values())
    _cycles = get_cycles(_output)
    handler.delete_file(_output)
    total_cycles = len(_cycles)

    # cycles = remove_cycles_type(nodes, cycles, "highway")
    # highway_cycles = len(cycles)
    # log("{}/{} highway cycles were identified.".format(highway_cycles,
    #                                                 total_cycles))
    #
    min_area, max_area, avg_area, std_area = get_cycles_data(nodes, _cycles)
    cycle_data = {"min_area": min_area,
             "max_area": max_area,
             "avg_area": avg_area,
             "max_dist": max_dist,
             "std_area": std_area}
    log(cycle_data)

    # tags = {"highway":["trunk","primary","secondary","tertiary"]}
    # nodes, ways = filter_by_tag(nodes, ways, tags)
    #
    # # get all cycles in the graph
    # _output = "_temp.osm"
    # handler.write_data(_output, nodes.values(), ways.values())
    # cycles = get_cycles(_output)
    cycles = get_cycles(input)

    min_lat, min_lon, max_lat, max_lon = handler.get_bounds(nodes.values())
    matrix, lon_range, lat_range = helper.split_into_matrix(min_lat,
                                            min_lon, max_lat, max_lon, nodes)

    cycles, empty_count = remove_nonempty_cycles(nodes, cycles, matrix,
                                                     lon_range, lat_range)

    print("Empty cycles: {}".format(len(cycles)))
    for cycle in cycles:
       f1(nodes, ways, cycle, cycle_data)
       print("")
       #break

    #
    # cycles, empty_count = remove_nonempty_cycles(nodes, cycles, matrix,
    #                                                 lon_range, lat_range)
    #
    # # for cycle in cycles:
    #     #try:
    #     n, a = building.generate_in_cycle([nodes[x] for x in cycle], ways)
    #     nodes.update(n)
    #     ways.update(a)
    #    # except:
    #     #    print("Error at cycle: {}".format(cycle))
    #     #    sys.exit()
    #
    log("Total cycles: {}".format(total_cycles))
    # log("Highway cycles: {}".format(highway_cycles))
    # log("Empty highway cycles: {}".format(empty_count))
    # log("{} buildings were generated in {} edges.".format(created, total))
    #
    # handler.write_data("_output_{}".format(input), nodes.values(),
    #                         ways.values())
    # log("OSM file saved as 'output_{}'".format(input))
    # plot_tags = [("highway",None)]
    # # plot_tags = [("highway","primary"),
    # #              ("highway","trunk"),
    # #              ("highway","seconday"),
    # #              ("highway","tertiary"),
    # #              ("highway","motorway_link"),
    # #              ("highway","trunk_link"),
    # #              ("highway","primary_link"),
    # #              ("highway","secondary_link"),
    # #              ("highway","tertiary_link")]
    # #plot_tags = None
    # plot(nodes, ways, plot_tags, ways_labels=colored_labels)
    plot(nodes, ways, tags=None, ways_labels=None)

if __name__ == '__main__':
    main()
