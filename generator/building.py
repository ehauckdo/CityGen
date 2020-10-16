from lib.Map import OSMWay, OSMNode
import lib.trigonometry as trig
import numpy as np
import random
import math
import logging

id_counter = 993

def new_node(lon, lat, color="black"):
    global id_counter
    n = OSMNode()
    n.id = id_counter
    id_counter += 1
    n.location = (lon, lat)
    n.color = color
    return n

def new_way(nodes=[], tags={}):
    way = OSMWay()
    global id_counter
    way.id = id_counter
    way.color = "blue"
    id_counter += 1
    way.nodes = nodes
    way.tags = tags
    return way

def order_edges_by_size(polygon):
    ordered = []
    for i in range(len(polygon)-1):
         n1 = polygon[i]
         n2 = polygon[i+1]
         x1, y1 = n1.location[0], n1.location[1]
         x2, y2 = n2.location[0], n2.location[1]
         dist = trig.dist(x1, y1, x2, y2)
         ordered.append((dist, (n1,n2)))
    ordered = sorted(ordered, key = lambda x: x[0])
    return [x[1] for x in ordered]

def get_next_point(x1,y1,x2,y2,dist):
    d = trig.dist(x1,y1,x2,y2)
    x3 = (dist*(x2-x1))/d + x1
    y3 = (dist*(y2-y1))/d + y1
    return x3, y3

def get_divisor2(x1, y1, x2, y2, maxdist, maxstd):
    threshold =random.uniform(maxdist-maxstd, maxdist+maxstd)
    n = 1
    div = n*2+2
    x_range = np.linspace(x1, x2, div)
    y_range = np.linspace(y1, y2, div)
    test_x1, test_x2 = x_range[0], x_range[1]
    test_y1, test_y2 = y_range[0], y_range[1]
    #dist = trig.dist(test_x1, test_y1, test_x2, test_y2)
    dist = math.sqrt((test_x2-test_x1)**2 + (test_y2-test_y1)**2)
    while dist > threshold:
        n += 1
        div = n*2+2
        x_range = np.linspace(x1, x2, div)
        y_range = np.linspace(y1, y2, div)
        test_x1, test_x2 = x_range[0], x_range[1]
        test_y1, test_y2 = y_range[0], y_range[1]
        dist = trig.dist(test_x1, test_y1, test_x2, test_y2)
        #dist = math.sqrt((test_x2-test_x1)**2 + (test_y2-test_y1)**2)
        print("{} - {}".format(n, dist))
    x_values = [(x_range[i], x_range[i+1]) for i in range(div-1) if i % 2 == 1]
    y_values = [(y_range[i], y_range[i+1]) for i in range(div-1) if i % 2 == 1]
    return x_values, y_values

def generate_parallel_building(lot, x1, y1, x2, y2, u, v, dx, dy):
    #global created, total
    created_nodes, created_ways = {}, {}
    x3, y3, x4, y4 = trig.get_parallel_points(x1, y1, x2, y2, u, v, dx)
    dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    x5, y5 = trig.get_pont_in_line(x1,y1,x3,y3,dist)
    x6, y6 = trig.get_pont_in_line(x2,y2,x4,y4,dist)
    #log("p3 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x3,y3,x4,y4))
    #x5, y5, x6, y6 = trig.get_parallel_points(x1, y1, x2, y2, u, v, dy)
    #print("p5 lon: {}, lat: {}, p4 lon: {}, lat: {}, ".format(x5,y5,x6,y6))

    n1 = new_node(x3, y3)
    n2 = new_node(x4, y4)
    n3 = new_node(x6, y6)
    n4 = new_node(x5, y5)

    lot_nodes = [x.location for x in lot]
    lot_nodes.append(lot_nodes[0]) # add last node as an edge
    building_nodes = [n1.location, n2.location, n3.location, n4.location, n1.location]

    if trig.is_inside(building_nodes, lot_nodes):
        #nodes.update({n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4})
        way = new_way()
        way.nodes = [n1.id, n2.id, n3.id, n4.id, n1.id]
        way.tags = {"building":"residential"}
        #ways.update({way.id:way})
        #created +=1
        created_nodes = {n1.id: n1, n2.id: n2, n3.id: n3, n4.id: n4}
        created_ways = {way.id:way}

    return created_nodes, created_ways

def generate_in_cycle(lot, source_ways, data=None):
    #global created, total
    nodes, ways = {}, {}

    if len(lot) <= 0:
        return nodes, ways

    logging.info("Generating buildings in cycle with {} nodes.".format(len(lot)))

    edges = order_edges_by_size(lot)
    for n1, n2 in edges:

        #log("Nodes: {} and {}".format(n1.id, n2.id), "DEBUG")
        x1, y1 = n1.location[0], n1.location[1]
        x2, y2 = n2.location[0], n2.location[1]
        dist = trig.dist(x1, y1, x2, y2)

        if dist < 0.0004:
            continue # filter smaller edges

        logging.debug("Generating building between edges {} and {}".format((x1, y1),
                                                        (x2, y2)))
        #total += 1
        a, b, c = trig.get_line_equation(x1, y1, x2, y2)
        u, v = trig.get_unit_vector(a, b)
        #print("a: {}, b: {}, c: {}".format(a, b, c))
        #print("u: {}, v: {}".format(u, v))

        generate_n = 6
        div = generate_n*2+2
        x_range = np.linspace(x1, x2, div)
        x_values = [(x_range[i], x_range[i+1]) for i in range(div-1) if i % 2 == 1]
        y_range = np.linspace(y1, y2, div)
        y_values = [(y_range[i], y_range[i+1]) for i in range(div-1) if i % 2 == 1]
        dx, dy = 0.00020, 0.00010

        for (x1, x2), (y1, y2) in zip(x_values, y_values):
            # dx = distance of the wall to the street
            # dy = distance of the front wall to the rear wall
            #dx, dy = 0.00005, 0.00020
            created_nodes, created_ways = generate_parallel_building(lot, x1, y1, x2, y2, u, v, dx, dy)
            nodes.update(created_nodes)
            ways.update(created_ways)

            #dx, dy = -0.00005, -0.00020
            created_nodes, created_ways = generate_parallel_building(lot, x1, y1, x2, y2, u, v, -dx, -dy)
            nodes.update(created_nodes)
            ways.update(created_ways)

    ways_list = list(ways.items())
    for i in range(len(ways_list)-1, 0, -1):
        id_1, way_1 = ways_list[i]
        building1_nodes = [n.location for n in [nodes[id] for id in way_1.nodes]]
        for j in range(i-1, -1, -1):
            id_2, way_2 = ways_list[j]
            building2_nodes = [n.location for n in [nodes[id] for id in way_2.nodes]]
            logging.debug("Comparing buildings \nb1 ({}): {} \nb2 ({}): {}".format(
                  id_1, building1_nodes, id_2, building2_nodes))
            if trig.has_intersection(building1_nodes, building2_nodes):
                logging.debug("Overlap detected. Removing {}".format(id_1))
                ways.pop(id_1)
                for n_id in way_1.nodes:
                    nodes.pop(n_id, None) # the last node in the way is repeated
                break

    logging.debug("Generated a total of {} ways".format(len(ways.items())))
    return nodes, ways
