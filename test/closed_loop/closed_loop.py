# -*- encoding: utf-8 -*-
# This file is part of Optosketch. It is released under the GPL v2 licence.
"""This file is used to develop/test the closed-loop detector."""

import os
import os.path as osp
import numpy as np
import pylab as plt

from pprint import pprint

import sys
sys.path.append(osp.join(osp.dirname(__file__), '..', '..'))
from descriptors import StrokeDescriptors


def raw_importer(basedir, target):
    """Import every file contained in a subdirectory of basedir.
    Return a list of dict with keys "filename" and "data".
    data is a numpy array.
    """
    arrays = []
    for (dirpath, _, filenames) in os.walk(basedir):
        fnames = [osp.join(dirpath, f) for f in filenames
                  if f.startswith('stroke_') and f.endswith('.dat')]
        arrays.extend([{"filename": fname,
                        "data": np.loadtxt(fname),
                        "target": target}
                       for fname in fnames])
    return arrays


def plot_strokes(strokes, *args, **kwargs):
    """Plot strokes.
    strokes must be a list of dict with key "data", containing an Nx2 numpy array."""
    for s in strokes:
        plt.plot(s['data'][:,0], s['data'][:,1], 'o-', *args, **kwargs)



if __name__ == "__main__":
    # load data
    """Can list the number of the strokes to process on the command line"""
    strokes = []
    for basedir in ('closed', 'not_closed'):
        strokes.extend(raw_importer(basedir, target=(basedir == 'closed')))

    if len(sys.argv) == 1:
        selected = strokes
    else:
        selected = [strokes[int(s)] for s in sys.argv[1:]]

    for n,s in enumerate(selected):
        desc = StrokeDescriptors(s['data'])
        ans, _, _ = desc.closed_detector()
        
        print "%s %r / %r - %.2d %s" % ('success' if ans == s['target'] else "failure",
                                     ans, s['target'], n, s['filename'])

    if True:
        plt.figure()
        plot_strokes(selected)
        plt.axis('equal')
        ymin, ymax = plt.ylim()
        plt.ylim((ymax, ymin))
        plt.show()

