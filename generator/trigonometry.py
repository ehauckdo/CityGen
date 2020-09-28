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
