
import matplotlib.pyplot as plt
import numpy as np

# source: https://stackoverflow.com/a/45276634
def get_OBB(polygon):
    ca = np.cov(polygon,y = None,rowvar = 0,bias = 1)

    v, vect = np.linalg.eig(ca)
    tvect = np.transpose(vect)

    #use the inverse of the eigenvectors as a rotation matrix and
    #rotate the points so they align with the x and y axes
    ar = np.dot(polygon,vect)

    # get the minimum and maximum x and y
    mina = np.min(ar,axis=0)
    maxa = np.max(ar,axis=0)
    diff = (maxa - mina)*0.5

    # the center is just half way between the min and max xy
    center = mina + diff

    #get the 4 corners by subtracting and adding half the bounding boxes height and width to the center
    corners = np.array([center+[-diff[0],-diff[1]],center+[diff[0],-diff[1]],center+[diff[0],diff[1]],center+[-diff[0],diff[1]],center+[-diff[0],-diff[1]]])

    #use the the eigenvectors as a rotation matrix and
    #rotate the corners and the centerback
    corners = np.dot(corners,tvect)
    center = np.dot(center,tvect)

    return corners

import numpy as np
from scipy.spatial import ConvexHull

# source: https://gis.stackexchange.com/a/169633
def minimum_bounding_rectangle(points):
    """
    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.

    :param points: an nx2 matrix of coordinates
    :rval: an nx2 matrix of coordinates
    """
    from scipy.ndimage.interpolation import rotate
    pi2 = np.pi/2.

    # get the convex hull for the points
    hull_points = points[ConvexHull(points).vertices]

    # calculate edge angles
    edges = np.zeros((len(hull_points)-1, 2))
    edges = hull_points[1:] - hull_points[:-1]

    angles = np.zeros((len(edges)))
    angles = np.arctan2(edges[:, 1], edges[:, 0])

    angles = np.abs(np.mod(angles, pi2))
    angles = np.unique(angles)

    # find rotation matrices
    # XXX both work
    rotations = np.vstack([
        np.cos(angles),
        np.cos(angles-pi2),
        np.cos(angles+pi2),
        np.cos(angles)]).T
#     rotations = np.vstack([
#         np.cos(angles),
#         -np.sin(angles),
#         np.sin(angles),
#         np.cos(angles)]).T
    rotations = rotations.reshape((-1, 2, 2))

    # apply rotations to the hull
    rot_points = np.dot(rotations, hull_points.T)

    # find the bounding points
    min_x = np.nanmin(rot_points[:, 0], axis=1)
    max_x = np.nanmax(rot_points[:, 0], axis=1)
    min_y = np.nanmin(rot_points[:, 1], axis=1)
    max_y = np.nanmax(rot_points[:, 1], axis=1)

    # find the box with the best area
    areas = (max_x - min_x) * (max_y - min_y)
    best_idx = np.argmin(areas)

    # return the best box
    x1 = max_x[best_idx]
    x2 = min_x[best_idx]
    y1 = max_y[best_idx]
    y2 = min_y[best_idx]
    r = rotations[best_idx]

    rval = np.zeros((4, 2))
    rval[0] = np.dot([x1, y2], r)
    rval[1] = np.dot([x2, y2], r)
    rval[2] = np.dot([x2, y1], r)
    rval[3] = np.dot([x1, y1], r)

    return rval

def demo():
    #print(get_OBB([(3.7, 1.7), (4.1, 3.8), (4.7, 2.9), (5.2, 2.8), (6.0,4.0),
    #(6.3, 3.6), (9.7, 6.3), (10.0, 4.9), (11.0, 3.6), (12.5, 6.4)]))
    box = [(0.0,0.0), (5.0,0.0), (5.0,5.0), (0.0,5.0), (0.0,0.0)]
    print(minimum_bounding_rectangle(np.array(box)))

demo()
