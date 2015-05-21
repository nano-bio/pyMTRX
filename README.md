# pyMTRX
A Python module for reading the data files from Omicron NanoTechnology's MATRIX SPM system

---

**Author:** *Alex M. Pronschinske*

**Version:** *1.4.1*

Software Requirements
=====================

This package has the following direct dependencies:

 * python 2.7
 * numpy >= 1.5.1 (lower versions are untested)
 * matplotlib >= 1.1.0
 * python-pptx
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
 3. Install nose
 
> $pip install nose

 4. Install numpy 1.9.1 (always official 32-bit package) from .exe
 6. Install all matplotlib dependencies, using "pip install [package]":
  * six
  * python-dateutil
  * pytz
  * pyparsing
  * Pillow
 7. Install matplotlib 1.4.2 (always official 32-bit package) from .exe
 8. Install python-pptx

Installation Instructions (Ubuntu 14.04)
========================================

 1. Install python (probably already there)
 2. Install pip
 3. Install python-nose
 
> $sudo apt-get install python nose

 4. Install numpy:
 
> $sudo apt-get install python-numpy

 5. Install cython:
 
> $sudo apt-get install cython

 7. Install all matplotlib dependencies:
 
> $sudo apt-get build-dep python-matplotlib

 8. Install matplotlib:
 
> $sudo apt-get install python-matplotlib

 9. Install python-pptx:
 
> $sudo pip install python-pptx

