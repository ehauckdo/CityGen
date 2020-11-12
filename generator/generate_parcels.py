import os, sys
import lib.handler as handler
import optparse
import logging
import lib.helper as helper
from lib.logger import log
from lib.plotter import plot
from parcel import generate_parcel_density, generate_parcel_minarea

total = 0
created = 0

logging.basicConfig(level=logging.INFO, filemode='w', filename='_main.log')
#logging.getLogger().addHandler(logging.StreamHandler())

def parse_args(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="data/smaller_tsukuba.osm")
	return parser.parse_args()

def main():

    os.system('clear')
    opt, args = parse_args(sys.argv[1:])
    input = opt.filename
    output = "output_{}".format(input)
    print(input)
    log("Reading OSM file '{}'...".format(input))

    # we can obtain parcel data from one type of highway (e.g. residential)
    # and then use this data to generate on another (e.g. primary, secondary)
    obtain_data_from = ["residential","unclassified"]
    generate_on = ["trunk","primary","secondary","tertiary"]
    #generate_on = ["residential","unclassified"]

    nodes, ways = handler.extract_data(input)
    original_nodes, original_ways = nodes, ways
    helper.update_id_counter(nodes.values())
    log("Data read sucessfully.")
    log("Total nodes: {}".format(len(nodes.values())))
    log("Total ways: {}".format(len(ways.values())))

    # preprocess nodes, add some properties to them
    helper.set_node_type(ways, nodes)
    helper.color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    helper.color_ways(ways, nodes, ways_colors, nodes_colors, default="black")
    colored_labels = helper.color_highways(ways, nodes)
    log("Nodes preprocessed sucessfully.")

    #### Get only residential streets and extract some data from them
    tags = {"highway": obtain_data_from}
    _nodes, _ways = helper.filter_by_tag(nodes, ways, tags)

    _output = "_temp.osm"
    handler.write_data(_output, _nodes.values(), _ways.values())
    log("Obtaining 1st round of cycles from: {}".format(tags))
    _cycles = helper.get_cycles(_output)
    handler.delete_file(_output)
    total_cycles = len(_cycles)

    min_area, max_area, avg_area, std_area = helper.get_cycles_data(nodes,
                                                                        _cycles)
    cycle_data = {"min_area": min_area,
             "max_area": max_area,
             "avg_area": avg_area,
             "std_area": std_area}
    log(cycle_data)

    ##### Get only main roads to execute our parcel generation on them
    tags = {"highway": generate_on}
    #tags = {"highway":None}
    nodes, ways = helper.filter_by_tag(nodes, ways, tags)

    _output = "_temp.osm"
    handler.write_data(_output, nodes.values(), ways.values())
    log("Obtaining 2nd round of cycles from: {}".format(tags))
    cycles = helper.get_cycles(_output)
    handler.delete_file(_output)

    cycles = helper.remove_nonempty_cycles(original_nodes, cycles)
    print("Total empty cycles to generate on: {}".format(len(cycles)))

    plot(nodes, ways)

    ##### Filter cycles that do not have minimum area or ratio
    _cycles = []
    for c in cycles:
        largest, shortest = helper.get_obb_data(nodes, c)
        ratio = shortest/largest
        area = helper.get_area([nodes[n_id].location for n_id in c])
        #print("Area: {:0.2f}, Ratio: {:0.2f}, Largest: {}, Shortest: {}".format(area, shortest/largest, largest, shortest))
        #if area < 3000 or ratio < 0.25: continue
        _cycles.append(c)
    cycles = _cycles


    for cycle in cycles:
       #generate_parcel_minarea(nodes, ways, cycle, cycle_data)
       generate_parcel_density(nodes, ways, cycle, 7)
       print("")
       #break

    handler.write_data("{}_output.osm".format(input),
                                                nodes.values(),ways.values())
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
    colored_labels = helper.color_highways(ways, nodes)
    plot(nodes, ways, tags=plot_tags, ways_labels=colored_labels)

if __name__ == '__main__':
    main()
