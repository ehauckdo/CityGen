import optparse
import os, sys, logging
from lib.logger import log
import lib.handler as handler
import lib.helper as helper
import lib.evolution as evo
from parcel import generate_parcel_density
from lib.plotter import plot, plot_cycles_w_density
from classifier.model import load_model, accuracy
import copy

# set up logging
logging.basicConfig(level=logging.INFO, filemode='w', filename='_main.log')

# supress tensorflow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

def set_colors(nodes, ways):
    # this is just for helping in plotting
    # no practical use during execution
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    helper.set_node_type(ways, nodes)
    helper.color_nodes(nodes.values(), "black")
    helper.color_ways(ways, nodes, ways_colors, nodes_colors, default="black")
def generate_ind(nodes,ways,cycles,ind,chrom_idx,neigh_idx,output="data/ind.osm"):
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
        #print("cycle_id {}: b{}, a{:.2f}, d{:.2f}".format(c_id, len(d), cycles[c_id]["area"], cycles[c_id]["actual_density"]))
        cycles[c_id]["buildings"] = d
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
def compute_centroids(cycles, nodes):
    for i in cycles:
        centroid = helper.centroid([nodes[n_id].location for n_id in
                                                        cycles[i]["n_ids"]])
        cycles[i]["centroid"] = centroid
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
def parse_args(args):
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-i', action="store", type="string", dest="filename",
        help="OSM input file", default=None)
    parser.add_option('-m', action="store", type="string", dest="model",
        help="Model trained on cities", default=None)
    parser.add_option('-d', action="store", type="int", dest="density",
        help="Maximum initial density per cell for population", default=10)
    parser.add_option('-a', action="store", type="float", dest="minarea",
        help="Minimum area necessary for a building",default=(1500/1000000))
    return parser.parse_args()

def main():
    os.system('clear')
    log("Starting experiment...")

    opt, args = parse_args(sys.argv[1:])
    input = opt.filename
    model = opt.model

    ###########################
    # Loading model data
    ###########################
    log("Loading model file: {}...".format(model))
    #model = load_model(opt.model)

    ##########################
    # Loading OSM data
    ##########################
    log("Loading OSM file '{}'...".format(input))
    nodes, ways = handler.extract_data(input)
    helper.update_id_counter(nodes.values())
    set_colors(nodes, ways)

    log("Computing road information and cycles...")
    r_nodes, r_ways, r_cycles, cycles = get_roads(nodes, ways, input)
    cycles = filter_small_cycles(nodes, cycles)

    cycles = {id:{"n_ids":cycle} for id, cycle in enumerate(cycles)}

    ##########################
    # Compute various data for each cycle
    ##########################
    compute_centroids(cycles, nodes)
    compute_neighbors_MST(cycles, input)
    compute_building_density(cycles, input, nodes, ways)

    ##########################
    # Easy to visualize plot
    ##########################
    buildings = {}
    for c_id in cycles:
       try: buildings.update(cycles[c_id]["buildings"])
       except: print("Failed to fetch density of {}".format(c_id))
    #plot_cycles_w_density(nodes, cycles, buildings)

    ##########################
    # Initialize data for experiment
    ##########################
    chrom = [cycles[i]["density"] for i in cycles]
    areas = [cycles[i]["area"] for i in cycles]
    chrom_idx = [idx for idx in cycles if cycles[idx]["density"] == 0]
    neigh_idx = [cycles[idx]["neighbors"] for idx in cycles
                                            if cycles[idx]["density"] == 0]

    initial_density = max([cycles[c_id]["density"] for c_id in cycles])
    initial_density = opt.density if initial_density == 0 else initial_density

    maximum_buildings = sum(areas)/opt.minarea
    maximum_density = maximum_buildings/sum(areas)
    log("Current and maximum building density of input: {:.2f}, {:.2f}".format(
                                    sum(chrom)/sum(areas), maximum_density))


    ##########################
    # Run evolution
    ##########################
    #evo.get_highest_error(chrom, chrom_idx, neigh_idx, maximum_buildings, areas)


    pop = evo.initialize_pop_ME(chrom, chrom_idx, neigh_idx, areas,
                             max_buildings=maximum_buildings, pop_size=300)


    evo.generation_ME(pop, chrom_idx, neigh_idx, areas,
                     max_buildings=maximum_buildings, generations=1000)

    sys.exit()
    top_individuals = evo.top_individuals_ME(pop)

    #best_ind = sorted(pop[0], key=lambda i: i.fitness)[0]

    ##########################
    # Parse individuals into osm files
    ##########################
    accuracies = [[] for x in range(10)]
    log("Starting evaluation process...")
    for i in range(len(top_individuals)):
        for j in range(len(top_individuals[i])):
            top_ind = top_individuals[i][j]
            ind_file = "{}_r{}_i{}_output.osm".format(input,i,j)
            _n, _w = generate_ind(nodes,ways,cycles,top_ind,
                                   chrom_idx,neigh_idx,ind_file)
            log("Saving of {} completed. Started evlaluation...".format(ind_file))
            acc = accuracy(ind_file, model)
            accuracies[i].append(acc)
            log("Evaluation complete. Acc: {:.5f}".format(acc))

            ##########################
            # Easy to visualize plot
            ##########################
            _b = copy.deepcopy(buildings)
            for w_id, w in _w.items():
                if "building" in w.tags and w_id not in ways:
                    _b[w_id] = w
            plot_cycles_w_density(_n, cycles, _b)

    for i in range(len(accuracies)):
        print("Accuracies for range {}: {}".format((i,i+1), accuracies[i]))

    # log("Saving generated output to disk...")
    # ind_file = "{}_output.osm".format(input)
    # _n, _w = generate_ind(nodes,ways,cycles,best_ind,chrom_idx,neigh_idx,ind_file)
    #log("Starting evaluation...")
    #acc = accuracy(ind_file, model)
    #print(acc)

    log("Experiment finished.\n\n")


if __name__ == '__main__':
    main()
