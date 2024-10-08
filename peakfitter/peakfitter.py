"""
===========
peakfitter
===========
.. codeauthor:: Paul Grimes 12/2022, derived for code by Adam Ginsburg <adam.g.ginsburg@gmail.com> 3/17/08

Latest version available at <https://github.com/smithsonian/peakfitter>, where
it was forked from Gaussfitter <https://github.com/keflavich/gaussfitter>, 12/2022

"""
from __future__ import print_function, division, absolute_import

import itertools

import numpy as np
from numpy.ma import median
from numpy import pi
from scipy.special import genlaguerre


from .mpfit import mpfit

from .gaussfitter import moments
"""
Note about mpfit/leastsq:
I switched everything over to the Markwardt mpfit routine for a few reasons,
but foremost being the ability to set limits on parameters, not just force them
to be fixed.  As far as I can tell, leastsq does not have that capability.

The version of mpfit I use can be found here:
    http://code.google.com/p/agpy/source/browse/trunk/mpfit

Alternative: lmfit

.. todo::
    -turn into a class instead of a collection of objects
    -implement WCS-based gaussian fitting with correct coordinates
"""

def twodpeak_onedfunc(peakfunc, inpars, circle=False, rotate=True, vheight=True, shape=None):
    """
    Returns a 2d peak function of the form:
    x' = np.cos(rota) * x - np.sin(rota) * y
    y' = np.sin(rota) * x + np.cos(rota) * y
    (rota should be in degrees)
    g = b + a * <peakfunc>((x'-center_x), width_x) *
    <peakfunc>((y'-center_y), width_y)

    peakfunc (func) : 1d numpy ufunc that takes parameters of the form of [center, width]
    
    peakfunc should be nomralized to a maximum of 1.0.

    inpars = [b,a,center_x,center_y,width_x,width_y,rota]
             (b is background height, a is peak amplitude)
             
    where x and y are the input parameters of the returned function,
    and all other parameters are specified by this function.
    
    However, the above values are passed by list.  The list should be:
    inpars = (height,amplitude,center_x,center_y,width_x,width_y,rota)
    
    Widths are defined such that the peakfunc is reasonably approximated by
    a Gaussian peak with parameters inpar, so that calculating the moments of the 
    data to be fitted produces a reasonable starting point for the fitting.

    You can choose to ignore / neglect some of the above input parameters using
    the following options:

    Parameters
    ----------
    circle : bool
        default is an elliptical peak (different x, y widths), but can
        reduce the input by one parameter if it's a circular peak
    rotate : bool
        default allows rotation of the peak ellipse.  Can
        remove last parameter by setting rotate=0
    vheight : bool
        default allows a variable height-above-zero, i.e. an
        additive constant for the peak function.  Can remove first
        parameter by setting this to 0
    shape : tuple
        if shape is set (to a 2-parameter list) then returns an image with the
        peak defined by inpars
    """
    inpars_old = inpars
    inpars = list(inpars)
    if vheight:
        height = inpars.pop(0)
        height = float(height)
    else:
        height = float(0)
    amplitude, center_y, center_x = inpars.pop(0), inpars.pop(0), inpars.pop(0)
    amplitude = float(amplitude)
    center_x = float(center_x)
    center_y = float(center_y)
    if circle:
        width = inpars.pop(0)
        width_x = float(width)
        width_y = float(width)
        rotate = 0
    else:
        width_x, width_y = inpars.pop(0), inpars.pop(0)
        width_x = float(width_x)
        width_y = float(width_y)
    if rotate:
        rota = inpars.pop(0)
        rota = pi/180. * float(rota)
        rcen_x = center_x * np.cos(rota) - center_y * np.sin(rota)
        rcen_y = center_x * np.sin(rota) + center_y * np.cos(rota)
    else:
        rcen_x = center_x
        rcen_y = center_y
    if len(inpars) > 0:
        raise ValueError("There are still input parameters:" + str(inpars) +
                         " and you've input: " + str(inpars_old) +
                         " circle=%d, rotate=%d, vheight=%d" % (circle, rotate, vheight))

    def rotpeak(x, y):
        if rotate:
            xp = x * np.cos(rota) - y * np.sin(rota)
            yp = x * np.sin(rota) + y * np.cos(rota)
        else:
            xp = x
            yp = y
        g = height+amplitude*peakfunc(xp-rcen_x, width_x)*peakfunc(yp-rcen_y, width_y)
        return g
    if shape is not None:
        return rotpeak(*np.indices(shape))
    else:
        return rotpeak

def twodpeak(peakfunc, inpars, circle=False, rotate=True, vheight=True, shape=None):
    """
    Returns a 2d peak function of the form:
    x' = np.cos(rota) * x - np.sin(rota) * y
    y' = np.sin(rota) * x + np.cos(rota) * y
    (rota should be in degrees)
    g = b + a * <peakfunc>((x'-center_x), width_x) *
    <peakfunc>((y'-center_y), width_y)

    peakfunc (func) : 2d numpy ufunc that takes parameters of the form of inpars[2:6].
    
    peakfunc should be nomralized to a maximum of 1.0.

    inpars = [b,a,center_x,center_y,width_x,width_y,rota]
             (b is background height, a is peak amplitude)
             
    where x and y are the input parameters of the returned function,
    and all other parameters are specified by this function.
    
    However, the above values are passed by list.  The list should be:
    inpars = (height,amplitude,center_x,center_y,width_x,width_y,rota)
    
    Widths are defined such that the peakfunc is reasonably approximated by
    a Gaussian peak with parameters inpar, so that calculating the moments of the 
    data to be fitted produces a reasonable starting point for the fitting.

    You can choose to ignore / neglect some of the above input parameters using
    the following options:

    Parameters
    ----------
    circle : bool
        default is an elliptical peak (different x, y widths), but can
        reduce the input by one parameter if it's a circular peak
    rotate : bool
        default allows rotation of the peak ellipse.  Can
        remove last parameter by setting rotate=0
    vheight : bool
        default allows a variable height-above-zero, i.e. an
        additive constant for the peak function.  Can remove first
        parameter by setting this to 0
    shape : tuple
        if shape is set (to a 2-parameter list) then returns an image with the
        peak defined by inpars
    """
    inpars_old = inpars
    inpars = list(inpars)
    if vheight:
        height = inpars.pop(0)
        height = float(height)
    else:
        height = float(0)
    amplitude, center_y, center_x = inpars.pop(0), inpars.pop(0), inpars.pop(0)
    amplitude = float(amplitude)
    center_x = float(center_x)
    center_y = float(center_y)
    if circle:
        width = inpars.pop(0)
        width_x = float(width)
        width_y = float(width)
        rotate = 0
    else:
        width_x, width_y = inpars.pop(0), inpars.pop(0)
        width_x = float(width_x)
        width_y = float(width_y)
    if rotate:
        rota = inpars.pop(0)
        rota = pi/180. * float(rota)
        rcen_x = center_x * np.cos(rota) - center_y * np.sin(rota)
        rcen_y = center_x * np.sin(rota) + center_y * np.cos(rota)
    else:
        rcen_x = center_x
        rcen_y = center_y
    if len(inpars) > 0:
        raise ValueError("There are still input parameters:" + str(inpars) +
                         " and you've input: " + str(inpars_old) +
                         " circle=%d, rotate=%d, vheight=%d" % (circle, rotate, vheight))

    def rotpeak(x, y):
        if rotate:
            xp = x * np.cos(rota) - y * np.sin(rota)
            yp = x * np.sin(rota) + y * np.cos(rota)
        else:
            xp = x
            yp = y
        g = height+amplitude*peakfunc(xp-rcen_x, yp-rcen_y, width_x, width_y)
        return g
    if shape is not None:
        return rotpeak(*np.indices(shape))
    else:
        return rotpeak

def mm_laguerregauss_2d(inpars, max_p=1, max_l=0, circle=False, rotate=True, vheight=True, shape=None):
    """
    Returns a multimode 2d elliptical Laguerre-Gaussian beam of the form:
    x' = np.cos(rota) * x - np.sin(rota) * y
    y' = np.sin(rota) * x + np.cos(rota) * y
    (rota should be in degrees)
    g = a + Sum(p, l) {b * LG((x'-center_x)/width_x) *
    LG((y'-center_y)/width_y)}

    inpars = [a,[b,...], center_x,center_y,width_x,width_y,rota]
             (a is background height, b is a list of mode amplitudes)
             
    The maximum number of modes to fit are set by max_p and max_l.
    
    the final elements of inpars are a ravelled list of mode amplitudes for modes of order (p, l).  
             
    However, the above values are passed by list.  The list should be:
    inpars = (height,amplitudes,center_x,center_y,width_x,width_y,rota)
    
    If the beam canb be reasonably approximated by
    a fundamental Gaussian peak with parameters inpar, calculating the moments of the 
    data to be fitted produces a reasonable starting point for the fitting.

    You can choose to ignore / neglect some of the above input parameters using
    the following options:

    Parameters
    ----------
    circle : bool
        default is an elliptical peak (different x, y widths), but can
        reduce the input by one parameter if it's a circular peak
    rotate : bool
        default allows rotation of the peak ellipse.  Can
        remove last parameter by setting rotate=0
    vheight : bool
        default allows a variable height-above-zero, i.e. an
        additive constant for the peak function.  Can remove first
        parameter by setting this to 0
    shape : tuple
        if shape is set (to a 2-parameter list) then returns an image with the
        peak defined by inpars
    """
    inpars_old = inpars
    inpars = list(inpars)
    
    if max_l == 0:
        amplen = max_p+1
        amps = np.array(inpars[-amplen:])
        ampshape = amps.shape
    else:
        amplen = (max_p+1)*(max_l+1)
        ampshape = (max_p+1, max_l+1)
        amps = np.reshape(np.array(inpars[-amplen:]), ampshape)
    
    del inpars[-amplen:]
    
    if vheight:
        height = inpars.pop(0)
        height = float(height)
    else:
        height = float(0)
    center_x, center_y = inpars.pop(0), inpars.pop(0)
    center_x = float(center_x)
    center_y = float(center_y)
    if circle:
        width = inpars.pop(0)
        width_x = float(width)
        width_y = float(width)
        rotate = 0
    else:
        width_x, width_y = inpars.pop(0), inpars.pop(0)
        width_x = float(width_x)
        width_y = float(width_y)
    if rotate:
        rota = inpars.pop(0)
        rota = pi/180. * float(rota)
        rcen_x = center_x * np.cos(rota) - center_y * np.sin(rota)
        rcen_y = center_x * np.sin(rota) + center_y * np.cos(rota)
    else:
        rcen_x = center_x
        rcen_y = center_y
        
    if len(inpars) > 0:
        raise ValueError("There are still input parameters:" + str(inpars) +
                         " and you've input: " + str(inpars_old) +
                         " circle=%d, rotate=%d, vheight=%d" % (circle, rotate, vheight))
        
    def rotpeak(x, y):
        if rotate:
            xp = ((x * np.cos(rota) - y * np.sin(rota))-rcen_x)/width_x
            yp = ((x * np.sin(rota) + y * np.cos(rota))-rcen_y)/width_y
        else:
            xp = x/width_x
            yp = y/width_y
        
        g = height
    
        for p in range(max_p+1):
            for l in range(max_l+1):
                if max_l == 0:
                    amp = amps[p]
                else:
                    amp = amps[p,l]
                g = g + float(amp)*laguerre_gauss2d(xp, yp, p, l)
        return np.abs(g)**2
    
    if shape is not None:
        return rotpeak(*np.indices(shape))
    else:
        return rotpeak


def laguerre_gauss2d(x, y, p, l):
    """Return the (p,l)th 2d Laguerre Gauss mode amplitude profile.
    
    Parameters:
        x (np.ndarray) : array of normalized x positions in the mode.
        y (np.ndarray) : array of normalized x positions in the mode.
        p (int)        : radial mode number.
        l (int)        : azimuthal mode number.
        
    Returns:
        np.ndarray : array of mode amplitudes."""

    r = np.sqrt(x**2 + y**2)
    phi = np.arctan2(y,x)

    c_lp = np.sqrt(2*np.math.factorial(p)/(np.pi*np.math.factorial(p+abs(l))))
    
    l_lp = genlaguerre(p, abs(l))(2*r**2)
    
    return c_lp * l_lp * (r*np.sqrt(2))**abs(l) * np.exp(-(r**2)) * np.exp(-1j*l*phi)


def mm_laguerregauss2d_fit(data, max_p=1, max_l=0, err=None, params=(), autoderiv=True, return_error=False,
             circle=False, fixed=np.repeat(False, 6),
             limitedmin=[False, True, True, True, True, True],
             limitedmax=[False, False, False, False, False, True],
             usemoment=np.array([], dtype='bool'), minpars=np.repeat(0, 6),
             maxpars=np.array([0, 0, 0, 0, 0, 180]), minamp=0.0, maxamp=2.0, limitedampmin=True, limitedampmax=False, rotate=True, vheight=True,
             quiet=True, returnmp=False, returnfitimage=False, **kwargs):
    """
    Peak fitter with the ability to fit multimode Laguerre-Gaussian mode intensities

    Parameters
    ----------
    data : `numpy.ndarray`
        2-dimensional data array
    max_p : `int`
        Highest radial mode number to include
    max_l : `int`
        Highest azimuthal mode number to include
    err : `numpy.ndarray` or None
        error array with same size as data array.  Defaults to 1 everywhere.
    params : (background, x, y, width_x, width_y, rota, amplitudes)
        Initial input parameters for Gaussian function.  If not input, these
        will be determined from the moments of the system, assuming no rotation
    autoderiv : bool
        Use the autoderiv provided in the lmder.f function (the alternative is
        to us an analytic derivative with lmdif.f: this method is less robust)
    return_error : bool
        Default is to return only the Gaussian parameters.
        If ``True``, return fit params & fit error
    returnfitimage : bool
        returns (best fit params,best fit image)
    returnmp : bool
        returns the full mpfit struct
    circle : bool
        The default is to fit an elliptical gaussian (different x, y widths),
        but the input is reduced by one parameter if it's a circular gaussian.
    rotate : bool
        Allow rotation of the gaussian ellipse.  Can remove
        last parameter of input & fit by setting rotate=False.
        Angle should be specified in degrees.
    vheight : bool
        Allows a variable height-above-zero, i.e. an additive constant
        background for the Gaussian function.  Can remove the first fitter
        parameter by setting this to ``False``
    usemoment : `numpy.ndarray`, dtype='bool'
        Array to choose which parameters to use a moment estimation for.  Other
        parameters will be taken from params.

    Returns
    -------
    (params, [parerr], [fitimage]) | (mpfit, [fitimage])
    parameters : list
        The default output is a set of Gaussian parameters with the same shape
        as the input parameters
    fitimage : `numpy.ndarray`
        If returnfitimage==True, the last return will be a 2D array holding the
        best-fit model
    mpfit : `mpfit` object
        If ``returnmp==True`` returns a `mpfit` object. This object contains a
        `covar` attribute which is the 7x7 covariance array generated by the
        mpfit class in the `mpfit_custom.py` module. It contains a `param`
        attribute that contains a list of the best fit parameters in the same
        order as the optional input parameter `params`.
    """
    data = data.view(np.ma.MaskedArray).view('float')
    usemoment = np.array(usemoment, dtype='bool')
    
    amplen = (max_p+1)*(max_l+1)
    ampshape = (max_p+1, max_l+1)
    amps = np.repeat(0, amplen)
    
    modenum = list(itertools.product(range(max_p+1), range(max_l+1)))
    
    params = np.array(params, dtype='float')
    if usemoment.any() and len(params) == len(usemoment):
        moms = moments(data, circle, rotate, vheight, **kwargs)
        # Take the amplitude from the moments and and put into the amplitude list for mode (0,0)
        if vheight:
            amps[0] = moms.pop(1)
        else:
            amps[0] = moms.pop(0)
        moment = np.array(moms, dtype='float')
        params[usemoment] = moment[usemoment]    
    elif params == [] or len(params) == 0:
        params = (moments(data, circle, rotate, vheight, **kwargs))
        # Take the amplitude from the moments and and put into the amplitude list for mode (0,0)
        if vheight:
            amps[0] = params.pop(1)
        else:
            amps[0] = params.pop(0)
    
    
    if not vheight:
        # If vheight is not set, we set it for sub-function calls but fix the
        # parameter at zero
        vheight=True
        params = np.concatenate([[0],params])
        fixed[0] = 1

    # mpfit will fail if it is given a start parameter outside the allowed range:
    for i in range(len(params)):
        if params[i] > maxpars[i] and limitedmax[i]: params[i] = maxpars[i]
        if params[i] < minpars[i] and limitedmin[i]: params[i] = minpars[i]
            
    for i in range(len(amps)):
        if amps[i] > maxamp and limitedampmax: amps[i] = maxamp
        if amps[i] < minamp and limitedampmin: amps[i] = minamp
        
    params = np.concatenate((params, amps))

    # One time: check if error is set, otherwise fix it at 1.
    err = err if err is not None else 1.0

    def mpfitfun(data, err):
        def f(p, fjac):
            twodp = mm_laguerregauss_2d(p, max_p=max_p, max_l=max_l, circle=circle, rotate=rotate, vheight=vheight)
            delta = (data - twodp(*np.indices(data.shape))) / err
            return [0, delta.compressed()]
        return f

    parinfo = [{'n': 1, 'value': params[1], 'limits': [minpars[1], maxpars[1]],
                'limited': [limitedmin[1], limitedmax[1]], 'fixed': fixed[1],
                'parname': "XSHIFT", 'error': 0},
               {'n': 2, 'value': params[2], 'limits': [minpars[2], maxpars[2]],
                'limited': [limitedmin[2], limitedmax[2]], 'fixed': fixed[2],
                'parname': "YSHIFT", 'error': 0},
               {'n': 3, 'value': params[3], 'limits': [minpars[3], maxpars[3]],
                'limited': [limitedmin[3], limitedmax[3]], 'fixed': fixed[3],
                'parname': "XWIDTH", 'error': 0}]
    if vheight:
        parinfo.insert(0, {'n': 0, 'value': params[0], 'limits': [minpars[0], maxpars[0]],
                           'limited': [limitedmin[0], limitedmax[0]], 'fixed': fixed[0],
                           'parname': "HEIGHT", 'error': 0})
    if not circle:
        parinfo.append({'n': 4, 'value': params[4], 'limits': [minpars[4], maxpars[4]],
                        'limited': [limitedmin[4], limitedmax[4]], 'fixed': fixed[4],
                        'parname': "YWIDTH", 'error': 0})
        if rotate:
            parinfo.append({'n': 5, 'value': params[5], 'limits': [minpars[5], maxpars[5]],
                            'limited': [limitedmin[5], limitedmax[5]], 'fixed': fixed[5],
                            'parname': "ROTATION", 'error': 0})
            
    n = parinfo[-1]['n'] + 1
    for i, a in enumerate(amps):
        parinfo.append({'n': n+i, 'value': params[n+1], 'limits': [minamp, maxamp], 
                        'limited': [limitedampmin, limitedampmax], 'fixed': False,
                        'parname': f"MODEAMP {modenum[i]}", 'error': 0})

    if not autoderiv:
        raise NotImplementedError("I'm sorry, I haven't implemented this feature yet.  "
                                  "Given that I wrote this message in 2008, "
                                  "it will probably never be implemented.")
    else:
        mp = mpfit(mpfitfun(data, err), parinfo=parinfo, quiet=quiet)

    if mp.errmsg:
        raise Exception("MPFIT error: {0}".format(mp.errmsg))

    if (not circle) and rotate:
        mp.params[-1] %= 180.0

    mp.chi2 = mp.fnorm
    try:
        mp.chi2n = mp.fnorm/mp.dof
    except ZeroDivisionError:
        mp.chi2n = np.nan

    if returnmp:
        returns = (mp)
    elif return_error:
        returns = mp.params, mp.perror
    else:
        returns = mp.params
    if returnfitimage:
        fitimage = mm_laguerregauss_2d(mp.params, max_p=max_p, max_l=max_l, circle=circle, rotate=rotate, vheight=vheight)(*np.indices(data.shape))
        returns = (returns, fitimage)
    return returns


def peakfit(peakfunc, data, err=None, params=(), autoderiv=True, return_error=False,
             circle=False, fixed=np.repeat(False, 7),
             limitedmin=[False, False, False, False, True, True, True],
             limitedmax=[False, False, False, False, False, False, True],
             usemoment=np.array([], dtype='bool'), minpars=np.repeat(0, 7),
             maxpars=[0, 0, 0, 0, 0, 0, 180], rotate=True, vheight=True,
             quiet=True, returnmp=False, returnfitimage=False, **kwargs):
    """
    Peak fitter with the ability to fit a variety of different forms of
    2-dimensional peaks.

    Parameters
    ----------
    data : `numpy.ndarray`
        2-dimensional data array
    peakfunc : `numpy.ufunc`
        1-dimensional function with signature `(x_vals, width)` that returns a
        peaked function that can be approximated by a Gaussian of `width`
    err : `numpy.ndarray` or None
        error array with same size as data array.  Defaults to 1 everywhere.
    params : (height, amplitude, x, y, width_x, width_y, rota)
        Initial input parameters for Gaussian function.  If not input, these
        will be determined from the moments of the system, assuming no rotation
    autoderiv : bool
        Use the autoderiv provided in the lmder.f function (the alternative is
        to us an analytic derivative with lmdif.f: this method is less robust)
    return_error : bool
        Default is to return only the Gaussian parameters.
        If ``True``, return fit params & fit error
    returnfitimage : bool
        returns (best fit params,best fit image)
    returnmp : bool
        returns the full mpfit struct
    circle : bool
        The default is to fit an elliptical gaussian (different x, y widths),
        but the input is reduced by one parameter if it's a circular gaussian.
    rotate : bool
        Allow rotation of the gaussian ellipse.  Can remove
        last parameter of input & fit by setting rotate=False.
        Angle should be specified in degrees.
    vheight : bool
        Allows a variable height-above-zero, i.e. an additive constant
        background for the Gaussian function.  Can remove the first fitter
        parameter by setting this to ``False``
    usemoment : `numpy.ndarray`, dtype='bool'
        Array to choose which parameters to use a moment estimation for.  Other
        parameters will be taken from params.

    Returns
    -------
    (params, [parerr], [fitimage]) | (mpfit, [fitimage])
    parameters : list
        The default output is a set of Gaussian parameters with the same shape
        as the input parameters
    fitimage : `numpy.ndarray`
        If returnfitimage==True, the last return will be a 2D array holding the
        best-fit model
    mpfit : `mpfit` object
        If ``returnmp==True`` returns a `mpfit` object. This object contains a
        `covar` attribute which is the 7x7 covariance array generated by the
        mpfit class in the `mpfit_custom.py` module. It contains a `param`
        attribute that contains a list of the best fit parameters in the same
        order as the optional input parameter `params`.
    """
    data = data.view(np.ma.MaskedArray).view('float')
    usemoment = np.array(usemoment, dtype='bool')
    params = np.array(params, dtype='float')
    if usemoment.any() and len(params) == len(usemoment):
        moment = np.array(moments(data, circle, rotate, vheight, **kwargs), dtype='float')
        params[usemoment] = moment[usemoment]
    elif params == [] or len(params) == 0:
        params = (moments(data, circle, rotate, vheight, **kwargs))
    if not vheight:
        # If vheight is not set, we set it for sub-function calls but fix the
        # parameter at zero
        vheight=True
        params = np.concatenate([[0],params])
        fixed[0] = 1

    # mpfit will fail if it is given a start parameter outside the allowed range:
    for i in range(len(params)):
        if params[i] > maxpars[i] and limitedmax[i]: params[i] = maxpars[i]
        if params[i] < minpars[i] and limitedmin[i]: params[i] = minpars[i]

    # One time: check if error is set, otherwise fix it at 1.
    err = err if err is not None else 1.0

    def mpfitfun(data, err):
        def f(p, fjac):
            twodp = twodpeak(peakfunc, p, circle, rotate, vheight)
            delta = (data - twodp(*np.indices(data.shape))) / err
            return [0, delta.compressed()]
        return f

    parinfo = [{'n': 1, 'value': params[1], 'limits': [minpars[1], maxpars[1]],
                'limited': [limitedmin[1], limitedmax[1]], 'fixed': fixed[1],
                'parname': "AMPLITUDE", 'error': 0},
               {'n': 2, 'value': params[2], 'limits': [minpars[2], maxpars[2]],
                'limited': [limitedmin[2], limitedmax[2]], 'fixed': fixed[2],
                'parname': "XSHIFT", 'error': 0},
               {'n': 3, 'value': params[3], 'limits': [minpars[3], maxpars[3]],
                'limited': [limitedmin[3], limitedmax[3]], 'fixed': fixed[3],
                'parname': "YSHIFT", 'error': 0},
               {'n': 4, 'value': params[4], 'limits': [minpars[4], maxpars[4]],
                'limited': [limitedmin[4], limitedmax[4]], 'fixed': fixed[4],
                'parname': "XWIDTH", 'error': 0}]
    if vheight:
        parinfo.insert(0, {'n': 0, 'value': params[0], 'limits': [minpars[0], maxpars[0]],
                           'limited': [limitedmin[0], limitedmax[0]], 'fixed': fixed[0],
                           'parname': "HEIGHT", 'error': 0})
    if not circle:
        parinfo.append({'n': 5, 'value': params[5], 'limits': [minpars[5], maxpars[5]],
                        'limited': [limitedmin[5], limitedmax[5]], 'fixed': fixed[5],
                        'parname': "YWIDTH", 'error': 0})
        if rotate:
            parinfo.append({'n': 6, 'value': params[6], 'limits': [minpars[6], maxpars[6]],
                            'limited': [limitedmin[6], limitedmax[6]], 'fixed': fixed[6],
                            'parname': "ROTATION", 'error': 0})

    if not autoderiv:
        # the analytic derivative, while not terribly difficult, is less
        # efficient and useful.  I only bothered putting it here because I was
        # instructed to do so for a class project - please ask if you would
        # like this feature implemented
        raise NotImplementedError("I'm sorry, I haven't implemented this feature yet.  "
                                  "Given that I wrote this message in 2008, "
                                  "it will probably never be implemented.")
    else:
        mp = mpfit(mpfitfun(data, err), parinfo=parinfo, quiet=quiet)

    if mp.errmsg:
        raise Exception("MPFIT error: {0}".format(mp.errmsg))

    if (not circle) and rotate:
        mp.params[-1] %= 180.0

    mp.chi2 = mp.fnorm
    try:
        mp.chi2n = mp.fnorm/mp.dof
    except ZeroDivisionError:
        mp.chi2n = np.nan

    if returnmp:
        returns = (mp)
    elif return_error:
        returns = mp.params,mp.perror
    else:
        returns = mp.params
    if returnfitimage:
        fitimage = twodpeak(peakfunc, mp.params, circle, rotate, vheight)(*np.indices(data.shape))
        returns = (returns, fitimage)
    return returns

def onedmoments(Xax, data, vheight=True, estimator=median, negamp=None,
                veryverbose=False, **kwargs):
    """Returns (height, amplitude, x, width_x)
    the gaussian parameters of a 1D distribution by calculating its
    moments.  Depending on the input parameters, will only output
    a subset of the above.

    If using masked arrays, pass estimator=np.ma.median
    'estimator' is used to measure the background level (height)

    negamp can be used to force the peak negative (True), positive (False),
    or it will be "autodetected" (negamp=None)
    """

    dx = np.mean(Xax[1:] - Xax[:-1])  # assume a regular grid
    integral = (data*dx).sum()
    height = estimator(data)

    # try to figure out whether pos or neg based on the minimum width of the pos/neg peaks
    Lpeakintegral = integral - height*len(Xax)*dx - (data[data > height]*dx).sum()
    Lamplitude = data.min()-height
    Lwidth_x = 0.5*(np.abs(Lpeakintegral / Lamplitude))
    Hpeakintegral = integral - height*len(Xax)*dx - (data[data < height]*dx).sum()
    Hamplitude = data.max()-height
    Hwidth_x = 0.5*(np.abs(Hpeakintegral / Hamplitude))
    Lstddev = Xax[data < data.mean()].std()
    Hstddev = Xax[data > data.mean()].std()
    # print "Lstddev: %10.3g  Hstddev: %10.3g" % (Lstddev,Hstddev)
    # print "Lwidth_x: %10.3g  Hwidth_x: %10.3g" % (Lwidth_x,Hwidth_x)

    if negamp:  # can force the guess to be negative
        xcen, amplitude, width_x = Xax[np.argmin(data)], Lamplitude, Lwidth_x
    elif negamp is None:
        if Hstddev < Lstddev:
            xcen, amplitude, width_x, = Xax[np.argmax(data)], Hamplitude, Hwidth_x
        else:
            xcen, amplitude, width_x, = Xax[np.argmin(data)], Lamplitude, Lwidth_x
    else:  # if negamp==False, make positive
        xcen, amplitude, width_x = Xax[np.argmax(data)], Hamplitude, Hwidth_x

    if veryverbose:
        print("negamp: %s  amp,width,cen Lower: %g, %g   Upper: %g, %g  Center: %g" %\
              (negamp, Lamplitude, Lwidth_x, Hamplitude, Hwidth_x, xcen))
    mylist = [amplitude, xcen, width_x]
    if np.isnan(width_x) or np.isnan(height) or np.isnan(amplitude):
        raise ValueError("something is nan")
    if vheight:
        mylist = [height] + mylist
    return mylist


def onedpeak(peakfunc, x, H, A, dx, w):
    """
    Returns a 1-dimensional peak of form
    H+A*peakfunc((x-dx), w)
    """
    return H+A*peakfunc((x-dx), w)


def onedpeakfit(peakfunc, xax, data, err=None,
                 params=[0, 1, 0, 1], fixed=[False, False, False, False],
                 limitedmin=[False, False, False, True],
                 limitedmax=[False, False, False, False],
                 minpars=[0, 0, 0, 0], maxpars=[0, 0, 0, 0],
                 quiet=True, shh=True, veryverbose=False,
                 vheight=True, negamp=False, usemoments=False):
    """
    Parameters
    ----------
    peakfunc : np.ufunc
        peaked normalized function to fit to data
    xax : np.array
        x axis
    data : np.array
        y axis
    err : np.array
        error corresponding to data
    params : tuple
        Fit parameters: Height of background, Amplitude, Shift, Width
    fixed : bool
        Is parameter fixed?
    limitedmin/minpars : tuple
        set lower limits on each parameter (default: width>0)
    limitedmax/maxpars : tuple
        set upper limits on each parameter
    quiet : bool
        should MPFIT output each iteration?
    shh : bool
        output final parameters?
    usemoments : bool
        replace default parameters with moments

    Returns
    -------
    Fit parameters
    Model
    Fit errors
    chi2
    """

    def mpfitfun(peakfunc, x, y, err):
        if err is None:
            def f(p, fjac=None): return [0, (y-onedpeak(x, *p, peakfunc))]
        else:
            def f(p, fjac=None): return [0, (y-onedpeak(x, *p, peakfunc))/err]
        return f

    if xax is None:
        xax = np.arange(len(data))

    if not vheight:
        height = params[0]
        fixed[0] = True
    if usemoments:
        params = onedmoments(xax, data, vheight=vheight, negamp=negamp, veryverbose=veryverbose)
        if vheight is False:
            params = [height]+params
        if veryverbose:
            print("OneD moments: h: %g  a: %g  c: %g  w: %g" % tuple(params))

    parinfo = [{'n': 0, 'value': params[0], 'limits': [minpars[0], maxpars[0]],
                'limited': [limitedmin[0], limitedmax[0]], 'fixed': fixed[0],
                'parname': "HEIGHT", 'error': 0},
               {'n': 1, 'value': params[1], 'limits': [minpars[1], maxpars[1]],
                'limited': [limitedmin[1], limitedmax[1]], 'fixed': fixed[1],
                'parname': "AMPLITUDE", 'error': 0},
               {'n': 2, 'value': params[2], 'limits': [minpars[2], maxpars[2]],
                'limited': [limitedmin[2], limitedmax[2]], 'fixed': fixed[2],
                'parname': "SHIFT", 'error': 0},
               {'n': 3, 'value': params[3], 'limits': [minpars[3], maxpars[3]],
                'limited': [limitedmin[3], limitedmax[3]], 'fixed': fixed[3],
                'parname': "WIDTH", 'error': 0}]

    mp = mpfit(mpfitfun(peakfunc, xax, data, err), parinfo=parinfo, quiet=quiet)
    mpp = mp.params
    mpperr = mp.perror
    chi2 = mp.fnorm

    if mp.status == 0:
        raise Exception(mp.errmsg)

    if (not shh) or veryverbose:
        print("Fit status: ", mp.status)
        for i, p in enumerate(mpp):
            parinfo[i]['value'] = p
            print(parinfo[i]['parname'], p, " +/- ", mpperr[i])
        print("Chi2: ", mp.fnorm, " Reduced Chi2: ", mp.fnorm/len(data), " DOF:", len(data)-len(mpp))

    return mpp, onedpeak(peakfunc, xax, *mpp), mpperr, chi2


def n_peak(peakfunc, pars=None, a=None, dx=None, sigma=None):
    """
    Returns a function that sums over N peaks of shape peakfunc, where N is the length of
    a,dx,sigma *OR* N = len(pars) / 3

    The background "height" is assumed to be zero (you must "baseline" your
    spectrum before fitting)

    pars  - a list with len(pars) = 3n, assuming a,dx,sigma repeated
    dx    - offset (velocity center) values
    sigma - line widths
    a     - amplitudes
    """
    if len(pars) % 3 == 0:
        a = [pars[ii] for ii in range(0, len(pars), 3)]
        dx = [pars[ii] for ii in range(1, len(pars), 3)]
        sigma = [pars[ii] for ii in range(2, len(pars), 3)]
    elif not(len(dx) == len(sigma) == len(a)):
        raise ValueError("Wrong array lengths! dx: %i  sigma: %i  a: %i" %
                         (len(dx), len(sigma), len(a)))

    def g(x):
        v = np.zeros(len(x))
        for i in range(len(dx)):
            v += a[i] * peakfunc(x-dx[i], sigma[i])
        return v
    return g


def multipeakfit(peakfunc, xax, data, npeak=1, err=None, params=[1, 0, 1],
                  fixed=[False, False, False], limitedmin=[False, False, True],
                  limitedmax=[False, False, False], minpars=[0, 0, 0],
                  maxpars=[0, 0, 0],
                  quiet=True, shh=True, veryverbose=False):
    """
    An improvement on onedpeakfit.  Lets you fit multiple peaks.

    Parameters
    ----------
    peakfunc : np.ufunc
      normalized peaked function to fit to data, of signature `(x-center, width)`.
    xax : np.array
      x axis
    data : np.array
      y axis
    err : np.array or None
      error corresponding to data
    ngauss : int
      How many gaussians to fit?  Default 1 (this could supersede
      onedgaussfit). Parameters below need to have lenght of 3*ngauss. If
      ``ngauss``>1 and their lenght is 3, they will be replicated ngaus
      times, otherwise they will be reset to defaults.
    params : list
      Fit parameters: [amplitude, offset, width] * ngauss
      If len(params) % 3 == 0, ngauss will be set to len(params) / 3
    fixed : list of bools
      Is parameter fixed?
    limitedmin/minpars : list
      set lower limits on each parameter (default: width>0)
    limitedmax/maxpars : list
      set upper limits on each parameter
    minpars : list

    maxpars : list

    quiet : bool
      should MPFIT output each iteration?
    shh : bool
      output final parameters?
    veryverbose : bool

    Returns
    -------
    Fit parameters
    Model
    Fit errors
    chi2

    """

    if len(params) != npeak and (len(params) // 3) > npeak:
        npeak = len(params) // 3

    if isinstance(params, np.ndarray):
        params = params.tolist()

    # make sure all various things are the right length; if they're not, fix them using the defaults
    for parlist in (params, fixed, limitedmin, limitedmax, minpars, maxpars):
        if len(parlist) != 3*npeak:
            # if you leave the defaults, or enter something that can be multiplied by 3 to get
            # to the right number of peaks, it will just replicate
            if len(parlist) == 3:
                parlist *= npeak
            elif parlist == params:
                parlist[:] = [1, 0, 1] * npeak
            elif parlist == fixed or parlist == limitedmax:
                parlist[:] = [False, False, False] * npeak
            elif parlist == limitedmin:
                parlist[:] = [False, False, True] * npeak
            elif parlist == minpars or parlist == maxpars:
                parlist[:] = [0, 0, 0] * npeak

    def mpfitfun(x, y, err):
        if err is None:
            def f(p, fjac=None): return [0, (y-n_peak(peakfunc, pars=p)(x))]
        else:
            def f(p, fjac=None): return [0, (y-n_peak(peakfunc, pars=p)(x))/err]
        return f

    if xax is None:
        xax = np.arange(len(data))

    parnames = {0: "AMPLITUDE", 1: "SHIFT", 2: "WIDTH"}

    parinfo = [{'n': ii, 'value': params[ii],
                'limits': [minpars[ii], maxpars[ii]],
                'limited': [limitedmin[ii], limitedmax[ii]], 'fixed': fixed[ii],
                'parname': parnames[ii % 3]+str(ii % 3), 'error': ii}
               for ii in range(len(params))]

    if veryverbose:
        print("GUESSES: ")
        print("\n".join(["%s: %s" % (p['parname'], p['value']) for p in parinfo]))

    mp = mpfit(mpfitfun(xax, data, err), parinfo=parinfo, quiet=quiet)
    mpp = mp.params
    mpperr = mp.perror
    chi2 = mp.fnorm

    if mp.status == 0:
        raise Exception(mp.errmsg)

    if not shh:
        print("Final fit values: ")
        for i, p in enumerate(mpp):
            parinfo[i]['value'] = p
            print(parinfo[i]['parname'], p, " +/- ", mpperr[i])
        print("Chi2: ", mp.fnorm, " Reduced Chi2: ", mp.fnorm/len(data), " DOF:", len(data)-len(mpp))

    return mpp, n_peak(peakfunc, pars=mpp)(xax), mpperr, chi2


def collapse_peakfit(peakfunc, cube, xax=None, axis=2, negamp=False, usemoments=True,
                      nsigcut=1.0, mppsigcut=1.0, return_errors=False, **kwargs):
    import time
    std_coll = cube.std(axis=axis)
    std_coll[std_coll == 0] = np.nan  # must eliminate all-zero spectra
    mean_std = median(std_coll[std_coll == std_coll])
    if axis > 0:
        cube = cube.swapaxes(0, axis)
    width_arr = np.zeros(cube.shape[1:]) + np.nan
    amp_arr = np.zeros(cube.shape[1:]) + np.nan
    chi2_arr = np.zeros(cube.shape[1:]) + np.nan
    offset_arr = np.zeros(cube.shape[1:]) + np.nan
    width_err = np.zeros(cube.shape[1:]) + np.nan
    amp_err = np.zeros(cube.shape[1:]) + np.nan
    offset_err = np.zeros(cube.shape[1:]) + np.nan
    if xax is None:
        xax = np.arange(cube.shape[0])
    starttime = time.time()
    print("Cube shape: ", cube.shape)
    extremum = np.min if negamp else np.max
    print("Fitting a total of %i spectra with peak signal above %f" %\
          ((np.abs(extremum(cube, axis=0)) > (mean_std*nsigcut)).sum(),
           mean_std*nsigcut))
    for i in range(cube.shape[1]):
        t0 = time.time()
        nspec = (np.abs(extremum(cube[:,i,:], axis=0)) > (mean_std*nsigcut)).sum()
        print("Working on row %d with %d spectra to fit" % (i, nspec), end=' ')
        for j in range(cube.shape[2]):
            if np.abs(extremum(cube[:,i,j])) > (mean_std*nsigcut):
                mpp, gfit, mpperr, chi2 = onedpeakfit(peakfunc, xax, cube[:,i,j],
                    err=np.ones(cube.shape[0])*mean_std, negamp=negamp,
                    usemoments=usemoments, **kwargs)
                if np.abs(mpp[1]) > (mpperr[1]*mppsigcut):
                    width_arr[i,j] = mpp[3]
                    offset_arr[i,j] = mpp[2]
                    chi2_arr[i,j] = chi2
                    amp_arr[i,j] = mpp[1]
                    width_err[i,j] = mpperr[3]
                    offset_err[i,j] = mpperr[2]
                    amp_err[i,j] = mpperr[1]
        dt = time.time()-t0
        if nspec > 0:
            print("in %f seconds (average: %f)" % (dt, dt/float(nspec)))
        else:
            print("in %f seconds" % (dt))
    print("Total time %f seconds" % (time.time()-starttime))

    if return_errors:
        return width_arr, offset_arr, amp_arr, width_err, offset_err, amp_err, chi2_arr
    else:
        return width_arr, offset_arr, amp_arr, chi2_arr
