import os, sys
import handler
import optparse
import numpy as np
import trigonometry as trig
import matplotlib.pyplot as plt
import logging
import math
import helper
import building
from lib.logger import elapsed, log
from lib.plotter import plot

total = 0
created = 0

logging.basicConfig(level=logging.DEBUG, filemode='w', filename='_main.log')
#logging.getLogger().addHandler(logging.StreamHandler())

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

    # get all cycles in the graph
    cycles = helper.get_cycles(input)
    total_cycles = len(cycles)

    cycles = helper.filter_cycles_by_type(nodes, cycles, "highway")
    highway_cycles = len(cycles)
    log("{}/{} highway cycles were identified.".format(highway_cycles,
                                                    total_cycles))

    min_area, max_area, avg_area, std_area = helper.get_cycles_data(nodes,
                                                                        cycles)
    cycle_data = {"min_area": min_area,
             "max_area": max_area,
             "avg_area": avg_area,
             "max_dist": max_dist,
             "std_area": std_area}
    log(cycle_data)

    cycles = helper.remove_nonempty_cycles(nodes, cycles, matrix,
                                                    lon_range, lat_range)

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
    log("Empty highway cycles: {}".format(len(cycles)))
    log("{} buildings were generated in {} edges.".format(created, total))

    handler.write_data("{}_output.osm".format(input), nodes.values(),
                            ways.values())
    log("OSM file saved as 'output_{}'".format(input))

    plot_tags = [("highway",None)]
    plot_tags = None
    # plot_tags = [("highway","primary"),
    #              ("highway","trunk"),
    #              ("highway","seconday"),
    #              ("highway","tertiary"),
    #              ("highway","motorway_link"),
    #              ("highway","trunk_link"),
    #              ("highway","primary_link"),
    #              ("highway","secondary_link"),
    #              ("highway","tertiary_link")]
    #plot_tags = None
    plot(nodes, ways, plot_tags, ways_labels=None)

if __name__ == '__main__':
    main()
