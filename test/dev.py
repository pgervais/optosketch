"""Survival script for testing Optosketch without graphical tablet.
Running the development test:

    $ PYTHONPATH=. python test/dev.py

"""
import numpy as N

from optosketch import Application
import backend as BCK

app = Application([])
frt = app.window.ui.canvasview.scene().frontend
bck = app.engine
baseline = BCK.Baseline(frt, 0)
bck._baseline = baseline
lens = BCK.Lens(frt, 100, baseline._frontend_object, focal=50)
bck._lenses.append(lens)
rvals, unit = (N.array([20, 20]), N.array([1, 0]))
ray = BCK.Ray(frt, bck, rvals, unit)
bck._rays.append(ray)
app.exec_()
