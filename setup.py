#!/usr/bin/env python

from distutils.core import setup

setup( name='pyMTRX',
       version='1.5.0',
       description="Omicron NanoTechnology MATRIX SPM Support",
       author='Alex Pronschinske',
       url='https://www.github.com/ampron',
       packages=['pyMTRX',],
       scripts=[ 'scripts/convert_spec.py',
                 'scripts/notebook_sheet.py',
                 'scripts/notebook_slides.py',
               ],
     )