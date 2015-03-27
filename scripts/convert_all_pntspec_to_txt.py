#!/usr/bin/python
# -*- encoding: UTF-8 -*-
'''MATRIX Log File Maker
    Version: 2
    
    This script will create a csv file that will be a table of settings for all
    STM data recorded from the Omicron MATRIX software.
    
    List of classes: -none-
    List of functions:
        main
'''

# built-in modules
import sys
import traceback
import os
import os.path
import re
import random
import time
import multiprocessing as mp

import pdb

# 3rd-party modules
#sys.path.append('C:/Users/csykes/alex/Dropbox/ampPy/spm_dev/')
from pyMTRX.experiment import Experiment

#==============================================================================
def main(cwd='./', r=True, processes=mp.cpu_count(), debug=False):
    if debug: print '*** DEBUG MODE ON ***'
    t = time.time()
    if cwd[-1] != '/':
        cwd += '/'
    files = os.listdir(cwd)
    
    # Get list of files...
    
    print 'looking for experiment files in "{}"'.format(cwd)
    # find one experiment file and then move on
    experiment_files = find_files(cwd, fext='mtrx', r=r)
    print 'Found the following .mtrx files'
    for fp in experiment_files:
        print '    ' + os.path.basename(fp)
    
    N_opened = []
    try:
        processes = int(processes)
    except ValueError:
        processes = 1
    #END try
    if processes < 1 or debug: processes = 1
    if processes == 1:
        for fp in experiment_files:
            N_opened.append( create_experiment_log(fp, debug=debug) )
        # END for
    else:
        # Create worker pool and start all jobs
        worker_pool = mp.Pool(processes=processes)
        for fp in experiment_files:
            N_opened.append(
                worker_pool.apply_async( create_experiment_log,
                                         args=(fp,debug)
                                       )
            )
        # END for
        worker_pool.close()
        # Wait here for all work to complete
        worker_pool.join()
    # END if
    
    N = 0
    if processes == 1:
        for n in N_opened: N += n
    else:
        for n in N_opened:
            try:
                n.get()
            except:
                continue
            # END try
            N += n.get()
        # END for
    # END if
    t = time.time() - t
    hours = int(t/3600)
    minutes = int((t-3600*hours)/60)
    seconds = int(t - 3600*hours - 60*minutes)
    print 'Total run time: {:02d}:{:02d}:{:02d}'.format(
        hours, minutes, seconds
    )
    print 'Average processing speed: {:.0f} files/min'.format(N/(t/60))
# END main

#==============================================================================
def make_spectra_entries(scn, ex, no_warn=True, debug=False):
    # Column titles
    # time, scan,,,, spec index, spec channel, start voltage, end voltage,
    # scan voltage (V), current setpoint (pA), loop gain (%), T_raster (ms) 
    # points, file, comments
    out = []
    if debug and len(scn.spectra) > 0:
        print (
            '{0:>3d} spectra in '.format(len(scn.spectra)) +
            '{index}_{rep}_{direction}'.format(**scn.props)
        )
    for crv in scn.spectra:
        ls = []
        # time (write time in DAYS since 1900Jan1, this is MS Excel friendly)
        ls.append( str(crv.props['time']/86400.0 + 25569 - 4.0/24) )
        # experiment sample
        ls.append('{0.sample},{0.data_set}'.format(ex))
        # parent scan index (scan, repetition, direction) and channel
        ls.append(
            '{index:03d},{rep:04d},{direction},{channel}'.format(
                **scn.props
            )
        )
        # spec index (scan, repetition, direction) and channel
        ls.append(
            '{index:03d},{rep:04d},{direction},{channel}'.format(**crv.props)
        )
        # spec start, end
        ls.append('{:0.3f},{:0.3f}'.format(crv.X[0], crv.X[-1]))
        # scan bias
        ls.append('{}'.format(crv.props['GapVoltageControl_Voltage']))
        # scan current setpoint
        ls.append(
            '{:0.1f}'.format(crv.props['Regulator_Setpoint_1'] * 1e12)
        )
        # scan loop gain
        ls.append('{:0.2f}'.format(crv.props['Regulator_Loop_Gain_1_I']))
        # spec raster time
        ls.append(
            '{:0.3f}'.format(crv.props['Spectroscopy_Raster_Time_1'] * 1e3)
        )
        # spec number of points
        ls.append(str(len(crv)))
        # experiment data set and comment, sts file name
        ls.append(
            '{0.comment},{1[comment]},{1[file]}\n'.format(ex, crv.props)
        )
        
        out.append( (crv.props['time'], ','.join(ls)) )
    # END for
    return out
# END make_spectra_entries

#==============================================================================
def find_files(cwd='./', fext='[^.]+', r=True):
    '''Find _mtrx files (Breath-first search)
    
    Args:
        cwd (str): current working directory
        fext (str): pattern used to match the file extensions
        r (bool): flag for recursive search
    Returns:
        (list) ['./file.ext', './file.ext', './file.ext', ...]
    '''
    
    if cwd[-1] != '/':
        cwd += '/'
    out_files = []
    work_queue = [cwd+fn for fn in os.listdir(cwd)]
    # BFS for I(t)_mtrx files
    while work_queue:
        fpath = work_queue.pop(0)
        if os.path.isdir(fpath) and r:
            work_queue.extend( [fpath+'/'+fn for fn in os.listdir(fpath)] )
        elif re.search(r'\.'+fext+'$', fpath):
            out_files.append(fpath)
        # END if
    # END while
    return out_files
# END find files

#==============================================================================
def make_hms(t):
    hours = int(t/60**2)
    minutes = int((t%60**2)/60**1)
    seconds = t%60**1/60**0
    return hours, minutes, seconds
# END make_hms

#==============================================================================
if __name__ == '__main__':
    main()
    quit()
    try:
        main()
    except Exception as err:
        exc_type, exc_value, exc_tb = sys.exc_info()
        bad_file, bad_line, func_name, text = traceback.extract_tb(exc_tb)[-1]
        print 'Error in {}'.format(bad_file)
        print '{} on {}: {}'.format(type(err).__name__, bad_line, err)
        print ''
    finally:
        raw_input("press enter to exit")
    # END try
# END if