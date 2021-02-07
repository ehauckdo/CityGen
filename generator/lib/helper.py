import os
from area import area
import numpy as np
from bisect import bisect
from lib.logger import log
from lib import settings
import lib.trigonometry as trig
import lib.handler as handler
import osmnx as ox
import networkx as nx
import pickle
import lib.handler as handler

# save data using pickle
def save(data, filename):
    pickle.dump(data, open("{}".format(filename), "wb"))

# load data using pickle
def load(filename):
    try:
        data = pickle.load(open("{}".format(filename), "rb"))
        return data
    except:
        log("FAILED load file {}".format(filename))
        return None

# given an OSM file, remove all nodes and ways outside of passed bounds
# and save it back on the same file
def remove_out_of_bounds(filename, min_lon, min_lat, max_lon, max_lat):
    nodes, ways = handler.extract_data(filename)
    print("nodes: {}, ways: {}".format(len(nodes), len(ways)))
    delete_nodes = []
    for n_id, n in nodes.items():
        lon, lat = n.location
        if lon < min_lon or lon > max_lon or lat < min_lat or lat > max_lat:
            delete_nodes.append(n_id)

    for n_id in delete_nodes:
        del nodes[n_id]
        for w_id, w in ways.items():
            if n_id in w.nodes:
                w.nodes.remove(n_id)

    delete_ways = []
    for w_id, w in ways.items():
        if len(w.nodes) == 0:
            delete_ways.append(w_id)
    for w in delete_ways:
        del ways[w]

    print("nodes: {}, ways: {}".format(len(nodes), len(ways)))
    handler.write_data(filename, nodes.values(), ways.values(), 0.00002)

# try to fetch all cycles from an input OSM file
# (this function considers that the file contains only the road nodes and ways)
def get_cycles(input_file):
    # the cycle basis does not give all the chordless cycles
    # but getting all the cycles from cycle basis and filtering the ones
    # with nodes inside is quite fast
    G = ox.graph.graph_from_xml(input_file, simplify=False, retain_all=True)
    H = nx.Graph(G) # make a simple undirected graph from G

    cycles = nx.cycles.cycle_basis(H) # I think a cycle basis should get all the neighborhoods, except
                                      # we'll need to filter the cycles that are too small.
    return cycles

# alternative to fetch cycles from an input OSM file
# tends to yield more cycles than the previous approach but takes longer
# (this function considers that the file contains only the road nodes and ways)
def get_cycles_minimum(input_file):
    # this is extremely slow, took about 11 minutes to get cycles
    # from residential/unclassified streets of "smaller_tsukuba.osm"
    G = ox.graph.graph_from_xml(input_file, simplify=False, retain_all=True)
    H = nx.Graph(G) # make a simple undirected graph from G

    cycles = nx.cycles.minimum_cycle_basis(H) # I think a cycle basis should get all the neighborhoods, except
                                      # we'll need to filter the cycles that are too small.

    def order_cycles(H, cycle):
        for i in range(len(cycle)-1):
            for j in range(i+1, len(cycle)):
                if H.has_edge(cycle[i], cycle[j]):
                    temp = cycle[i+1]
                    cycle[i+1] = cycle[j]
                    cycle[j] = temp
                    break

    for c in cycles:
        log("Ordering cycle...")
        order_cycles(H, c)
    log("Ordering finished.")

    return cycles

# get all the cycles formed by road nodes in an OSM file
def get_cycles_highway(input_file):
    nodes, ways = handler.extract_data(input_file)
    tags = {"highway":None}
    _nodes, _ways = filter_by_tag(nodes, ways, tags)
    _output = "_temp.osm"
    handler.write_data(_output, _nodes.values(), _ways.values())
    cycles = get_cycles(_output)
    handler.delete_file(_output)
    return cycles

# returns the area of a polygon given by a list of points
def get_area(points):
    coordinates = []
    for lon, lat in points:
        coordinates.append([lon,lat])
    polygon = {'type':'Polygon','coordinates':[coordinates]}
    return area(polygon)

# splits the passed coordinate space into nxn cells and return the
# a matrix containing the ids of nodes for each cell
def split_into_matrix(min_lat, min_lon, max_lat, max_lon, nodes, n=1000):
    lat_range = np.linspace(min_lat, max_lat, n)[1:]
    lon_range = np.linspace(min_lon, max_lon, n)[1:]

    matrix = [[[] for y in range(n)] for x in range(n)]

    for n in nodes.values():
        lon, lat = n.location
        assigned_x, assigned_y = get_node_cell(lon_range, lat_range, lon, lat)
        matrix[assigned_x][assigned_y].append(n.id)

    return matrix, lon_range, lat_range

# given a nxn splitted area, returns the cell indexes for a given lat/lon
def get_node_cell(lon_range, lat_range, lon, lat):
    x = bisect(lon_range, lon)
    y = bisect(lat_range, lat)
    return x, y


def nodes_in_area(min_lat, min_lon, max_lat, max_lon, lat_range, lon_range):
    x_min = bisect(lon_range, min_lon)
    y_min = bisect(lat_range, min_lat)
    x_max = bisect(lon_range, max_lon)
    y_max = bisect(lat_range, max_lat)
    return x_min, y_min, x_max, y_max

# set an extre property for nodes describing if they are road or not
def set_node_type(ways, nodes):
    for n in nodes.values():
        n.type = "unspecified"

    for w_id, w in ways.items():
        type = "highway" if "highway" in w.tags else "other"
        for n_id in w.nodes:
            nodes[n_id].type = type

# used for a prettier plotting
def color_nodes(nodes, color):
    for n in nodes:
        n.color = color

# used for a prettier plotting
def color_ways(ways, nodes, ways_colors, nodes_colors, default="black"):
    tags = {}
    for id, way in ways.items():
        for tag, color in ways_colors.items():
            if tag in way.tags:
                way.color = color
                for n_id in way.nodes:
                    nodes[n_id].color = "black"
                break
        else:
            way.color = default
            for n_id in way.nodes:
                nodes[n_id].color = "black"

# used for a prettier plotting
def color_highways(ways, nodes):
    import matplotlib.pyplot as plt
    pltcolors = iter([plt.cm.Set1(i) for i in range(8)]+
                     [plt.cm.Dark2(i) for i in range(8)]+
                     [plt.cm.tab10(i) for i in range(10)])
    # assigns a color for each appearing highway value in the
    # passed ways. It gets too colorful and hard to understand
    def all_labels(ways, pltcolors):
        tags = {}
        for id, way in ways.items():
            if "highway" in way.tags:
                tag = way.tags["highway"]
                if tag not in tags:
                    tags[tag] = "black"#next(pltcolors)
                way.color = tags[tag]
        return tags

    # assigns colors for specific highways and group all the
    # others into a single color
    def assigned_labels(ways, pltcolors):
        search_tags = ["trunk","primary","secondary","tertiary"]
        other = "gray"
        tags = {}
        for id, way in ways.items():
            if "highway" in way.tags:
                tag = way.tags["highway"]
                if tag not in search_tags:
                    way.color = other
                else:
                    if tag not in tags:
                        tags[tag] = next(pltcolors)
                    way.color = tags[tag]
        tags["others"] = other
        return tags

    tags = assigned_labels(ways, pltcolors)
    return tags

# given a list of cycles, remove any that are not chordless (i.e. there are
# some road nodes inside the cycle)
def remove_nonempty_cycles(nodes, cycles):
    min_lat, min_lon, max_lat, max_lon = handler.get_bounds(nodes.values())
    matrix, lon_range, lat_range = split_into_matrix(min_lat,
                                            min_lon, max_lat, max_lon, nodes)

    empty_cycles = []
    for cycle in cycles:
        log("Nodes in Cycle:", "DEBUG")
        for n_id in cycle:
            log("{} - {}".format(n_id, nodes[n_id].location), "DEBUG")

        min_lat, min_lon, max_lat, max_lon = handler.get_bounds(
                                                    [nodes[x] for x in cycle])
        log("Bounds of cycle: {}".format((min_lat, min_lon, max_lat, max_lon)),
                                                                    "DEBUG")
        x_min, y_min, x_max, y_max = nodes_in_area(min_lat, min_lon,
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

        # remove cycle nodes from the detected nodes dict
        # obs: we use set(cycle) in case the cycle list has the same node at
        # the beginning and end of the list, so we only del it once
        for n_id in set(cycle):
           del detected_nodes[n_id]

        log("Cycle polygon: {}".format(cycle_polygon), "DEBUG")
        for id, n in detected_nodes.items():
           lon, lat = n.location
           if trig.point_inside_polygon(lon, lat, cycle_polygon):
               log("Node inside cycle detected! Coord: {}".format((lon,lat)),
                                                                        "DEBUG")
               break
        else:
            empty_cycles.append(cycle)

    return empty_cycles

# return the list of building ways for a given road cycle
def building_density(nodes,ways,cycle):
    # print("Calculating building density...")
    # print("Cycle nodes: {}".format(cycle))
    matrix, lon_range, lat_range = split_into_matrix(*handler.get_bounds(
                                                        nodes.values()),
                                                        nodes)

    min_lat, min_lon, max_lat, max_lon = handler.get_bounds(
                                                [nodes[x] for x in cycle], ex=0)
    x_min, y_min, x_max, y_max = nodes_in_area(min_lat, min_lon,
                                 max_lat, max_lon, lat_range, lon_range)
    # print("Bounding rectangle of cycle: {}".format((min_lon, max_lon,
    #                                                         min_lat, max_lat)))

    detected_nodes = {}
    for x in range(x_min, x_max+1):
        for y in range(y_min, y_max+1):
            node_ids_list = matrix[x][y]
            for n_id in node_ids_list:
                detected_nodes[n_id] = nodes[n_id]

    # remove cycle nodes from the detected nodes dict
    # obs: we use set(cycle) in case the cycle list has the same node at
    # the beginning and end of the list, so we only del it once
    for n_id in set(cycle):
       del detected_nodes[n_id]

    # print("Total nodes detected in the area: ")
    # print(detected_nodes.keys())

    cycle_polygon = []
    for n_id in cycle:
        cycle_polygon.append(nodes[n_id].location)

    inner_nodes = {}
    for id, n in detected_nodes.items():
       lon, lat = n.location
       if trig.point_inside_polygon(lon, lat, cycle_polygon):
           inner_nodes[id] = n

    # print("Total nodes effectively inside cycle: ")
    # print(inner_nodes.keys())

    detected_ways = {}
    for w_id, way in ways.items():
        for n_id in inner_nodes.keys():
            if n_id in way.nodes:
                detected_ways[w_id] = way
                break

    # import pprint
    # print("Total detected ways inside cycle:")
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint([(x.id, x.tags) for x in detected_ways.values()])

    building_ways = {}
    for w_id, way in detected_ways.items():
        if "building" in way.tags:
            building_ways[w_id] = way

    # print("Total building ways inside cycle: {}".format(len(building_ways)))
    # if len(inner_nodes) > 0:
    #     import sys
    #     print("Found inner nodes in the previous cycle: ")
    #     sys.exit()

    return building_ways

# calculate the centroid for a sequence of points
def centroid(vertexes):
    # source: https://progr.interplanety.org/en/python-how-to-find-the-
    #         polygon-center-coordinates/
     _x_list = [vertex [0] for vertex in vertexes]
     _y_list = [vertex [1] for vertex in vertexes]
     _len = len(vertexes)
     _x = sum(_x_list) / _len
     _y = sum(_y_list) / _len
     return(_x, _y)

def filter_cycles_by_type(nodes, cycles, wanted_type):
    # remove cycles containing nodes of an assigned type other than wanted_type
    for i in range(len(cycles)-1, -1, -1):
        cycles[i].append(cycles[i][0])
        for n_id in cycles[i]:
            if nodes[n_id].type != wanted_type:
                cycles.pop(i)
                break
    return cycles

def filter_by_tag(nodes, ways, tags):
    _nodes, _ways = {}, {}
    for way in ways.values():
        # try to find intersection of keys between two dictionaries
        intersection = set(way.tags.keys()) & set(tags.keys())

        # check if way[key] is an element of the list in tags[key]
        # otherwise, if tags[key] is an empty list, accept any value of way[key]
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

# this can be used to avoid setting id numbers that arleady exist to new nodes
def update_id_counter(nodes):
    for n in nodes:
        if n.id >= settings.id_counter:
            settings.id_counter = n.id + 1

index = 0
colors = ["b","g","c","m","y"]

# fetch largest and smallest side of an obb
def get_obb_data(nodes, cycle):
    import lib.obb as obb
    polygon = []
    for n_id in cycle:
        polygon.append(nodes[n_id].location)

    # returns 2D obb, uses convex hulls
    # yields decent results for symmetric shapes such as rectangles/squares
    box = obb.minimum_bounding_rectangle(np.array(polygon))

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
        return largest[0]

    def shortest_edge(polygon):
        if len(polygon) < 2: return None
        shortest = (trig.dist(*polygon[0], *polygon[1]), None)
        p_size = len(polygon)
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i+1)%p_size]
            dist = trig.dist(p1[0], p1[1], p2[0], p2[1])
            if dist < shortest[0]:
                shortest = (dist, (p1, p2), (polygon[(i+2)%p_size], polygon[(i+1+2)%p_size]))
        return shortest[0]

    largest = largest_edge(box)
    shortest = shortest_edge(box)

    return largest, shortest

def create_folder(foldername):
    try:
        os.mkdir(foldername)
    except FileExistsError:
        pass
