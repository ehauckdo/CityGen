import os, sys
import lib.handler as handler
import optparse
import numpy as np
import lib.trigonometry as trig
import logging
import lib.helper as helper
import building
import random
import lib.obb as obb
from lib.logger import elapsed, log
from lib.plotter import plot

total = 0
created = 0

logging.basicConfig(level=logging.INFO, filemode='w', filename='_main.log')
#logging.getLogger().addHandler(logging.StreamHandler())

def insert_node_way(nodes, ways, p1, p2, created_node):
    for way in ways:
        if p1 in way.nodes and p2 in way.nodes:
            p1_index = way.nodes.index(p1)
            p2_index = way.nodes.index(p2)
            way.nodes.insert(p2_index, created_node)

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

    lower_a = get_lower(cycle_data["avg_area"],cycle_data["std_area"])
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
    log("Identified Box: {}".format(box))

    # ==== plot nodes from obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n_ids = []
    # for lon, lat in box:
    #     n = building.new_node(lon, lat)
    #     n_ids.append(n.id)
    #     nodes[n.id] = n
    # w = building.new_way(n_ids + n_ids[:1], {"highway":"primary"})
    # ways[w.id] = w
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

    def get_midpoint2(p1, p2, split=100):
        #x = p1[0] + (p2[0] - p1[0])/2
        #y = p1[1] + (p2[1] - p1[1])/2
        range = []
        x_range = np.linspace(p1[0], p2[0], split)
        y_range = np.linspace(p1[1], p2[1], split)
        range = [(x, y) for (x, y) in zip(x_range, y_range)]
        selected_index = random.randint( int(split*0.45), int(split*0.55))
        return range[selected_index]

    p1, p2, p1_opposite, p2_opposite = largest_edge(box)
    # log("Largest: {}".format((p1, p2)))
    # log("Opposite: {}".format((p1_opposite, p2_opposite)))

    midpoint = get_midpoint(p1, p2)
    midpoint_opposite = get_midpoint(p1_opposite, p2_opposite)
    # log("Midpoint: {}".format(midpoint))
    # log("Midpoint Opposite: {}".format(midpoint_opposite))

    # extend the lines a little bit just to make sure they will
    # intersect with the edges of the polygon
    midpoint_opposite = trig.extend_line(*midpoint, *midpoint_opposite)
    midpoint = trig.extend_line(*midpoint_opposite, *midpoint)

    # ==== plot nodes from the perpendicular line to obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n1 = building.new_node(*midpoint)
    # nodes[n1.id] = n1
    # n2 = building.new_node(*midpoint_opposite)
    # nodes[n2.id] = n2
    # w = building.new_way([n1.id, n2.id], {"highway":"primary"})
    # ways[w.id] = w
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
        log("Perpendicular line from OBB intersected with > 2 edges.")

        created_ids = []
        for pos, polygon_index in intersected:
            n = building.new_node(*pos)
            nodes[n.id] = n
            created_ids.append(n.id)
        w = building.new_way(created_ids, {"highway":"tertiary"})
        ways[w.id] = w

        colored_labels = helper.color_highways(ways,nodes)
        colored_labels = None
        plot(nodes, ways, tags=None, ways_labels=colored_labels)
        #input("Press any key to continue...")
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

    w = building.new_way([n1.id, n2.id], {"highway":"tertiary"})
    ways[w.id] = w

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
    for n_id in subcycle1:
        print("{}: {}".format(n_id, nodes[n_id].location))

    print("Subcycle2: ")
    for n_id in subcycle2:
        print("{}: {}".format(n_id, nodes[n_id].location))

    colored_labels = helper.color_highways(ways,nodes)
    #colored_labels = None
    plot(nodes, ways, tags=None, ways_labels=colored_labels)
    #input("Press any key to continue...")

    # generate parcel recursively in subcycle1
    points = []
    for n_id in subcycle1:
        points.append(nodes[n_id].location)
    area = helper.get_area(points)
    print("Area of Subycle1: {:.10f} (lower_a: {:.10f})".format(area, lower_a))
    if area > lower_a:
        print("Executing recursion Sub1...")
        generate_parcel(nodes, ways, subcycle1, cycle_data)
    else:
        # place building here
        created_nodes, created_ways = building.generate_offset_polygon_iterative(points)
        nodes.update(created_nodes)
        ways.update(created_ways)

    # generate parcel recursively in subcycle2
    points = []
    for n_id in subcycle2:
        points.append(nodes[n_id].location)
    area = helper.get_area(points)
    print("Area of Subycle2: {:.10f} (lower_a: {:.10f})".format(area, lower_a))
    if area > lower_a:
        print("Executing recursion Sub2...")
        generate_parcel(nodes, ways, subcycle2, cycle_data)
    else:
        created_nodes, created_ways = building.generate_offset_polygon_iterative(points)
        nodes.update(created_nodes)
        ways.update(created_ways)

def generate_parcel2(nodes, ways, cycle, partitions_left):

    _nodes, _ways = {}, {}
    points = [n.location for n_id, n in nodes.items() if n_id in cycle]
    area = helper.get_area(points)

    #print("Processing cycle: ")
    polygon = []
    for n_id in cycle:
        #print("id {}: \t{}".format(n_id, nodes[n_id].location))
        polygon.append(nodes[n_id].location)
    log("\nCurrent cycle area: {:.10f}".format(area), "DEBUG")

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
    log("Identified Box: {}".format(box), "DEBUG")

    # ==== plot nodes from obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n_ids = []
    # for lon, lat in box:
    #     n = building.new_node(lon, lat)
    #     n_ids.append(n.id)
    #     nodes[n.id] = n
    # w = building.new_way(n_ids + n_ids[:1], {"highway":"primary"})
    # ways[w.id] = w
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

    def get_midpoint2(p1, p2, split=100):
        #x = p1[0] + (p2[0] - p1[0])/2
        #y = p1[1] + (p2[1] - p1[1])/2
        range = []
        x_range = np.linspace(p1[0], p2[0], split)
        y_range = np.linspace(p1[1], p2[1], split)
        range = [(x, y) for (x, y) in zip(x_range, y_range)]
        selected_index = random.randint( int(split*0.45), int(split*0.55))
        return range[selected_index]

    p1, p2, p1_opposite, p2_opposite = largest_edge(box)
    # log("Largest: {}".format((p1, p2)))
    # log("Opposite: {}".format((p1_opposite, p2_opposite)))

    midpoint = get_midpoint(p1, p2)
    midpoint_opposite = get_midpoint(p1_opposite, p2_opposite)
    # log("Midpoint: {}".format(midpoint))
    # log("Midpoint Opposite: {}".format(midpoint_opposite))

    # extend the lines a little bit just to make sure they will
    # intersect with the edges of the polygon
    midpoint_opposite = trig.extend_line(*midpoint, *midpoint_opposite)
    midpoint = trig.extend_line(*midpoint_opposite, *midpoint)

    # ==== plot nodes from the perpendicular line to obb
    # ==== this is actually unnecessary, only doing it for the viz
    # n1 = building.new_node(*midpoint)
    # nodes[n1.id] = n1
    # n2 = building.new_node(*midpoint_opposite)
    # nodes[n2.id] = n2
    # w = building.new_way([n1.id, n2.id], {"highway":"primary"})
    # ways[w.id] = w
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
        log("Perpendicular line from OBB intersected with > 2 edges.", "DEBUG")

        created_ids = []
        for pos, polygon_index in intersected:
            n = building.new_node(*pos)
            nodes[n.id] = n
            created_ids.append(n.id)
        w = building.new_way(created_ids, {"highway":"residential"})
        ways[w.id] = w

        colored_labels = helper.color_highways(ways,nodes)
        colored_labels = None
        #plot(nodes, ways, tags=None, ways_labels=colored_labels)
        #input("Press any key to continue...")
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

    w = building.new_way([n1.id, n2.id], {"highway":"residential"})
    ways[w.id] = w

    #print("New Polygon: ")
    #for point in polygon:
    #    print(point)

    p1_index = intersected[0][1]+1
    p2_index = (intersected[1][1]+1)%(len(cycle))
    #print("P1: {}, P2: {}".format(p1_index, p2_index))

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

    #print("Subcycle1: ")
    #for n_id in subcycle1:
    #    print("{}: {}".format(n_id, nodes[n_id].location))

    #print("Subcycle2: ")
    #for n_id in subcycle2:
    #    print("{}: {}".format(n_id, nodes[n_id].location))

    colored_labels = helper.color_highways(ways,nodes)
    #colored_labels = None
    #plot(nodes, ways, tags=None, ways_labels=colored_labels)
    #input("Press any key to continue...")

    # generate parcel recursively in subcycle1
    points = []
    for n_id in subcycle1:
        points.append(nodes[n_id].location)
    area = helper.get_area(points)

    partitions_left /= 2
    if partitions_left >= 1:
        #print("Executing recursion Sub1...")
        generate_parcel2(nodes, ways, subcycle1, partitions_left)
    else:
        # place building here
        created_nodes, created_ways = building.generate_offset_polygon_iterative(points)
        nodes.update(created_nodes)
        ways.update(created_ways)

    # generate parcel recursively in subcycle2
    points = []
    for n_id in subcycle2:
        points.append(nodes[n_id].location)
    area = helper.get_area(points)

    partitions_left -= 1
    if partitions_left > 0:
        #print("Executing recursion Sub2...")
        generate_parcel2(nodes, ways, subcycle2, partitions_left)
    else:
        created_nodes, created_ways = building.generate_offset_polygon_iterative(points)
        nodes.update(created_nodes)
        ways.update(created_ways)

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
    print(input)
    log("Reading OSM file '{}'...".format(input))

    # we can obtain parcel data from one type of highway (e.g. residential)
    # and then use this data to generate on another (e.g. primary, secondary)
    obtain_data_from = ["residential","unclassified"]
    generate_on = ["trunk","primary","secondary","tertiary"]
    #generate_on = ["residential","unclassified"]

    nodes, ways = handler.extract_data(input)
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

    cycles = helper.remove_nonempty_cycles(nodes, cycles)
    print("Total empty cycles to generate on: {}".format(len(cycles)))

    plot(nodes, ways)

    for cycle in cycles:
       #generate_parcel(nodes, ways, cycle, cycle_data)
       generate_parcel2(nodes, ways, cycle, 7)
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
