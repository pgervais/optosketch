# -*- encoding: utf-8 -*-

import numpy as np
import os.path as osp

try:
    import h5py

    class StrokeFile(object):
        """Permanent storage of strokes information for OptoSketch."""

        metadata_dtype = [('start_time', 'float64'),
                          ('sessionid', 'int64'),
                          ('strokeid', 'int64')]
        stroke_dtype = [('x', 'float32'), ('y', 'float32')]

        def __init__(self, filename, overwrite=False):
            self.__create_file(filename, overwrite=overwrite)
            self.f = h5py.File(filename, mode="a")
            self.__count = self.f['metadata'].attrs['count']
            self.__sessionid = self.f['metadata'].attrs['sessionid'] + 1
            self.__strokes = []


        def flush(self):
            # Fill metadata table, add stroke arrays
            stroke_g = self.f['strokes']
            metadata = self.f['metadata']
            initial_count = metadata.shape[0]
            metadata.resize((self.__count,))

            line = np.zeros((1,), dtype=self.metadata_dtype)
            for i, s in enumerate(self.__strokes):
                line['start_time'] = s['start_time']
                line['strokeid'] = s['id']
                line['sessionid'] = self.__sessionid
                metadata[initial_count+i] = line
                stroke_g.create_dataset('s_%.6d' % s['id'], data=s['stroke'])

            self.f['metadata'].attrs['count'] = self.__count        
            self.f['metadata'].attrs['sessionid'] = self.__sessionid
            self.__strokes = []
            self.f.flush()


        def close(self):
            self.flush()
            self.f.close()


        def __create_file(self, filename, overwrite=False):
            """Create internal structure. Never overwrite an existing file, unless
            explicitely asked."""

            if osp.lexists(filename) and not overwrite: return

            f = h5py.File(filename, mode='w')
            strokes = f.create_group('/strokes')

            ds = f.create_dataset('metadata', shape=(0,),
                                  dtype = self.metadata_dtype, maxshape = (None,),
                                  chunks=True)
            ds.attrs['count'] = 0 # number of strokes currently recorded
            ds.attrs['sessionid'] = 0 # next sessionid
            f.close()


        def add_stroke(self, stroke, start_time):
            """stroke is a numpy array (Nx2),
            start_time is a timestamp (seconds since the epoch, float64)"""
            self.__strokes.append({'stroke': stroke,
                                   'start_time': start_time,
                                   'id': self.__count})
            self.__count += 1

except ImportError:
    class StrokeFile(object):
        """Mockup class in case h5py is not available."""
        pass

    
if __name__ == "__main__":
    import time
    import random
#    sf = StrokeFile("h5py_optosketch.h5", overwrite = True)
    sf = StrokeFile("h5py_optosketch.h5")
    for n in xrange(10):
        sf.add_stroke(np.random.randn(random.randint(10, 100)), time.time())

    sf.flush()
#    raw_input()

    for n in xrange(10):
        sf.add_stroke(np.random.randn(random.randint(10, 100)), time.time())
    
    sf.close()

