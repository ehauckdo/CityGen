from area import area
import numpy as np
from bisect import bisect

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

index = 0
colors = ["b","g","c","m","y"]
def next_color():
    global index, colors
    index += 1
    if index >= len(colors):
        index = 0
    return colors[index]
