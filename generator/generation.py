import optparse
import os, sys
import logging
from lib.logger import log
from lib.Individual import Individual
import lib.evolution as evo
import lib.helper as helper
import lib.handler as handler

logging.basicConfig(level=logging.DEBUG, filemode='w', filename='_main.log')

def parseArgs(args):
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-i', action="store", type="string", dest="filename",
		help="OSM input file", default="data/smaller_tsukuba.osm")
	return parser.parse_args()

def main():

    os.system('clear')
    opt, args = parseArgs(sys.argv[1:])
    input = opt.filename
    output = "output_{}".format(input)
    log("Reading OSM file '{}'...".format(input))

    #
    # Load data & obtain cycles
    #
    nodes, ways = handler.extract_data(input)
    helper.update_id_counter(nodes.values())

    road_cycles = helper.get_cycles_highway(input)
    empty_cycles = helper.remove_nonempty_cycles(nodes, road_cycles)

    print("All Cycles: {}".format(len(road_cycles)))
    print("Empty Cycles: {}".format(len(empty_cycles)))

    #
    # Initialize a pop for cycles
    #
    pop = evo.initialize_pop(10)
    for i in pop:
        log(i)

    log("Pop[-1] fitness: {}".format(evo.evaluate(pop[-1])))

    #
    # Execute some sort of evolution
    #

    evo.generation(pop)
    log("Execution finished succesfully.")

if __name__ == '__main__':
    main()
