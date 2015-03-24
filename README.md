# pyMTRX
A Python module for reading the results files from Omicron NanoTechnology's MATRIX SPM system

---

**Author:** *Dr. Alex M. Pronschinske*

**Version:** *development*

Software Requirements
=====================

This package has the following dependencies:

    * python 2.7
    * numpy >= 1.5.1 (lower versions are untested)
    * scipy >= 0.9.0 (lower versions are untested)
    * matplotlib >= 1.1.0

Known Bug List
==============



Improvement Goals
=================


Installation Instructions (Windows 7)
=====================================

    1. Install python (32-bit, ignore OS type), and make sure to check the option for adding python.exe to system PATH
    2. Open command prompt
    3. Install nose
>       $pip install nose

    4. Install numpy 1.9.1 (always official 32-bit package) from .exe
    5. Install scipy 0.15.0 (always official 32-bit package) from .exe
    6. Install all matplotlib dependencies, using "pip install [package]":
        * six
        * python-dateutil
        * pytz
        * pyparsing
        * Pillow
    7. Install matplotlib 1.4.2 (always official 32-bit package) from .exe
    8. Install scikit-learn
>        $pip install scikit-learn

    9. Install pypng; $pip install pypng

Installation Instructions (Ubuntu 14.04)
========================================

    1. Install python (probably already there)
    2. Install pip
    3. Install python-nose
>       $sudo apt-get install python nose

    4. Install numpy:
>       $sudo apt-get install python-numpy

    5. Install cython:
        $sudo apt-get install cython
        This also installed (previously) the following:
            * libexpat1-dev
            * libpython-dev
            * libpython2.7-dev
            * python-dev
            * python2.7-dev
    6. Install scipy:
>       $sudo apt-get install python-scipy

        This also installed the following:
            * python-decorator
    7. Install all matplotlib dependencies:
>       $sudo apt-get build-dep python-matplotlib

    8. Install matplotlib:
>       $sudo apt-get install python-matplotlib

        This also installed the following:
            * fonts-lyx
            * python-matplotlib-data
    9. Install scikit-learn:
>       $sudo pip install scikit-learn

