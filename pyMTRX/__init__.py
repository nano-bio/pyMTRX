# -*- encoding: UTF-8 -*-
'''pyMTRX Package Initialization Module
    
    This classes in this package can be used to read MATRIX SPM files into
    python data structures.  Generally it will be sufficient to import only
    the Experiment class from this module:
        from pyMTRX.experiment import Experiment
'''

# All functions and classes from the following modules should be imported as
# native parts of the spectroscopy package
from experiment import *
from curves import *
from scan import *
from scripts import *

__version__ = '1.8.0'