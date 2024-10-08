# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
This is an Astropy affiliated package.
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *
# ----------------------------------------------------------------------------


# For egg_info test builds to pass, put package imports here.
if not _ASTROPY_SETUP_:
    from .gaussfitter import (collapse_gaussfit, gaussfit, moments, multigaussfit,
                             n_gaussian, onedgaussfit, onedgaussian, onedmoments,
                             twodgaussian)
    from .peakfitter import (collapse_peakfit, peakfit, multipeakfit,
                            n_peak, onedpeakfit, onedpeak,
                            twodpeak, mm_laguerregauss_2d, mm_laguerregauss2d_fit, laguerre_gauss2d)
