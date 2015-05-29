# pyMTRX
A Python module for reading the data files from Omicron NanoTechnology's MATRIX SPM system

---

**Author:** *Alex M. Pronschinske*

**Version:** *1.8.0*

Software Requirements
=====================

This package has the following direct dependencies:

 * python 2.7
 * numpy >= 1.6.0 (lower versions are untested)
 * matplotlib >= 1.1.0
 * python-pptx (optional)
 * Pillow

Known Bug List
==============

 * comments are timestamped with when the save button was click, and so they may not correspond perfectly to the image/spectrum they go with.  Especially for fast acquisition times


Improvement Goals
=================

 * Add options to notebook_slides script: colormaps, leveling


Installation Instructions (Windows 7)
=====================================

 1. Install python (32-bit, ignore OS type), and make sure to check the option for adding python.exe to system PATH
 2. Open command prompt
 3. Install nose by typing in the command prompt (starting after `$`): `$pip install nose`
 4. Install numpy 1.9.1 (always official 32-bit package) from .exe
 5. Install all matplotlib dependencies, using `$pip install [package_name_here]`:
  * six
  * python-dateutil
  * pytz
  * pyparsing
  * Pillow
 6. Install matplotlib 1.4.2 (always official 32-bit package) from .exe
 7. Install python-pptx: `$pip install python-pptx`
 8. Install pyMTRX: `$pip install pyMTRX`

Installation Instructions (Ubuntu 14.04)
========================================

 1. Install python (probably already there)
 2. Install pip
 3. Install python-nose: `$sudo apt-get install python nose`
 4. Install numpy: `$sudo apt-get install python-numpy`
 5. Install cython: `$sudo apt-get install cython`
 6. Install all matplotlib dependencies: `$sudo apt-get build-dep python-matplotlib`
 7. Install matplotlib: `$sudo apt-get install python-matplotlib`
 8. Install python-pptx: `$sudo pip install python-pptx`
 9. Install pyMTRX: `$sudo pip install pyMTRX`

Usage Example
=============

```
>>> import pyMTRX
>>> ex = pyMTRX.experiment('test_data/2014Oct09-090049_0001.mtrx')
>>> scans = ex.import_scan('2014Oct09-090049--1_122.Z_mtrx')
>>> scans[0][0].global_level()
>>> scans[0][0].save_png('image_of_data.png')
```
