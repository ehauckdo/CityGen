import math
import matplotlib
import numpy as np

def dist(x1, y1, x2, y2):
    return math.sqrt((x2-x1)**2 + (y2-y1)**2)

def intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    # unchecked implementation that appears to work
    # I can implement my own using the cross product vector based approach
    # where p * tr = q * us
    def ccw(x1, y1, x2, y2, x3, y3):
        return (y3-y1) * (x2-x1) > (y2-y1) * (x3-x1)
    return (ccw(x1,y1, x3,y3, x4,y4) != ccw(x2,y2, x3,y3, x4,y4) and
           ccw(x1,y1, x2,y2, x3,y3) != ccw(x1,y1, x2,y2, x4,y4))

def my_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    # based on https://stackoverflow.com/a/565282
    p = (x1, y1)
    r = (x2-x1, y2-y1)
    q = (x3, y3)
    s = (x4-x3, y4-y3)
    def calc(q, p, s, r):
        t = (q[0]-p[0], q[1]-p[1])
        t = (t[0]*s[1]) - (t[1]*s[0])
        t /= (r[0]*s[1]) - (r[1]*s[0])
        return t
    rs = (r[0]*s[1]) - (r[1]*s[0])
    if rs == 0:
        return False
    t = calc(q,p,s,r)
    u = calc(p,q,r,s)
    # print("t: {}".format(p[0]+ r[0]*t, p[1]+r[1]*t))
    # print("u: {}".format(q[0]+ s[0]*u, q[1]+s[1]*u))
    if t >= 0 and t <= 1 and u >= 0 and u <= 1:
        return (p[0]+ r[0]*t, p[1]+r[1]*t)

def has_intersection(polygon1, polygon2):
    # Check if there is any intersection between pairs of edges of polygons
    for i in range(len(polygon1)-1):
        x1, y1 = polygon1[i]
        x2, y2 = polygon1[i+1]
        for j in range(len(polygon2)-1):
            x3, y3 = polygon2[j]
            x4, y4 = polygon2[j+1]
            if intersect(x1, y1, x2, y2, x3, y3, x4, y4):
                return True
    return False

def point_inside_polygon(x, y, polygon):
    # source: https://stackoverflow.com/a/23453678
    test_polygon = [point for point in polygon]
    bb_path = matplotlib.path.Path(np.array(test_polygon))
    return bb_path.contains_point((x, y))

def is_inside(polygon1, polygon2):
    #print("Checking if poylgon1: \n {}".format(polygon1))
    #print("is inside polygon2: \n {}".format(polygon2))
    if has_intersection(polygon1, polygon2):
        return False

    # If no intersection is found, we just need to check that
    # at least 1 point of pol1 is within pol2
    for x, y in polygon1:
        if point_inside_polygon(x, y, polygon2):
            return True

    return False

def get_boundingbox(polygon):
    x, y = polygon[0]
    min_x, min_y, max_x, max_y = x, y, x, y
    for x, y in polygon:
        min_x = x if x < min_x else min_x
        min_y = y if y < min_y else min_y
        max_x = x if x > max_x else max_x
        max_y = y if y > max_y else max_y
    return min_x, min_y, max_x, max_y

def get_parallel_points(x1, y1, x2, y2, u, v, d):
    return x1 + d*u, y1 + d*v, x2 + d*u, y2 + d*v

def get_unit_vector(a, b):
    import math
    l = 1 / math.sqrt(a**2 + b**2)
    u = l * a
    v = l * b
    return u, v

def get_line_equation(x1, y1, x2, y2):
    a = y1 - y2
    b = x2 - x1
    c = (-(y1 - y2))*x1 + (x1 - x2)*y1
    return a, b, c

def get_pont_in_line(x1,y1,x2,y2,dist):
    d = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    x3 = (dist*(x2-x1))/d + x1
    y3 = (dist*(y2-y1))/d + y1
    return x3, y3

def extend_line(x1,y1,x2,y2,ext=0.1):
    len_p1_p2 = dist(x1,y1,x2,y2)
    x3 = x2 + (x2 - x1) / len_p1_p2 * (ext*len_p1_p2)
    y3 = y2 + (y2 - y1) / len_p1_p2 * (ext*len_p1_p2)
    return x3, y3

def get_angle(lat1, long1, lat2, long2):
    import math
    dLon = (long2 - long1)

    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)

    brng = math.atan2(y, x)

    brng = math.degrees(brng)
    brng = (brng + 360) % 360
    brng = 360 - brng # count degrees clockwise - remove to make counter-clockwise

    return brng

# playing and understanding the code
def line_manipulation_demo():

    # points in a line
    x1, y1 = 4, 5
    x2, y2 = 7, 9
    print(x1, y1, x2, y2)

    # a, b, c terms that define the line
    a, b, c = get_line_equation(x1, y1, x2, y2)
    print(a, b, c)

    # unit vector of a perpendicular vector to the line given by a, b
    u, v = get_unit_vector(a, b)
    print(u, v)

    # calculate p3 and p4 given a multiple of the perpendicular unit vector
    d = 5
    x3, y3, x4, y4 = get_parallel_points(x1, y1, x2, y2, u, v, d)
    print(x3, y3, x4, y4)

    d = 1
    x3, y3, x4, y4 = get_parallel_points(x1, y1, x2, y2, u, v, d)
    print(x3, y3, x4, y4)
