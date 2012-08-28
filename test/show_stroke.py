#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# This file is part of Optosketch. It is released under the GPL v2 licence.
"""Display one or several strokes."""

import os
import os.path as osp
import numpy as np
import pylab as plt

from pprint import pprint

import sys
sys.path.append(osp.join(osp.dirname(__file__), '..'))
from descriptors import StrokeDescriptors


def raw_importer(basedir):
    """Import every file contained in a subdirectory of basedir.
    Return a list of dict with keys "filename" and "data".
    data is a numpy array.
    """
    arrays = []
    for (dirpath, _, filenames) in os.walk(basedir):
        fnames = [osp.join(dirpath, f) for f in filenames
                  if f.startswith('stroke_') and f.endswith('.dat')]
        arrays.extend(import_files(fnames))
    return arrays


def import_files(filenames):
    return ([{"filename": fname, "data": np.loadtxt(fname)}
             for fname in filenames])


def plot_strokes(strokes, *args, **kwargs):
    """Plot strokes.
    strokes must be a list of dict with key "data", containing an Nx2 numpy array."""
    for s in strokes:
        plt.plot(s['data'][:,0], s['data'][:,1], 'o-',
                 label=osp.basename(s['filename']), *args, **kwargs)


if __name__ == "__main__":
    # load data
    """Can list the number of the strokes to process on the command line"""
    if len(sys.argv) == 1:
        print ("Usage: %s <filename> [<filename>]" % sys.argv[0])
        sys.exit(0)
    strokes = import_files(sys.argv[1:])

    plt.figure()
    plot_strokes(strokes)
    plt.legend()
    plt.axis('equal')
    ymin, ymax = plt.ylim()
    plt.ylim((ymax, ymin))
    plt.show()

