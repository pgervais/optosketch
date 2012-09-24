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

        @property
        def get_sessionid(self):
            """Return current session id"""
            return self.__sessionid


        def close_session(self):
            """Compute a new session id.
            Flushes the file on disk."""
            self.flush()
            self.__sessionid += 1


        def __len__(self):
            return (self.f['metadata'].shape[0])


        def flush(self):
            # Fill metadata table, add stroke arrays
            if len(self.__strokes) == 0:
                return
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


        def read_stroke(self, strokeid=None, sessionid=None):
            """Read stroke either by id or by session (default: last stroke)
            Return : 2-tuple with metadata, stroke array
            metadata is a structured array with key start_time, sessionid, strokeid
            """
            if sessionid is not None and strokeid is not None:
                raise ValueError("Both sessionid and strokeid can't be defined")

            if strokeid is None and sessionid is None:
                strokeid = -1

            metadata = self.f['metadata'][:]

            if strokeid is not None:
                if strokeid == -1:
                    strokeid = metadata['strokeid'].max()
                ind = metadata['strokeid'].searchsorted(strokeid)
                
                if ind >= metadata.shape[0] or metadata['strokeid'][ind] != strokeid:
                    raise ValueError("Invalid stroke id")
                
                return (metadata[ind], self.f['strokes/s_%.6d' % strokeid])
            
            else: # session is not None
                ind = np.where(metadata['sessionid'][:] == sessionid)[0]

                ret = []
                for n in ind:
                    ret.append((metadata[n], self.f['strokes/s_%.6d' %
                                                    metadata[n]['strokeid']]))
                return ret


        def stroke_iter(self):
            """Iterator over every stroke."""
            for n in self.f['metadata']['strokeid']:
                yield self.read_stroke(n)


        def session_iter(self):
            """Iterate over each session."""
            sessionids = list(set(self.f['metadata']['sessionid']))
            sessionids.sort()
            for n in sessionids:
                yield self.read_stroke(sessionid=n)


except ImportError:
    class StrokeFile(object):
        """Mockup class in case h5py is not available."""
        pass

    
if __name__ == "__main__":
    # Tests for StrokeFile

    import time
    import random
    import unittest
    import os

    class TestWrite(unittest.TestCase):
        def setUp(self):
            self.filename = "strokefile_testwrite.h5"
            try:
                os.remove(self.filename)
            except OSError: pass


        def fill_file(self, sf, count=10):
            """Add a given number of random strokes to the StrokeFile object.
            Does not flush file, return strokes added as a list.
            """
            strokes = []
            for n in xrange(count):
                strokes.append((np.random.randn(random.randint(10, 100)), time.time()))
                sf.add_stroke(*strokes[-1])

            return strokes
        

        def test_session_iter(self):
            sf = StrokeFile("h5py_optosketch.h5", overwrite = True)
            strokes = []
            count = [5, 12, 37]
            for c in count:
                strokes.append(self.fill_file(sf, c))
                sf.close_session()
            sf.close()

            sf = StrokeFile("h5py_optosketch.h5")
            count.append(15)
            strokes.append(self.fill_file(sf, count[-1]))
            sf.close()

            sf = StrokeFile("h5py_optosketch.h5")
            for c, st, sess in zip(count, strokes, sf.session_iter()):
                self.assertEqual(c, len(st))
                self.assertEqual(c, len(sess))
                self.assertEqual(len(set([s[0]['sessionid'] for s in sess])), 1)
                for s1, s2 in zip(st, sess):
                    np.testing.assert_almost_equal(s1[0], s2[1])
                
            sf.close()            

            
        def _test_add_stroke(self):
            # Create an empty file
            stroke_number = 10
            sf = StrokeFile("h5py_optosketch.h5", overwrite = True)
            self.assertEqual(len(sf), 0)

            # Add some strokes
            strokes = self.fill_file(sf, stroke_number)
            self.assertEqual(len(sf), 0)
            sf.flush()
            self.assertEqual(len(sf), stroke_number)
            
            # Check len, and stroke content
            sessionid = None
            for n, s in enumerate(sf.stroke_iter()):
                self.assertEqual(strokes[n][1], s[0]["start_time"])
                if sessionid is None:
                    sessionid = s[0]["sessionid"]
                else:
                    self.assertEqual(sessionid, s[0]["sessionid"])
                np.testing.assert_almost_equal(strokes[n][0], s[1])
                
            # Add some more strokes
            strokes += self.fill_file(sf, stroke_number)            
            sf.flush()
            
            # Check len, and stroke content
            self.assertEqual(len(sf), 2*stroke_number)

            for n, s in enumerate(sf.stroke_iter()):
                self.assertEqual(strokes[n][1], s[0]["start_time"])
                self.assertEqual(sessionid, s[0]["sessionid"])
                np.testing.assert_almost_equal(strokes[n][0], s[1])
                
            # Check that strokeid are all different
            self.assertEqual(len(set(sf.f['metadata']['strokeid'])), 2*stroke_number)

            sf.close()

    unittest.main()
