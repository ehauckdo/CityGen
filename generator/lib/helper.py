from area import area
import numpy as np
from bisect import bisect
from lib.logger import log
import lib.trigonometry as trig
import lib.handler as handler
import osmnx as ox
import networkx as nx

def get_cycles(input_file):
    # the cycle basis does not give all the chordless cycles
    # but getting all the cycles from cycle basis and filtering the ones
    # with nodes inside is quite fast
    G = ox.graph.graph_from_xml(input_file, simplify=False, retain_all=True)
    H = nx.Graph(G) # make a simple undirected graph from G

    cycles = nx.cycles.cycle_basis(H) # I think a cycle basis should get all the neighborhoods, except
                                      # we'll need to filter the cycles that are too small.
    return cycles

def get_cycles_minimum(input_file):
    # it seems I can get all the chordless cycles with this approach
    # whoever, it is extremely slow, took about 11 minutes to get cycles
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

def get_area(points):
    coordinates = []
    for lon, lat in points:
        coordinates.append([lon,lat])
    polygon = {'type':'Polygon','coordinates':[coordinates]}
    return area(polygon)

def split_into_matrix(min_lat, min_lon, max_lat, max_lon, nodes, n=1000):
    lat_range = np.linspace(min_lat, max_lat, n)[1:]
    lon_range = np.linspace(min_lon, max_lon, n)[1:]

    matrix = [[[] for y in range(n)] for x in range(n)]

    for n in nodes.values():
        lon, lat = n.location
        assigned_x, assigned_y = get_node_cell(lon_range, lat_range, lon, lat)
        matrix[assigned_x][assigned_y].append(n.id)

    return matrix, lon_range, lat_range

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
    tags = {}
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
                    tags[tag] = next(pltcolors)
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

def get_cycles_data(nodes, cycles):
    areas = []
    for c in cycles:
        points = []
        for n_id in c:
            points.append(nodes[n_id].location)
        area = get_area(points)
        areas.append(area)
    return min(areas), max(areas), np.average(areas), np.std(areas)

def remove_nonempty_cycles(nodes, cycles, matrix, lon_range, lat_range):
    empty_cycles = []
    for cycle in cycles:
        log("Nodes in Cycle:", "DEBUG")
        for n_id in cycle:
            log("{} - {}".format(n_id, nodes[n_id].location), "DEBUG")

        min_lat, min_lon, max_lat, max_lon = handler.get_bounds(
                                                    [nodes[x] for x in cycle])
        log("Bounds of cycle: {}".format((min_lat, min_lon, max_lat, max_lon)))
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
            empty_cycles.append(cycle)

    return empty_cycles

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

index = 0
colors = ["b","g","c","m","y"]
def next_color():
    global index, colors
    index += 1
    if index >= len(colors):
        index = 0
    return colors[index]
