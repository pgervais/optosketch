# This file is part of Optosketch. It is released under the GPL v2 licence.

"""Base classes to instanciate by frontend object. These interfaces are expected
by RecognitionEngine."""


class FrontEnd(object):
    """Base class for frontend communication object. This object is used
    by RecognitionEngine to send information to the frontend.
    The present class basically does nothing. It is intended as a reminder,
    both for humans and computers."""

    def add_point(self, x, y, kind=None):
        """Add a geometric point to the schematic
        x,y: point coordinates (numbers)
        kind: (string) describe point (see also add_line)"""
        return None # return GenericPoint object


    def add_line(self, line, kind=None):
        """Add a polyline to the schematic
        line: coordinates (numpy array)
        kind: describe line (string). May be used by the frontend to change
              line appearance.
        """
        return None # return GenericLine object


    def add_baseline(self, ylocation):
        """Add a baseline to the schematic.
        ylocation: vertical coordinate of baseline. A baseline is supposed
        not to have horizontal limits (it extends from leftmost visible
        coordinate to rightmost visible coordinate)"""
        return None # return Baseline object

    
    def add_lens(self, location, baseline, height, kind):
        """Add a lens to a baseline.
        location: horizontal coordinate along baseline. 
        baseline: frontend object returned by add_baseline().
        height: half-size of lens (distance between center and one extreme
                point)
        kind: "diverging" or "converging" (or "negative"/"positive")
        """
        return None # return Lens object


class VisibleObject(object):
    """Base class for all frontend objects. """
    def remove(self):
        """Permanently remove the object from the schematic"""
        pass


class GenericLine(object):
    """A polyline, without any particular meaning. Can be used for partially
    recognized symbols."""
    def __init__(self, line):
        """line: numpy array, containing line coordinates."""
        pass


class GenericPoint(object):
    """A geometric point"""
    def __init__(self, x, y):
        """x, y: coordinates"""
        self.x = None
        self.y = None
    

class BaseLine(object):
    """Base class for a base line frontend object""" 
    def __init__(self):
        self.ylocation = None


class Lens(object):
    """Base class for a frontend lens object"""
    def __init__(self):
        self.baseline = None # BaseLine object
        self.xlocation = None
        self.height = None 
        




