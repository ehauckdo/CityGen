import os
import sys
import random
import copy
import handler
import optparse
from lib.NZRenderer import render
from lib.NZMap import readFile
from Map import Cell, OSMWay
from preprocess import get_bounds

def save_data(filename, ways, nodes):
    handler.write_data(filename, nodes, ways)
    min_lat, min_lon, max_lat, max_lon = get_bounds(nodes)
    handler.insert_bounds(filename, min_lat, min_lon, max_lat, max_lon)

# params: min/max lat/lon, number of cells in which map should be split
# returns: two arrays containing the lat/lon for each cell
def split_area(min_lat, min_lon, max_lat, max_lon, split_in=10):
    import numpy as np
    step = (max_lat - min_lat)/split_in
    lat_range = np.arange(min_lat, max_lat, step)
    lat_range = np.append(lat_range, max_lat)

    step = (max_lon - min_lon)/split_in
    lon_range = np.arange(min_lon, max_lon, step)
    lon_range = np.append(lon_range, max_lon)
    return lat_range, lon_range

def fetch_structures(ways, nodes):
    min_lat, min_lon, max_lat, max_lon = get_bounds(nodes.values())
    lat_range, lon_range = split_area(min_lat, min_lon, max_lat, max_lon, 50)
    structures = []
    for i in range(len(lat_range)-1):
        for j in range(len(lon_range)-1):
            selected_ways, selected_nodes = get_nodes_in_area(ways, nodes, lat_range[i], lon_range[j], lat_range[i+1], lon_range[j+1])
            if len(selected_nodes.values()) > 0:
                min_lat, min_lon, max_lat, max_lon = get_bounds(list(selected_nodes.values()))
                output_file = "generated/{}-{}.osm".format(i,j)
                handler.write_data(output_file, list(selected_nodes.values()), list(selected_ways.values()))
                handler.insert_bounds(output_file, lat_range[i], lon_range[j], lat_range[i+1], lon_range[j+1])
                bounds = (lat_range[i], lon_range[j], lat_range[i+1], lon_range[j+1])
                structures.append((selected_ways, selected_nodes, bounds))
    return structures

def get_nodes_in_area(ways, nodes, min_lat, min_lon, max_lat, max_lon):
    selected_nodes = {}
    selected_ways = {}

    for n in nodes.values():
        lat = n.location[1]
        lon = n.location[0]
        if lat >= min_lat and lat <= max_lat and lon >= min_lon and lon <= max_lon:
            selected_nodes[n.id] = copy.deepcopy(n)

    nodes_ids = selected_nodes.keys()
    for way in ways.values():
        for n in way.nodes:
            if n in nodes_ids:
                selected_ways[way.id] = copy.deepcopy(way)

    for way in selected_ways.values():
        #print("Checking way ", way.id)
        for i in range(len(way.nodes)-1, -1, -1):
            n = way.nodes[i]
            if n not in selected_nodes.keys():
                way.nodes.remove(n)
                #print("removed!", n)
        # get all nodes belonging to the ways in the area
        #for n_id in way.nodes:
            #selected_nodes[n_id] = nodes[n_id]

    #print(len(selected_ways.keys()))
    #print(len(selected_nodes.keys()))
    return selected_ways, selected_nodes

def connect(cell1, cell2, dir1, dir2):
    node1 = getattr(cell1, dir1)
    node2 = getattr(cell2, dir2)
    way = OSMWay()
    way.id = random.randint(0,999999999)
    way.nodes.append(node1.id)
    way.nodes.append(node2.id)
    cell1.ways[way.id] = way
    cell1.nodes[node2.id] = node2

# params: a way object and its list of nodes (to serve as pivot) and
#          a way object  and its list to be shifted in relation to the first
# returns: shifted second way and its nodes
def adjust(way1, nodes1, way2, nodes2, pivot, adjust_node):
    print("pivot node way1", pivot.location[1],
                             pivot.location[0])
    print("adjust node way2", adjust_node.location[1],
                              adjust_node.location[0])
    lat_adjust = pivot.location[1] - adjust_node.location[1]
    lon_adjust = pivot.location[0] - adjust_node.location[0]

    for n in nodes2:
        n.location = (n.location[0]+lon_adjust, n.location[1]+lat_adjust)

    return way2, nodes2

def adjust_cell(cell1, bounds1, cell2, bounds2, direction):
    print("bounds of cell1", bounds1)
    print("bounds of cell2", bounds2)
    print("direction: ", direction)

    if direction == "l":
        # min lat of cell2 must be equal to min lat of cell1
        lat_adjust = bounds1[0] - bounds2[0]
        # min lon of cell2 must be equal to max lon of cell1
        lon_adjust = bounds1[3] - bounds2[1]
    elif direction == "u":
        # min lat of cell2 must be equal to max lat of cell1
        lat_adjust = bounds1[2] - bounds2[0]
        # min lon of cell2 must be equal to min lon of cell1
        lon_adjust = bounds1[1] - bounds2[1]
    else:
        raise Exception

    print("lat_adjust: {}, lon_adjust:{}".format(lat_adjust, lon_adjust))
    adjusted_bounds = (bounds2[0]+lat_adjust, bounds2[1]+lon_adjust,
                       bounds2[2]+lat_adjust, bounds2[3]+lon_adjust)
    print("adjusted_bounds: ", adjusted_bounds)
    cell2.bounds = adjusted_bounds

    for n in cell2.nodes.values():
        n.location = (n.location[0]+lon_adjust, n.location[1]+lat_adjust)


def generate_city(structures, grid_size=5, filename="generated_city.osm"):
    # sorting by the number of nodes -- some structures are almost empty
    #structures.sort(key=lambda t:len(t[1]), reverse=True)
    import sys

    cell = {"contents": None, "bounds":None,
            "l": False, "r": False, "u": False, "d": False}
    import copy
    map_grid = [[Cell() for x in range(grid_size)] for x in range(grid_size)]
    #print(map_grid)

    import math
    center = math.ceil(grid_size/2)

    def previous(r, c, map_grid):
        previous_c = map_grid[r][c-1] if c-1 >= 0 else None
        previous_r = map_grid[r-1][c] if r-1 >= 0 else None
        #print("Previous for {},{}: left:{},up:{}".format(r,c, previous_c, previous_r))
        return previous_c, previous_r

    index = 0

    for r in range(grid_size):
        for c in range(grid_size):
            print("Going through r{}, c{}".format(r, c))
            # randomly select a cell in the first 10 positions of the list
            # cells are ordered descending by number of nodes
            selected = copy.deepcopy(structures.pop(random.randint(0,10)))

            output_file = "generated/grid{}-{}.osm".format(r,c)
            handler.write_data(output_file, list(selected[1].values()), list(selected[0].values()))
            handler.insert_bounds(output_file, *selected[2])

            cell = map_grid[r][c]

            cell.set_ways_nodes(selected[0], selected[1])
            cell.bounds = selected[2]

            cell_left, cell_up = previous(r, c, map_grid)
            if cell_left != None:
                adjust_cell(cell_left, cell_left.bounds, cell, cell.bounds, "l")
            elif cell_up != None:
                adjust_cell(cell_up, cell_up.bounds, cell, cell.bounds, "u")
            else:
                pass # first cell in the grid, no previous cell to adjust

            if cell_left != None:
                connect(cell_left, cell, "r" , "l")
            if cell_up != None:
                connect(cell_up, cell, "u" , "d")

    bundled_ways = []
    bundled_nodes = []
    for r in range(grid_size):
        for c in range(grid_size):
            #cell = map_grid[r][c]["contents"]
            cell = map_grid[r][c]
            bundled_ways.extend(list(cell.ways.values()))
            bundled_nodes.extend(list(cell.nodes.values()))
    # bundle up all grid[r][c] ways, nodes into two lists
    # call save_data
    save_data(filename, bundled_ways, bundled_nodes)

def parseArgs(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="TX-To-TU.osm")
	return parser.parse_args()

def main():
    opt, args = parseArgs(sys.argv[1:])
    input = opt.filename
    print("Reading from '{}'...".format(input))
    output = "output_{}".format(input)

    nodes, ways = handler.extract_data(input)
    structures = fetch_structures(ways, nodes)
    structures.sort(key=lambda t:len(t[1]), reverse=True)

    generate_city(structures, 5, output)
    map = readFile(output)
    render(map)

if __name__ == '__main__':
    main()
