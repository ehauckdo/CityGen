import optparse
import os, sys
import logging
from lib.logger import log
import lib.mapelites.Individual as Individual
import lib.mapelites.evolution as evo
import lib.helper as helper
import lib.handler as handler
import lib.plotter as plotter
import lib.trigonometry as trig
import pprint
from lib.parcel import generate_parcel_density
from classifier.model import load_model, accuracy

logging.basicConfig(level=logging.INFO, filemode='w', filename='_log_main')

# supress tensorflow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# this function adds some properties to nodes and ways objects for
# the a better plotting, no practical use for generation
def set_colors(nodes, ways):
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    helper.set_node_type(ways, nodes)
    helper.color_nodes(nodes.values(), "black")
    helper.color_ways(ways, nodes, ways_colors, nodes_colors, default="black")

# this function filters all nodes and ways that belong to roads
# and returns all cycles identified (road_cycles) in them and the subset
# of those cycles (usable_cycles) that have no other road nodes inside them
def get_roads(nodes, ways, input):
    road_nodes, road_ways = helper.filter_by_tag(nodes, ways, {"highway":None})
    _output = "{}_roads_only.osm".format(input)
    handler.write_data(_output, road_nodes.values(), road_ways.values())
    road_cycles = helper.get_cycles(_output)
    log("All road cycles in {}: {}".format(input, len(road_cycles)), "DEBUG")

    _output = "{}_roads_data".format(input)
    usable_cycles = helper.load(_output)
    if usable_cycles == None:
        log("Computing empty road cycles of {}...".format(input), "DEBUG")
        usable_cycles = helper.remove_nonempty_cycles(road_nodes, road_cycles)
        helper.save(usable_cycles, _output)
    else:
        log("Empty road cycles from file {}".format(_output), "DEBUG")

    log("Number of usable cycles identified: {}".format(len(usable_cycles)),
                                                                       "DEBUG")
    return road_nodes, road_ways, road_cycles, usable_cycles

# filter cycles that do not have a minimum area (defined manually)
# areas under these thresholds would be very difficult to generate placements
def filter_small_cycles(nodes, cycles):
    _cycles = []
    for c in cycles:
        largest, shortest = helper.get_obb_data(nodes, c)
        ratio = shortest/largest
        area = helper.get_area([nodes[n_id].location for n_id in c])
        #print("Area: {:0.2f}, Ratio: {:0.2f}, Largest: {}, Shortest: {}".format(area, shortest/largest, largest, shortest))
        if area < 3000 or ratio < 0.25: continue
        _cycles.append(c)
    return _cycles

# given a list of cycles, find the minimum spanning tree connecting their
# centroids and add neighbouring nodes from this tree to the data in cycles
def compute_neighbors_MST(cycles, input):
    import lib.trigonometry as trig
    _output = "{}_neighbor_data".format(input)
    neighbor_values = helper.load(_output)

    if neighbor_values == None:
        log("Computing neighbors with MST...", "DEBUG")
        neighbor_values = {}
        for i in cycles:
            neighbor_values[i] = []

        added = [0]
        while len(added) != len(cycles):
            distances = []
            for i in range(len(cycles)):
                for j in range(len(cycles)):
                    if i in added and j not in added:
                       dist = trig.dist(*cycles[i]["centroid"], *cycles[j]["centroid"])
                       distances.append((dist,i,j))
            distances = sorted(distances)
            dist, i, j = distances.pop(0)
            neighbor_values[i].append(j)
            neighbor_values[j].append(i)
            added.append(j)
        helper.save(neighbor_values, _output)
    else:
        log("Loaded MST data from file {}".format(_output), "DEBUG")

    for i in neighbor_values:
        cycles[i]["neighbors"] = neighbor_values[i]

# given a list of cycles, find the n closest cycles to them from their
# centroids and add them as neighbouring cycles (alternative to MST)
def compute_neighbors_closest(cycles, n=3):
    import lib.trigonometry as trig
    log("Calculating nearest {} neighbours for each cycle.".format(n), "DEBUG")
    for i in range(len(cycles)):
        distances = []
        for j in range(len(cycles)):
            if i == j: continue
            dist = trig.dist(*cycles[i]["centroid"], *cycles[j]["centroid"])
            distances.append((dist,j))
        distances = [id for coord, id in sorted(distances)]
        cycles[i]["neighbors"] = distances[:n]

def compute_centroids(cycles, nodes):
    for i in cycles:
        centroid = helper.centroid([nodes[n_id].location for n_id in
                                                        cycles[i]["n_ids"]])
        cycles[i]["centroid"] = centroid

# compute density and number of buildings for each cycle in cycles
def compute_building_density(cycles, input, nodes, ways):
    _output = "{}_building_density_data".format(input)
    density = helper.load(_output)
    if density == None:
        log("Computing building density data...", "DEBUG")
        density = {}
        for c_id, cycle in cycles.items():
            d = helper.building_density(nodes, ways, cycle["n_ids"])
            density[c_id] = d
        helper.save(density, _output)
    else:
        log("Loaded building density from file {}".format(_output), "DEBUG")

    for c_id, d in density.items():
        nodes_coord = [nodes[x].location for x in cycles[c_id]["n_ids"]]
        cycles[c_id]["density"] = len(d)
        cycles[c_id]["area"] = helper.get_area(nodes_coord)/1000000 # in km2
        cycles[c_id]["actual_density"] = len(d) / cycles[c_id]["area"]
        cycles[c_id]["buildings"] = d

# given the original nodes and ways from an OSM file and an individual with a
# number of buildings for each cycle, generate that individual as an OSM file
def generate_ind(nodes,ways,cycles,ind,chrom_idx,output="data/ind.osm"):
    import copy
    _nodes = copy.deepcopy(nodes)
    _ways = copy.deepcopy(ways)
    for idx in chrom_idx:
        cycle_data = cycles[idx]
        cycle_nodes = cycle_data["n_ids"]
        density = ind.chromosome[idx]
        generate_parcel_density(_nodes, _ways, cycle_nodes, density)
    handler.write_data(output,_nodes.values(),_ways.values())
    return _nodes, _ways

def parse_args(args):
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-i', action="store", type="string", dest="filename",
	   help="OSM input file", default="data/smaller_tsukuba.osm")
    parser.add_option('-m', action="store", type="string", dest="model",
        help="Model trained on cities", default="classifier/Tsukuba.hdf5")
    parser.add_option('-d', action="store", type="int", dest="density",
        help="Maximum initial density per cell for population", default=10)
    parser.add_option('-a', action="store", type="float", dest="minarea",
        help="Minimum area necessary for a building",default=(1500/5000000))
    parser.add_option('-o', action="store", type="string", dest="output_folder",
        help="Output folder", default="output")
    return parser.parse_args()

def main():
    os.system('clear')
    log("Starting program...")

    opt, args = parse_args(sys.argv[1:])
    input = opt.filename
    output = "{}_output.osm".format(input)
    output = opt.output_folder
    helper.create_folder(output)

    ##########################
    # Loading OSM data
    ##########################
    log("Loading OSM file '{}'...".format(input))
    nodes, ways = handler.extract_data(input)
    helper.update_id_counter(nodes.values())
    set_colors(nodes, ways)

    ##########################
    # Fetching cycles
    ##########################
    r_nodes, r_ways, r_cycles, cycles = get_roads(nodes, ways, input)
    cycles = filter_small_cycles(nodes, cycles)
    cycles = {id:{"n_ids":cycle} for id, cycle in enumerate(cycles)}

    ##########################
    # Compute various data for each cycle
    ##########################
    compute_centroids(cycles, nodes)
    # compute_neighbors_closest(cycles, 3)
    compute_neighbors_MST(cycles, input)
    compute_building_density(cycles, input, nodes, ways)

    ##########################
    # Easy to visualize plot (only roads, then roads+buildings)
    ##########################
    # buildings = {}
    # for c_id in cycles:
    #    try:
    #        buildings.update(cycles[c_id]["buildings"])
    #    except:
    #        print("Failed to fetch density of {}".format(c_id))
    #
    # plot(nodes, ways, tags=[("highway",None)])
    # plot_cycles_w_density(nodes, cycles, buildings)
    # sys.exit()

    ##########################
    # Initialize data for evolution
    ##########################
    chrom = [cycles[i]["density"] for i in cycles]
    areas = [cycles[i]["area"] for i in cycles]
    chrom_idx = [idx for idx in cycles if cycles[idx]["density"] == 0]
    neigh_idx = [cycles[idx]["neighbors"] for idx in cycles
                                            if cycles[idx]["density"] == 0]
    # maximum building number based on area
    maximum_buildings = sum(areas)/opt.minarea
    # maximum building number set manually
    maximum_buildings = 50

    # calculating current existing number of buildings for reference
    # (existing buildings also count for maxi number of buildings in the area)
    existing_buildings = 0
    for i in range(len(chrom)):
        if i not in chrom_idx:
            existing_buildings += chrom[i]
    log("Current and maximum number of buildings: {:.2f}, {:.2f}".format(
                                    existing_buildings, maximum_buildings))

    ##########################
    # Run evolution
    ##########################
    pop = evo.initialize_pop_ME(chrom, chrom_idx, neigh_idx, areas,
                             max_buildings=maximum_buildings, pop_size=10)

    evo.generation_ME(pop, chrom_idx, neigh_idx, areas,
                     max_buildings=maximum_buildings, generations=200)

    ##########################
    # Parse individuals into osm files
    # and get similarity from model
    ##########################
    top_individuals = evo.top_individuals_ME(pop)

    top_acc = (0,0)
    pop_range = 10
    output_file = "{}/experiment_top[{}][{}].osm"
    accuracies = [[[] for i in range(pop_range)] for j in range(pop_range)]
    log("Starting evaluation process...")
    model = load_model(opt.model)
    file1 = open("_log_accuracies".format(output),"w")
    for i in range(len(top_individuals)):
        for j in range(len(top_individuals[i])):
            pop = top_individuals[i][j]
            acc = 0
            if len(pop) > 0:
                top_ind = top_individuals[i][j][0]
                ind_file = output_file.format(output, i,j)
                log("Saving generated output to {}...".format(ind_file))
                _n, _w = generate_ind(nodes,ways,cycles,top_ind,
                                       chrom_idx,neigh_idx,ind_file)
                acc = accuracy(ind_file, model)
                log("Accuracy: {:.5f}".format(acc))

            accuracies[i][j].append(acc)
            if accuracies[i][j] > accuracies[top_acc[0]][top_acc[1]]:
                top_acc = (i,j)
            file1.write("{},{},{}\n".format(i,j,acc))

    file1.close()
    for i in range(len(accuracies)):
        for j in range(len(accuracies[i])):
            print("Accuracies for [{}][{}]: {}".format(i,j, accuracies[i][j]))

    best_output = output_file.format(output, top_acc[0], top_acc[1])
    print("Best output in terms of similarity: {}".format(best_output))

    ##########################
    # Plot of the output (optional)
    ##########################
    # _nodes, _ways = handler.extract_data(best_output)
    # set_colors(_nodes, _ways)
    # plot(_nodes, _ways)

    log("Generation finished.\n\n")

if __name__ == '__main__':
    main()
