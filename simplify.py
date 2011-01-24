# This file is part of Optosketch. It is released under the GPL v2 licence.

"""Line simplification functions."""

import numpy as np
import math


def simplify_dp(x,y):
    """Simplify 2D lines, using Douglas-Peuker Algorithm.
    This function returns an array of perpendicular distances, one per point.
    x,y : arrays of coordinates.
    If we call "d" the return value of this function, the coordinates of
    a simplified line for a threshold t are given by x[d>t], y[d>t]

    This algorithm has N^2 complexity, but is very robust and can handle very
    complex cases.

    Reference :
    Douglas, D. and Peuker, T., "Algorithms for the reduction of the 
    number of points required to represent a digitised line or its caricature", 
    The Canadian Cartographer, Vol 10, pp. 112-122, 1973.
    """

    def step_simplify_dp(n1, n2, x,y, distance, lastdist):
        """One step of simplification
        n1, n2: indices of interval to simplify
        x,y : arrays of coordinates.
        p: next point number
        distance: arrays containing distance for each point. 
        """

        if (n2-n1) == 1:
            # Nothing to split
            return 

        # Compute unitary vector pointing from first to last point.
        ilen = math.sqrt((x[n2]-x[n1])**2 + (y[n2]-y[n1])**2)
        ix = (x[n2]-x[n1])/ilen
        iy = (y[n2]-y[n1])/ilen

        # For each point, compute the distance from the line joining the
        # two extreme points
        vectx = x[n1:n2+1] - x[n1]
        vecty = y[n1:n2+1] - y[n1]
        dist = abs(vectx * iy - vecty * ix) 

        # Register the farthest point
        nmax = dist.argmax() 
        distmax = dist[nmax]

        nmax = nmax + n1
        if nmax == n1 or nmax == n2:
            # Line is perfectly straight...
            nmax = n1 + 1 

        newlastdist = min(distmax, lastdist)
        distance[nmax] = newlastdist

        assert nmax < n2
        assert nmax > n1

        # Split left interval
        step_simplify_dp(n1, nmax, x, y, distance, newlastdist)
        # Split right interval
        step_simplify_dp(nmax, n2, x, y, distance, newlastdist)


    distance = np.ndarray(len(x), dtype='float64')
    distance.fill(-float('inf'))
    distance[0] = float('inf')
    distance[-1] = float('inf')
    step = True
    n = 0

    q = step_simplify_dp(n , len(x)-1, x, y, distance, float('inf'))
    
    return distance


if __name__ == "__main__":
    # Test
    c = np.asarray([[0,1],[0,2],[1,3]])
    d = simplify_dp(c[:,0],c[:,1])
    print c
    print d
    print c[d>0.5] # simplified line.
