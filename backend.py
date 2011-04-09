# This file is part of Optosketch. It is released under the GPL v2 licence.
"""Recognition engine main file. The API provided by this file must be independant
of frontend. Frontend communication must be implemented in a separate file.
"""

from descriptors import StrokeDescriptors
from simplify import simplify_dp

class RecognitionEngine(object):
    """Main communication object between frontend and backend."""

    def set_frontend(self, frontend):
        """Must be called by frontend object."""
        self.frontend = frontend


    def push_stroke(self, stroke):
        """Provides the engine with a new stroke. Interpretation is performed."""
        
        print "--- Base line ---"
        print "number of points: ",len(stroke)
        # print "coordinates: ", stroke

        print ("--- Descriptors ---")
        descriptors = StrokeDescriptors(stroke)
        print (descriptors)
        # print "Angles:\n", descriptors._angles

        # Call detectors here
        print("--- Detectors ---")
        point = descriptors.point_detector()
        print "Point: "+str(point) 
        line  = descriptors.straight_line_detector()        
        print "Line: "+str(line)

        print("--- Corners detection ---")
        resamp = descriptors.resample()
        corners1 = descriptors.corners1()
        print "corners:",corners1
        print 'resampled point number: %d' % len(resamp)
        self.frontend.add_line(corners1)

        if point[0]:
            self.frontend.add_point(point[1], point[2])
            return 

        if line[0]:
            self.frontend.add_line(stroke[(0,-1),:], kind="generic")
            return

        print "--- Simplification ---"
        threshold = 1
        d = simplify_dp(stroke[:,0], stroke[:,1])
        s = stroke[d>1.]
        print "threshold: ", threshold
        print "number of points: ", len(s) 

        # Display simplified line
        self.frontend.add_line(s, kind="simplified")

