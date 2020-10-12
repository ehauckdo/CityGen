import os, sys
import handler
import optparse
import numpy as np
import trigonometry as trig
import logging
import helper
import building
import obb
from lib.logger import elapsed, log
from lib.plotter import plot

total = 0
created = 0

logging.basicConfig(level=logging.DEBUG, filemode='w', filename='_main.log')
#logging.getLogger().addHandler(logging.StreamHandler())

def generate_parcel(nodes, ways, cycle, cycle_data):
    # TODO: use a more intelligent approach like the one in this answer to get
    # a minimum size for our pacels: https://stats.stackexchange.com/a/49823
    def get_lower(avg, std, multiplier=0.5):
        lower_a = -1
        while lower_a < 0:
            lower_a = avg - std*multiplier
            multiplier -= 0.05
            if multiplier < 0: raise Exception
        return lower_a

    lower_a = get_lower(cycle_data["avg_area"],cycle_data["std_area"]) * 3
    upper_a = lower_a * 1.5
    _nodes, _ways = {}, {}
    log("\nLower area bound: {}\nUpper area bound: {}".format(lower_a, upper_a))
    points = [n.location for n_id, n in nodes.items() if n_id in cycle]
    area = helper.get_area(points)

    print("Processing cycle: ")
    polygon = []
    for n_id in cycle:
        print("id {}: \t{}".format(n_id, nodes[n_id].location))
        polygon.append(nodes[n_id].location)
    log("\nCurrent cycle area: {:.10f}".format(area))

    # # returns 2D obb, uses the PCA/covariance/eigenvector method
    # # good results for general shapes but TERRIBLE for rectangles/squares
    # box = obb.get_OBB(polygon)

    # # returns 3D obb, uses the PCA/covariance/eigenvector method
    # # good results for general shapes but TERRIBLE for rectangles/squares
    # from pyobb.obb import OBB
    # obb = OBB.build_from_points(polygon)
    # indexes = range(8)#[1, 2, 5, 6]
    # box = [(obb.points[i][0],obb.points[i][1]) for i in indexes]

    # returns 2D obb, uses convex hulls
    # yields decent results for symmetric shapes such as rectangles/squares
    box = obb.minimum_bounding_rectangle(np.array(polygon))
    #print("Box: {}".format(box))

    # ==== plot nodes from obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n_ids = []
    # for lon, lat in box:
    #     n = building.new_node(lon, lat)
    #     n_ids.append(n.id)
    #     _nodes[n.id] = n
    # w = building.new_way(n_ids + n_ids[:1], {"highway":"primary"})
    # _ways[w.id] = w
    # ====

    def largest_edge(polygon):
        if len(polygon) < 2: return None
        largest = (0, None)
        p_size = len(polygon)
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i+1)%p_size]
            dist = trig.dist(p1[0], p1[1], p2[0], p2[1])
            #print("Length {}: between points {}".format(dist, (p1,p2)))
            if dist > largest[0]:
                largest = (dist, (p1, p2), (polygon[(i+2)%p_size], polygon[(i+1+2)%p_size]))
        return *largest[1], *largest[2]

    def get_midpoint(p1, p2):
        x = p1[0] + (p2[0] - p1[0])/2
        y = p1[1] + (p2[1] - p1[1])/2
        return x, y

    p1, p2, p1_opposite, p2_opposite = largest_edge(box)
    # print("Largest: {}".format((p1, p2)))
    # print("Opposite: {}".format((p1_opposite, p2_opposite)))

    midpoint = get_midpoint(p1, p2)
    midpoint_opposite = get_midpoint(p1_opposite, p2_opposite)
    # print("Midpoint: {}".format(midpoint))
    # print("Midpoint Opposite: {}".format(midpoint_opposite))

    # extend the lines a little bit just to make sure they will
    # intersect with the edges of the polygon
    midpoint_opposite = trig.extend_line(*midpoint, *midpoint_opposite)
    midpoint = trig.extend_line(*midpoint_opposite, *midpoint)

    # ==== plot nodes from the perpendicular line to obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n1 = building.new_node(*midpoint)
    # _nodes[n1.id] = n1
    # n2 = building.new_node(*midpoint_opposite)
    # _nodes[n2.id] = n2
    # w = building.new_way([n1.id, n2.id], {"highway":"primary"})
    # _ways[w.id] = w
    # ====

    p3 = midpoint
    p4 = midpoint_opposite
    p_size = len(polygon)
    intersected = []

    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i+1)%p_size]

        intersect = trig.my_intersect(*p1, *p2, *p3, *p4)
        if intersect:
            # print("Intersected point {} between nodes {} and {}".format(
            #     intersect, p1, p2))
            intersected.append((intersect,i))

    if len(intersected) > 2:
        return   # this polygon is a bit more complex
                 # than what we hoped for, so just skip it

    if len(intersected) < 2:
        # for some reason we did not manage to find the two edges of the
        # polygon that intersect with the line splitting the OBB in two.
        # this is not meant to happen
        log("Partitioning with OBB failed for cycle {}".format(cycle), "WARN")
        return

    # get the two edges that intersect with the line dividing the OBB
    # and create two nodes and a way connecting them
    pos, polygon_index = intersected[0]
    n1 = building.new_node(*pos)
    nodes[n1.id] = n1
    polygon.insert((polygon_index+1)%len(polygon), pos)

    pos, polygon_index = intersected[1]
    n2 = building.new_node(*pos)
    nodes[n2.id] = n2
    polygon.insert((polygon_index+2)%len(polygon), pos)

    w = building.new_way([n1.id, n2.id], {"highway":"primary"})
    ways[w.id] = w

    #_nodes.update(nodes)
    #_ways.update(ways)

    print("New Polygon: ")
    for point in polygon:
        print(point)

    p1_index = intersected[0][1]+1
    p2_index = (intersected[1][1]+1)%(len(cycle))
    print("P1: {}, P2: {}".format(p1_index, p2_index))

    subcycle1 = [n1.id]
    it = p1_index
    while it != p2_index:
        subcycle1.append(cycle[it])
        it = (it+1)%len(cycle)
    subcycle1.append(n2.id)

    subcycle2 = [n2.id]
    it = p2_index
    while it != p1_index:
        subcycle2.append(cycle[it])
        it = (it+1)%len(cycle)
    subcycle2.append(n1.id)

    print("Subcycle1: ")
    subpolygon1 = []
    for n_id in subcycle1:
        print("{}: {}".format(n_id, nodes[n_id].location))
        #subpolygon1.append(nodes[n_id].location)

    print("Subcycle2: ")
    subpolygon2 = []
    for n_id in subcycle2:
        print("{}: {}".format(n_id, nodes[n_id].location))
        #subpolygon2.append(nodes[n_id].location)


    colored_labels = helper.color_highways(ways,nodes)
    plot(nodes, ways, tags=None, ways_labels=colored_labels)

    #input("Press any key to continue...")

    points = []
    for n_id in subcycle1:
        points.append(nodes[n_id].location)
    print("Subcycle Points for Area Calculation:")
    for p in points:
        print(p)
    area = helper.get_area(points)
    print("Area of Subycle1: {:.10f} (lower_a: {:.10f})".format(area, lower_a))
    if area > lower_a:
        print("Executing recursion Sub1...")
        generate_parcel(nodes, ways, subcycle1, cycle_data)

    points = []
    for n_id in subcycle1:
        points.append(nodes[n_id].location)
    area = helper.get_area(points)
    print("Area of Subycle2: {:.10f} (lower_a: {:.10f})".format(area, lower_a))
    if area > lower_a:
        print("Executing recursion Sub2...")
        generate_parcel(nodes, ways, subcycle2, cycle_data)

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

    obtain_data_from = ["residential","unclassified"]
    generate_on = ["trunk","primary","secondary","tertiary"]

    nodes, ways = handler.extract_data(input)
    log("Data read sucessfully.")
    log("Total nodes: {}".format(len(nodes.values())))
    log("Total ways: {}".format(len(ways.values())))

    min_lat, min_lon, max_lat, max_lon = handler.get_bounds(nodes.values())
    matrix, lon_range, lat_range = helper.split_into_matrix(min_lat,
                                            min_lon, max_lat, max_lon, nodes)

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
    cycles = helper.get_cycles(_output)
    handler.delete_file(_output)

    min_lat, min_lon, max_lat, max_lon = handler.get_bounds(nodes.values())
    matrix, lon_range, lat_range = helper.split_into_matrix(min_lat,
                                            min_lon, max_lat, max_lon, nodes)

    cycles = helper.remove_nonempty_cycles(nodes, cycles, matrix,
                                                    lon_range, lat_range)
    print("Total empty cycles to generate on: {}".format(len(cycles)))

    for cycle in cycles:
       generate_parcel(nodes, ways, cycle, cycle_data)
       print("")
       #break

    handler.write_data("{}_output.osm".format(input),
                                                nodes.values(),ways.values())
    plot_tags = [("highway",None)]
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
