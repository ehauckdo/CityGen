import math

def dist(x1, y1, x2, y2):
    return math.sqrt((x2-x1)**2 + (y2-y1)**2)

def intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    # I got this implementation from the internet and it appears to work
    # I can implement my own using the cross product vector based approach
    # where p * tr = q * us
    def ccw(x1, y1, x2, y2, x3, y3):
        return (y3-y1) * (x2-x1) > (y2-y1) * (x3-x1)
    return (ccw(x1,y1, x3,y3, x4,y4) != ccw(x2,y2, x3,y3, x4,y4) and
           ccw(x1,y1, x2,y2, x3,y3) != ccw(x1,y1, x2,y2, x4,y4))

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
    count = 0
    for i in range(len(polygon)-1):
        x1, y1 = polygon[i]
        x2, y2 = polygon[i+1]
        if (y > y1 and y < y2) or (y > y2 and y < y1):
            m = (y2-y1)/(x2-x1+0.000001)
            ray_x = x1 + (y - y1)/m
            if ray_x > x:  count +=1
    return count % 2 == 1

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
