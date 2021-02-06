import optparse
import os, sys, logging
from lib.logger import log
import lib.handler as handler
import lib.helper as helper
import lib.mapelites.evolution as evo
from lib.parcel import generate_parcel_density
from lib.plotter import plot, plot_cycles_w_density
from classifier.model import load_model, accuracy
import copy

# set up logging
logging.basicConfig(level=logging.INFO, filemode='w', filename='_log_main')

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
        help="OSM input file", default="data/sumidaku.osm")
    parser.add_option('-m', action="store", type="string", dest="model",
        help="Model trained on cities", default="classifier/Tokyo.hdf5")
    parser.add_option('-d', action="store", type="int", dest="density",
        help="Maximum initial density per cell for population", default=10)
    parser.add_option('-a', action="store", type="float", dest="minarea",
        help="Minimum area necessary for a building",default=(1500/5000000))
    parser.add_option('-o', action="store", type="string", dest="output_folder",
        help="Output folder", default="output")
    return parser.parse_args()

def main():
    os.system('clear')
    log("Starting experiment...")

    opt, args = parse_args(sys.argv[1:])
    input = opt.filename
    model = opt.model
    output = opt.output_folder
    helper.create_folder(output)

    ###########################
    # Loading model data
    ###########################
    log("Loading model file: {}...".format(model))
    model = load_model(opt.model)

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
    log("Computing road information and cycles...")
    # use these functions to attempt to fetch cycles from
    # the road network graph of the input data
    # #r_nodes, r_ways, r_cycles, cycles = get_roads(nodes, ways, input)
    # cycles = filter_small_cycles(nodes, cycles)

    # fixed pre-fetched cycles for sumidaku
    cycles = [[1197987560, 1197987449, 1361175762, 1361175760, 1361175752, 1361176778],
                [1361175762, 1361175760, 1361175750, 1361175751],
                [1361175752, 1361175749, 1361176774, 1361175750, 1361175760],
                [1197987449, 1361179461, 1361179451, 1361175762],
                [1361179461, 1361179451, 1361179453, 1361179462],
                [1361179453, 1361179462, 1197987441, 1197985675],
                [1197987441, 1197985675, 1197987551, 1197987476],
                [1197987551, 1197987476, 1197987491, 1361179455],
                [1361179455, 1197987551, 1361179445, 1361179447],
                [1197987551, 1361179445, 1361179443, 1197985675],
                [1361179443, 1197985675, 1361179453, 1361179451, 1361175762, 1361175751],
                [1361179445, 1361179447, 1197985744, 1197987452],
                [1197987452, 1361179445, 1361179443, 1197985712],
                [1361179443, 1197985712, 1197985578, 1361175751],
                [1197985578, 1361175751, 1361175750, 1361176774, 3056577316],
                [3056577316, 1361176774, 1361175749, 1361176772, 1197985596],
                [1197985578, 3056577316, 1197985596, 1361179441, 1361179425, 1361179427, 1197985649],
                [1197985578, 1197985712, 1197985789, 1197985678, 1197985649],
                [1197985712, 1197985789, 5710118040, 1197987443, 1197987452],
                [1197987443, 1197987452, 1197985744, 1197985732, 1197985789],
                [1197985732, 2669680089, 2669680087, 1361179433],
                [2669680087, 2669680099, 5710118041, 5710118040, 1197987443, 2669680089],
                [5710118040, 5710118041, 1361179431, 1197985789],
                [1197985789, 1361179431, 1361179429, 1197985678],
                [1361179429, 1197985678, 1197985649, 1361179427],
                [1361179425, 1361179427, 2669681315, 2669681322],
                [2669681315, 2669681322, 1197985772, 2669681324, 1691781332],
                [2669681324, 1691781332, 1664321820, 2669681320],
                [1197985772, 2669681324, 2669681320, 1197845636, 7769008105],
                [1361179427, 2669681315, 1691781332, 1361179411, 2669680084, 1361179417, 1361179429],
                [1361179417, 1361179429, 1361179431, 5710118042, 1361179419],
                [1361179417, 1361179419, 2669680093, 1197985668, 2669681313, 2669680084],
                [2669680093, 1197985668, 2669680088, 2669680094],
                [2669680094, 2669680093, 1361179419, 5710118042, 5710118043],
                [5710118043, 5710118042, 1361179431, 5710118041, 2669680099],
                [2669680087, 1361179433, 252409712, 1197985792, 2669680088, 2669680094, 5710118043, 2669680099],
                [1197985792, 2669680088, 1197985668, 2669681323, 2669681317],
                [2669681323, 2669681317, 252409713, 1197845644],
                [1197845644, 2669681323, 1197985668, 2669681313, 2669681319],
                [2669681313, 2669681319, 1361179408, 1361179411, 2669680084],
                [1361179408, 1361179411, 1691781332, 1664321820],
                [1695023742, 7769008112, 1197845645, 1197845677, 1695023764],
                [1197845645, 1197845677, 1809711603, 1197845641, 1197845632, 1197845628, 1197845630],
                [1695023764, 1197845677, 1809711609, 1809711628],
                [1809711609, 1809711628, 1809711630, 1809711611],
                [1197845677, 1809711609, 1809711611, 1809711612, 1197845672, 1809711607, 1809711605, 1809711603],
                [1809711605, 1809711603, 1197845641, 1197845683, 1809711592],
                [1809711605, 1809711592, 1197845674, 1809711607],
                [1809711630, 1809711611, 1809711612, 1809711618, 1809711619, 1809711631],
                [1809711612, 1809711618, 1809711619, 1809711631, 1695023767, 1197845672],
                [1695023767, 1197845672, 1809711613, 1809711622, 1809711625, 1809711626, 1695023770],
                [1809711613, 1809711622, 1809711625, 1809711626, 1695023628, 1809711615, 1809711614],
                [1197845672, 1809711613, 1809711614, 1809711594, 1197845674, 1809711607],
                [1809711614, 1809711594, 1809711595, 1809711597, 1809711615],
                [1809711597, 1809711615, 1695023628, 1695023539, 1809711598]
                ]
    cycles = {id:{"n_ids":cycle} for id, cycle in enumerate(cycles)}

    ##########################
    # Compute various data for each cycle
    ##########################
    compute_centroids(cycles, nodes)
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
    # Initialize data for experiment
    ##########################
    chrom = [cycles[i]["density"] for i in cycles]
    areas = [cycles[i]["area"] for i in cycles]
    chrom_idx = [idx for idx in cycles if cycles[idx]["density"] == 0]
    neigh_idx = [cycles[idx]["neighbors"] for idx in cycles
                                            if cycles[idx]["density"] == 0]

    # maximum building number based on area
    maximum_buildings = sum(areas)/opt.minarea
    # maximum building number set manually
    maximum_buildings = 300

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
                     max_buildings=maximum_buildings, generations=50)

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

    log("Experiment finished.\n\n")

if __name__ == '__main__':
    main()
