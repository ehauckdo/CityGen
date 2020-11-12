import optparse
import os, sys
import logging
from lib.logger import log
import lib.Individual as Individual
import lib.evolution as evo
import lib.helper as helper
import lib.handler as handler
import lib.plotter as plotter
import lib.trigonometry as trig
import pprint
from parcel import generate_parcel_density
from classifier.model import evaluate

logging.basicConfig(level=logging.INFO, filemode='w', filename='_main.log')

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
    output = "{}_output.osm".format(input)
    log("Reading OSM file '{}'...".format(input))

    #
    # Load data
    #
    nodes, ways = handler.extract_data(input)
    helper.update_id_counter(nodes.values())

    #
    # Fetch road cycles and then filter for road cycles that have no road
    # nodes inside and for cycles that have a minimum area/ratio
    #
    road_nodes, road_ways = helper.filter_by_tag(nodes, ways, {"highway":None})
    _output = "{}_roads_only.osm".format(input)
    handler.write_data(_output, road_nodes.values(), road_ways.values())
    road_cycles = helper.get_cycles(_output)
    log("All road cycles identified in {}: {}".format(input, len(road_cycles)))

    _output = "{}_roads_data".format(input)
    usable_cycles = helper.load(_output)
    if usable_cycles == None:
        log("Fetching empty road cycles of {}...".format(input))
        usable_cycles = helper.remove_nonempty_cycles(road_nodes, road_cycles)
        helper.save(usable_cycles, _output)
    else:
        log("Loaded empty road cycles from data file {}".format(_output))

    log("Number of empty cycles identified: {}".format(len(usable_cycles)))

    ##### Filter cycles that do not have minimum area or ratio
    _cycles = []
    for c in usable_cycles:
        largest, shortest = helper.get_obb_data(nodes, c)
        ratio = shortest/largest
        area = helper.get_area([nodes[n_id].location for n_id in c])
        #print("Area: {:0.2f}, Ratio: {:0.2f}, Largest: {}, Shortest: {}".format(area, shortest/largest, largest, shortest))
        if area < 3000 or ratio < 0.25: continue
        _cycles.append(c)
    usable_cycles = _cycles

    #
    # Parse data into a dict structure
    #
    cycles = {}
    for i in range(len(usable_cycles)):
        cycles[i] = {"n_ids":usable_cycles[i]}

    #
    # Calculate centroid of each cycle
    #
    log("Calculating centroid for each cycle...")
    for i in cycles:
        centroid = helper.centroid([road_nodes[n_id].location for n_id in
                                                        cycles[i]["n_ids"]])
        cycles[i]["centroid"] = centroid

    #
    # Set neighbors for each cycle by selecting the 3 closest cycles from it
    #
    # log("Calculating nearest neighbours for each cycle.")
    # for i in range(len(cycles)):
    #     distances = []
    #     for j in range(len(cycles)):
    #         if i == j: continue
    #         dist = trig.dist(*cycles[i]["centroid"], *cycles[j]["centroid"])
    #         distances.append((dist,j))
    #     distances = [id for coord, id in sorted(distances)]
    #     cycles[i]["neighbors"] = distances[:3]
    #     # pp = pprint.PrettyPrinter(indent=4)
    #     # print("Final cycle: {}".format(i))
    #     # pp.pprint(cycles[i])

    #
    # Set neighbors for each cycle by calculating a MST connecting all cycles
    #
    _output = "{}_neighbor_data".format(input)
    neighbor_values = helper.load(_output)

    if neighbor_values == None:
        log("Computing neighbors with MST...")
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
        log("Loaded neighbors from MST data file {}".format(_output))

    for i in neighbor_values:
        cycles[i]["neighbors"] = neighbor_values[i]

    #
    # Get building density for each cycle
    #
    _output = "{}_building_density_data".format(input)
    density = helper.load(_output)
    if density == None:
        log("Fetching building density data...")
        density = {}
        for c_id, cycle in cycles.items():
            d = helper.building_density(nodes, ways, cycle["n_ids"])
            density[c_id] = d
        helper.save(density, _output)
    else:
        log("Loaded building density data from file {}".format(_output))

    for c_id, d in density.items():
        cycles[c_id]["density"] = len(d)

    sys.exit()

    max_density = max([len(d) for c_id, d in density.items()])
    max_density = 20 if max_density == 0 else max_density

    #
    # Save indexes of cycles that have no buildings on them. We will operate
    # on these cycles and leave the ones with buildings alone.
    #
    chrom_idx, neigh_idx = [], []
    for idx in cycles:
        if cycles[idx]["density"] == 0:
            chrom_idx.append(idx)
            neigh_idx.append(cycles[idx]["neighbors"])

    full_chrom = [cycles[i]["density"] for i in cycles]
    # print("full_chrom: ")
    # print(" ".join(str(c) for c in full_chrom))
    #
    # print("chrom_idx: ")
    # print(" ".join(str(c) for c in chrom_idx))
    #
    # print("neigh_idx: ")
    # print(" ".join(str(c) for c in neigh_idx))

    helper.set_node_type(ways, nodes)
    helper.color_nodes(nodes.values(), "black")
    ways_colors = nodes_colors = {"building":"red", "highway":"black"}
    helper.color_ways(ways, nodes, ways_colors, nodes_colors, default="black")
    colored_labels = helper.color_highways(ways, nodes)
    #plotter.plot(nodes, ways, tags=[("highway",None)])

    #
    # Easy to visualize plot of the density
    #
    buildings = {}
    for c_id, d in density.items():
        buildings.update(d)
    plotter.plot_cycles_w_density(nodes, cycles, buildings)
    #plotter.plot(nodes, ways)

    print("Parcel densities: ")
    print(full_chrom)
    print("Fitness: {}".format(evo.fitness(full_chrom, chrom_idx, neigh_idx)))

    # #
    # # Manual setting of densities to compare against evolution
    # #
    # import random
    # ind = Individual.Individual(full_chrom)
    # ind.fitness = evo.fitness(full_chrom, chrom_idx, neigh_idx)
    # print("Fitness: {}".format(ind.fitness))
    #
    # completed = []
    # for i in range(100):
    #     for c_idx, n_idx_list in zip(chrom_idx, neigh_idx):
    #         print("Inspecting c_idx {} with neighbors {}".format(c_idx, n_idx_list))
    #         if full_chrom[c_idx] == 0 and max([full_chrom[n_idx] for n_idx in n_idx_list]) == 0:
    #                 continue
    #         if full_chrom[c_idx] == 0:
    #             maxi = max([full_chrom[n_idx] for n_idx in n_idx_list])
    #             new_density = maxi #random.randint(int(maxi*0.8), int(maxi*1.2))
    #             full_chrom[c_idx] = new_density
    #             completed.append(c_idx)
    #     ind.fitness = evo.fitness(full_chrom, chrom_idx, neigh_idx)
    #     print("Fitness: {}".format(ind.fitness))
    # print("Untouched nodes: {}".format([x for x in chrom_idx if x not in completed]))
    #
    # print("Full chrom: ")
    # print(full_chrom)
    # ind.fitness = evo.fitness(full_chrom, chrom_idx, neigh_idx)
    # print("Fitness: {}".format(ind.fitness))
    #
    # for c in chrom_idx:
    #     cycles[c]["density"] = full_chrom[c]
    #     cycle = cycles[c]["n_ids"]
    #     print("Cycle: {}".format(cycle))
    #     density = cycles[c]["density"]
    #     density = density - 1 if density > 0 else 0
    #     generate_parcel_density(nodes, ways, cycle, density)

    #
    # Initialize a pop for cycles
    #
    # log("Initializing population...")
    # pop = evo.initialize_pop(full_chrom, chrom_idx, neigh_idx,
    #                             pop_size=10, min_range=0,
    #                             max_range=max_density)
    #
    # #log("Pop[-1] fitness: {}".format(evo.evaluate(pop[-1])))
    # #
    # # Execute some sort of evolution
    # #
    # log("Running evolutionary process...")
    # evo.generation(pop, chrom_idx, neigh_idx,
    #                 min_range=0, max_range=max_density, generations=10000)
    #
    # #print("my indiv: {}".format(pop[-1]))
    #
    # # Get best individual from evolution process
    # best_ind = sorted(pop, key=lambda i: i.fitness)[0]
    # #print("Best individual: {}".format(best_ind))
    #
    # print("Parcel densities for best individual: ")
    # print(best_ind.chromosome)
    # print("Fitness: {}".format(evo.fitness(best_ind.chromosome,
    #                                                     chrom_idx, neigh_idx)))
    #
    # # Generate on top of best individual
    # for c in chrom_idx:
    #     cycle = cycles[c]["n_ids"]
    #     #print("Cycle: {}".format(cycle))
    #     density = best_ind.chromosome[c]
    #     density = density - 1 if density > 0 else 0
    #     generate_parcel_density(nodes, ways, cycle, density)
    #
    #
    # plotter.plot(nodes, ways)
    # handler.write_data(output, nodes.values(), ways.values(), -0.002)
    # print(output)
    # acc = evaluate(output)
    # print("Accuracy Output: {}".format(acc))
    #
    # acc = evaluate(input)
    # print("Accuracy Input: {}".format(acc))
    # log("Execution finished succesfully.")

if __name__ == '__main__':
    main()
