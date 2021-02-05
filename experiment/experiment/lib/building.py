from lib.Map import OSMWay, OSMNode
from lib import settings
import lib.trigonometry as trig
import numpy as np
import random
import math
import logging
import pyclipper
import lib.helper as helper

def new_node(lon, lat, color="black"):
    n = OSMNode()
    n.id = settings.id_counter
    settings.id_counter += 1
    n.location = (lon, lat)
    n.color = color
    return n

def new_way(nodes=[], tags={}):
    way = OSMWay()
    way.id = settings.id_counter
    settings.id_counter += 1
    way.color = "blue"
    way.nodes = nodes
    way.tags = tags
    return way

def generate_offset_polygon_iterative(lot, threshold=0.8, offset=-10000):
    # this implementation is a bit slower than generate_offset_polygon
    # but it will find a polygon that has less than 50% of the area
    # of the lot and use that for the building itself
    nodes, ways = {}, {}
    subj = []
    initial_area = generated_area = helper.get_area(lot)
    for x, y in lot:
        subj.append((pyclipper.scale_to_clipper(x),
                     pyclipper.scale_to_clipper(y)))

    while generated_area/initial_area > 0.4:
        pco = pyclipper.PyclipperOffset()
        pco.AddPath(subj, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
        solution = pco.Execute(offset)

        if len(solution) == 0:
            # failed to get offset polygon with the fixed param
            return nodes, ways

        building_lot = [(pyclipper.scale_from_clipper(x),
                        pyclipper.scale_from_clipper(y)) for x, y in solution[0]]


        generated_area = helper.get_area(building_lot)
        offset *= 1.5

    building_nodes = []
    for x, y in building_lot:
        n = new_node(x, y)
        building_nodes.append(n.id)
        nodes[n.id] = n

    way = new_way()
    way.nodes = building_nodes+[building_nodes[0]]
    way.tags = {"building":"residential"}
    ways[way.id] = way

    return nodes, ways
