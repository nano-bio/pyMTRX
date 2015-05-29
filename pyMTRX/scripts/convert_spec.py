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
from pprint import pprint

# 3rd-party modules
#sys.path.append('C:/Users/csykes/alex/Dropbox/ampPy/spm_dev/')
import pyMTRX

#==============================================================================
def main(cwd='./', sdir=None, r=True, processes=mp.cpu_count(), debug=False):
    if debug: print '*** DEBUG MODE ON ***'
    t = time.time()
    if cwd[-1] != '/':
        cwd += '/'
    files = os.listdir(cwd)
    
    if r: print 'recursive search enabled'
    print 'looking for STS files in "{}"'.format(cwd)
    # find one experiment file and then move on
    experiment_files = find_files(cwd, fext='mtrx', r=r)
    print 'Found the following .mtrx files'
    for fp in experiment_files: print 4*' ' + os.path.basename(fp)
    
    N_opened = []
    try:
        processes = int(processes)
    except ValueError:
        processes = 1
    #END try
    if processes < 1 or debug: processes = 1
    if processes == 1:
        for fp in experiment_files:
            if not isinstance(sdir, basestring): sdir = os.path.dirname(fp)
            N_opened.append( subroutine_1(fp, sdir=sdir, debug=debug) )
        # END for
    else:
        # Create worker pool and start all jobs
        worker_pool = mp.Pool(processes=processes)
        for fp in experiment_files:
            if not isinstance(sdir, basestring): sdir = os.path.dirname(fp)
            N_opened.append(
                worker_pool.apply_async( subroutine_1,
                                         args=(fp,sdir,debug)
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
def subroutine_1(ex_fp, sdir='.', debug=False):
    '''This function will receive the path to a .mtrx file and should attempt
    to convert every STS spectra in that experiment to a .txt (utf-8) file
    '''
    
    n_opened = 0
    cwd = os.path.dirname(ex_fp)
    ex = pyMTRX.Experiment(ex_fp, debug=debug)
    for fn in os.listdir(cwd):
        if fn not in ex: continue
        if not re.search(r'\.[^.]+?\(\w+\)[^.]+$', fn): continue
        if re.search(r'\(t\)', fn): continue
        if debug: print '\n{}'.format(fn)
        for crv in ex.import_spectra(os.path.join(cwd, fn)):
            parent_fn = crv.props.get('parent', '')
            if debug: print '  parent= {}'.format(parent_fn)
            try:
                mrk = ex.stslinks[fn]
                index, rep, chnl = re.search(
                    r'(\d+)_(\d+)\.(\w+)_mtrx$', parent_fn
                ).groups()
                parent_str = ''.join([
                    '{0}', '[{1:03d}-{2:02d}-{3.dir:02b}]_',
                ])
                parent_str = parent_str.format(
                    chnl, int(index), int(rep), mrk
                )
            except (AttributeError, KeyError) as err:
                parent_str = ''
            # END try
            tstr = time.strftime(
                '%Y%b%d-%H%M%S_', time.localtime(crv.props['time'])
            )
            sn = ''.join([ tstr, parent_str,
                           '{channel}[{index:03d}-{rep:02d}-{direction:02b}]',
                           '.asc'
                        ])
            sn = sn.format(**crv.props)
            pyMTRX.CurveData.save(crv, os.path.join(sdir, sn))
            if debug: print '  saved "{}"'.format(sn)
            n_opened += 1
        # END for
    # END for
    
    print 'saved {} spectra for {}'.format(n_opened, os.path.basename(ex_fp))
    return n_opened
# END subroutine_1

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