import math

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

def main():

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

if __name__ == '__main__':
    main()
