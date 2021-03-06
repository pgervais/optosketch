
# -*- coding: utf-8 -*-
# This file is part of Optosketch. It is released under the GPL v2 licence.
"""Functions and objects to compute various line descriptors.
StrokeDescriptor is an object that takes a numpy array as input.
It computes several useful descriptors, including :
- line length (_length)
- barycenter, weighted (_gcenter) and unweighted (_center)
- standard deviation (_astd)
- normalized line (standard deviation 1 in both directions : _anorm)
- center of bounding box (_bboxcenter) 
- principal axis computed with Principal Component Analysis (PCA)
- pca-normalized line : principal axis are aligned with horizontal and 
  vertical, standard deviations are set to 1 (_anormacp).
- bounding box sizes along principal axis (_span)
- segment angles (_angles), and cumulated angles (_cumangles). Cumulated 
 angles can be understood as the angle the line has turned since its beginning.
 For a complete circle, 2*pi, for an infinity sign or an 8 it is zero.

Useful methods :
- Extract a sub-part, given lengths since the beginning (extract())
- Bounding box for a sub-part (bbox_indices())
- ad-hoc point detector : point_detector(). 
"""

import math
import logging
from math import radians, pi
from array import array

import numpy as np
from numpy import dot, sin, cos, sqrt, cross
from numpy.linalg import svd, solve, det

from simplify import simplify_dp


class StrokeDescriptors(object):
    """Estimator of various geometric properties. """
    def __init__(self, a):
        self._a = a
        
        self.atan2 = np.frompyfunc(math.atan2, 2, 1)

        # Useful quantities 
        # Polyline segments, as vectors.
        self._vectors = self._a[1:, :] - self._a[:-1, :]
        self._dx = self._vectors[:, 0]
        self._dy = self._vectors[:, 1]

        # Polyline segment lengths, and overall length
        self._lengths = np.sqrt(self._dx**2 + self._dy**2)
        self._cumlength = self._lengths.cumsum()
        self._length = self._cumlength[-1]
        
        # Centers of segments
        self._segcenters = (self._a[1:,:] + self._a[:-1,:])/2

        # Unweighted barycenter
        self._center = self._a.mean(0)
        # Weighted barycenter
        self.gravity_center()

        # Center of bounding box
        self._bboxcenter = (self._a.max(0) + self._a.min(0)) / 2
        
        if len(self._a) > 2: self.angles_quantities()
        self.normalize()

        # PCA-related computations
        self.acpn() # FIXME: rename acp -> pca (french->english)
        self.span()
        self.normalize_acp()
        # Straight lines occur for a.r. app. greater than 10
        self._ar = self._S[0]/self._S[1]


    def __str__(self):
        s = 'Line length: %d' % self._length
        s += "\nBbox center: (%.2f, %.2f)" % (self._bboxcenter[0], self._bboxcenter[1])
        s += "\nGravity center: (%.2f, %.2f)" % (self._gcenter[0], self._gcenter[1])
        if len(self._a) > 2:
            s += "\nMax rotation: %.2f turn(s)" % (self._maxrotation/(2*math.pi))
            s += "\nAngle rate: %2f deg/(100*pixel)" % (100.*self._angle_rate *180/math.pi)
#            s += "\nMedian angle: %2f deg" % (self._angle_median *180/math.pi) 
        return s
    

    def gravity_center(self):
        """Return center of line. This estimation is consistent with the
        visual impression (not the bounding box center, nor the unweighted
        mean value) """

        # Lengths
        c = self._segcenters.copy()
        c[:, 0] *= self._lengths
        c[:, 1] *= self._lengths
        self._gcenter = c.sum(0) / sum(self._lengths)


    def angles_quantities(self):
        """Compute some quantities related to segments relative angles."""
        # Cosine: scalar product
        c = self._dx[0:-1] * self._dx[1:] + self._dy[0:-1] * self._dy[1:]
        #c /= self._lengths[0:-1]
        #c /= self._lengths[1:]
        
        # Sine: vector product
        s = self._dx[0:-1] * self._dy[1:] - self._dy[0:-1] * self._dx[1:]
        
        # Oriented angles
        self._angles = self.atan2(s,c)
        self._cumangles = self._angles.cumsum()

        # Get the peak-to-peak amplitude of cumulative angles
        self._maxrotation = self._cumangles.max() - self._cumangles.min()

        # Detrend
        P = np.polyfit(self._cumlength[1:], self._cumangles, 1)
        self._angle_rate = P[0]
        logging.debug('polynom: '+str(P))

        self._cumangles_d = self._cumangles - np.polyval(P, self._cumlength[1:])

        # Median angle: useless without a lot of points
#        self._angle_median = np.median(self._angles)


    def normalize(self):
        """Scale data so its standard deviations are equal to 10."""

        self._anorm = self._a.copy()

        s = self._anorm.std(0)
        self._astd = s

        if s[0] != 0.: self._anorm[:,0] /= s[0]/10.
        if s[1] != 0.: self._anorm[:,1] /= s[1]/10.
        return self._anorm


    def acpn(self):
        """Make a simple principal component analysis of input data.
        Returns the rotated sample. 
        X must be a matrix containing one sample per row. The number of
        columns is arbitrary.

        Returns V,S,m,U such that :
        X = dot(U, dot(diagflat(S), V)) + m
        m is a matrix with the same shape as X, containing the mean values for
        each component : X-m is the centered samples.

        A unitary vector giving the main direction of the set is V[0,:]. 
        V[0,0] is always positive.

        A rotated sample set can be obtained by : X * V.transpose()
        (* is the matrix product)
        Rotation around the mean value is given by (X-m) * V.transpose() + m

        det(V) can be +1.0 or -1.0
        """

        # Center variables
        m = dot(np.ones(self._a.shape), np.diagflat(self._center))
        Xm = self._a - m

        U,S,V = svd(Xm, full_matrices=False);

        # Ensure main direction points towards positive value
        if V[0,0] < 0. : V = -V

        self._V = V
        self._S = S
        # Angle of principal axis relative to horizontal
        self._principal_angle = math.atan2(self._V[0,1], self._V[0,0])


    def span(self):
        """Compute line span along principal axis."""
        # a contains coordinates, V is the first output of acpn()."""
        p = dot(self._a, self._V.transpose())
        self._span = p.max(0) - p.min(0)


    def normalize_acp(self):
        """Rotate and scale data."""

        b = dot(self._a - self._gcenter, self._V.transpose()) / self._S * 100
        self._anormacp = b


    def midpoint(self, l, ind):
        """Return the coordinate of the point along segment
        self._a[ind], self._a[ind+1], at a distance l from self._a[ind].
        No check is performed to ensure that the returned point is inside the
        segment (l may be greater than the segment length, or negative)"""

        # Unitary vector
        u = self._vectors[ind]/self._lengths[ind]
        return l*u + self._a[ind]


    # User methods
    def bbox_indices(self, n1, n2):
        """Compute bounding box for line between two indices.
        Order : xmin, ymin, xmax, ymax."""
        bb = np.zeros(4)
        assert (n2+1 <= self._a.shape[0])
        bb[0:2] = self._a[n1:n2+1,:].min(0)
        bb[2:4] = self._a[n1:n2+1,:].max(0)    
        return bb

    #def bbox_length(self, l1, l2):
#    """Compute bounding box for line between two lengths."

    def extract(self, l1, l2):
        """Return the part of the polyline between lengths l1 and l2, starting
        from the beginning of the line."""
        ind = self._cumlength.searchsorted([l1, l2])
        
        # First point: always exists
        ends = 0
        if ind[0] == 0:
            d = l1
        else:
            d = l1 - self._cumlength[ind[0]-1]
        assert (d>=0)
        first = self.midpoint(d, ind[0])
        ends += 1

        # Second point
        if ind[1] == len(self._cumlength):
            # No extrapolation
            second = None
        else:
            d = l2 - self._cumlength[ind[1]-1]
            assert (d >= 0)
            second = self.midpoint(d, ind[1])
            ends += 1

        n = ind[1]-ind[0]
        c = np.zeros((n+ends,2))
        # Add first point
        c[0,:] = first
        c[1:1+n,:] = self._a[ind[0]+1:ind[1]+1,:]

        if not second is None: c[-1,:] = second

        return c


    def point_detector(self):
        """Detects a point. A point is either a very short line, with very
        small spatial extend, or a very long intricated line, not
        necessarily small spatial extend.
        """
        # Values below 4 or 5 are associated with very small drawings.
        # Short lines give larger values very quickly.
        # Detection is not scale-independent !
        # FIXME: normalize by the ratio window size/opengl window size.
        thresh = 5.

        value = self._span.max()*self._span.mean()/self._length
        logging.debug("[point] %.2f vs %.2f" % (value, thresh))
        if value <= thresh: # point
            logging.debug("** Point detected **")
            return (True, self._center[0],self._center[1])

        return (False, None, None)


    def straight_line_detector(self):
        """Detects a straight line. Use ratio between length and end-to-end
        distance, on simplified line."""

        # Use of the simplified line is required to handle overall line length 
        # instability for very small lines. However, this detector is scale
        # dependent: small lines must be very straight to trigger this
        # detector, long lines trigger too often. 
        # Possible solutions : change threshold on "ratio" depending on line
        # length, or use another ratio (e.g. aspect ratio, computed using
        # pca results).

        d = simplify_dp(self._a[:,0], self._a[:,1])
        s = self._a[d>1.] # Simplified line

        # Length of simplified line
        # TODO: express as a single line.
        _vectors = s[1:, :] - s[:-1, :]
        _dx = _vectors[:, 0]
        _dy = _vectors[:, 1]
        _length = np.sqrt(_dx**2 + _dy**2).sum()

        endtoend = np.sqrt(((s[0,:]-s[-1,:])**2).sum())
        ratio = _length / endtoend
        logging.debug("Straight line: %.2f %.2f / %.2f = %.2f" % \
            (self._length, _length, endtoend, ratio))

        if ratio < 1.03:
            _lx, _ly = np.abs(s[0,:]-s[-1,:])

            # Test if line is vertical, horizontal or diagonal
            if abs(_lx) < 0.2*abs(_ly):
                orientation = "vertical"
            elif abs(_ly) < 0.2*abs(_lx):
                orientation = "horizontal"
            elif 0.8*abs(_ly) < abs(_lx) < 1.2*abs(_ly):
                orientation = "diagonal"
            else:
                orientation = ""
            return (True, orientation)
        else:
            return (False,)


    def resample(self, num=80, lengths=None):
        """Resample line. Wolin thesis p.64-66"""
        ## TODO: Pass resamp_cl as a parameter.

        # Compute resampled line cumulated length
        if not lengths is None:
            resamp_cl = lengths
        else:
            step = self._span.max()/num
            resamp_cl = np.arange(0., self._cumlength[-1], step)

        _cumlength = np.hstack(([-1e-4], self._cumlength))
        ind = _cumlength.searchsorted(resamp_cl)-1

        # Unitary vectors along selected segments
        _lengths = self._lengths[ind]
        u = self._vectors[ind]/np.vstack((_lengths, _lengths)).transpose()

        _partial_lengths = (resamp_cl-_cumlength[ind])
        return (np.vstack((_partial_lengths, _partial_lengths)).transpose() * u
                + self._a[ind])


    def corners1(self, w=3):
        """Bottom-up corner finding. See Wolin thesis p.67 """
        resampled = self.resample()
        segments = resampled[w:] - resampled[:-w]
        straws = np.sqrt(segments[:,0]**2 + segments[:,1]**2)

        threshold = np.median(straws) * 0.95

        # Local minimum computation : 
        # http://stackoverflow.com/questions/4624970/finding-local-maxima-minima-with-numpy-in-a-1d-numpy-array

        ind = np.where(np.r_[True, straws[1:] < straws[:-1]] 
                       & np.r_[straws[:-1] < straws[1:], True]
                       & (straws < threshold))[0]
        return np.r_[resampled[:1,:], resampled[ind+w-1,:], resampled[-1:,:]]


    def distance_to_point(self, point, sl=slice(None)):
        """Compute distance between line and point.
        Computed is minimum distance between the point and every vertex of stroke.
        point must be a 1x2 numpy array.
        sl is a slice object. It can be used to restrict the part of the line on
        which compute the distance.
        """

        extract = self._a[sl,:]
        if len(extract) == 1:
            return (0, ((extract-point)**2).sum())

        # Compute distance to every vertex in stroke
        dist2 = ((extract - point) ** 2).sum(1)
        k = np.argmin(dist2)
        return (k, dist2[k])


    def closed_detector(self):
        """Closed line detector."""
        # Compute distance between an endpoint and the 20% percent the other end.
        npoint = self._a.shape[0] # point number

        all = self._length
        fraction = 0.2
        ind = self._cumlength.searchsorted(np.asarray([all*fraction, all*(1-fraction)]))+1
#        print ind, len(gea._a)
#        print "[closed] ratios: (%.2f, %.2f)" % (gea._cumlength[ind[0]-1]/gea._length,
#                                        gea._cumlength[ind[1]-1]/gea._length)

        k1, d1 = self.distance_to_point(self._a[0,:], slice(ind[1], None))
        k2, d2 = self.distance_to_point(self._a[-1,:], sl=slice(0,ind[0])) 
        r1, r2 = d1/self._span.min(), d2/self._span.min()
#        print '[closed] Distances: %.3f, %.3f' % (r1, r2)

        closed = False
        if min(r1, r2) < 8.:
            logging.debug('**Closed loop detected**')
            closed = True

        return closed, k1+ind[1], k2
