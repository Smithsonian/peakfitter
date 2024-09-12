from __future__ import division,absolute_import
import unittest
import numpy as np
import peakfitter as gf

class PeakfitCase(unittest.TestCase):
    def test_simple_fit(self):
        # fit a 2D gaussian function centered at (64, 64) with width 8
        # inpars = [height,amplitude,center_x,center_y,width_x,width_y,rota]
        inpars = [0, 1, 64, 64, 8, 8,]
        def gaussfunc(x, width):
            return np.exp(-(x**2/width**2)/2)
        
        in_data = gf.twodpeak(gaussfunc, inpars, shape=(128, 128), rotate=False)
        fit = gf.peakfit(gaussfunc, in_data, rotate=False)
        for inval, outval in zip(inpars, fit):
            self.assertAlmostEqual(inval, outval)

    def test_elliptical_fit(self):
        inpars = [0, 1, 64, 64, 4, 12, 30]
        def gaussfunc(x, width):
            return np.exp(-(x**2/width**2)/2)
        
        in_data = gf.twodpeak(gaussfunc, inpars, shape=(128, 128))
        fit = gf.peakfit(gaussfunc, in_data)
        for inval, outval in zip(inpars, fit):
            self.assertAlmostEqual(inval, outval)

    def test_masked_fit(self):
        inpars = [0, 1, 64, 64, 8, 8]
        
        def gaussfunc(x, width):
            return np.exp(-(x**2/width**2)/2)
        
        in_data = gf.twodpeak(gaussfunc, inpars, shape=(128,128), rotate=False)
        masked_data = np.ma.array(in_data)

        # fit should be independent of masked data value
        masked_data[64,64] = 1e6
        masked_data[64,64] = np.ma.masked
        fit1 = gf.peakfit(gaussfunc, masked_data, rotate=False)

        masked_data[64,64] = 0
        masked_data[64,64] = np.ma.masked
        fit2 = gf.peakfit(gaussfunc, masked_data, rotate=False)

        for v1, v2 in zip(fit1, fit2):
            self.assertAlmostEqual(v1, v2)

