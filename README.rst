Peakfitter
===========

Generalization of [Gaussfitter](https://github.com/keflavich/gaussfitter) to add additional peak shapes, such as Bessel functions.

Installation: ::

   pip install https://github.com/smithsonian/peakfitter/archive/master.zip
   
or

    pip install -e git+https://github.com/smithsonian/peakfitter.git#egg=peakfitter
 
or

   git clone https://github.com/smithsonian/peakfitter.git
   cd peakfitter
   python setup.py install 


The gaussfitter code was taken from agpy, where it has resided for a long time and has had
a long, glorious history.


In short: This is a small toolkit for fitting 2D gaussians and other peaked distributions.  It makes use of
mpfit.py by Sergei Koposov
(https://code.google.com/p/astrolibpy/source/browse/), and a modified version
of his code is included (by necessity) here.  It is modified primarily to
remove a scipy dependency.

Examples to come!  PRs welcome!

Tested in Python 3.8
