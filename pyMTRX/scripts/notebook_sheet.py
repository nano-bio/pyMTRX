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

import pdb

# 3rd-party modules
#sys.path.append('C:/Users/csykes/alex/Dropbox/ampPy/spm_dev/')
import pyMTRX
from pyMTRX.experiment import Experiment

#==============================================================================
def main( cwd='./', sdir=None, r=True, processes=mp.cpu_count(),
          single_sheet=False, debug=False
        ):
    if debug: print('*** DEBUG MODE ON ***')
    t = time.time()
    if cwd[-1] != '/':
        cwd += '/'
    files = os.listdir(cwd)
    print('looking for experiment files in "{}"'.format(cwd))
    # find one experiment file and then move on
    experiment_files = find_files(cwd, fext='mtrx', r=r)
    print('Found the following .mtrx files')
    for fp in experiment_files:
        print('    ' + os.path.basename(fp))
    
    N_opened = []
    try:
        processes = int(processes)
    except ValueError:
        processes = 1
    #END try
    if processes < 1 or debug: processes = 1
    if processes == 1:
        for fp in experiment_files:
            if not isinstance(sdir, str): sdir = os.path.dirname(fp)
            N_opened.append(
                create_experiment_log(fp, sdir=sdir, debug=debug)
            )
        # END for
    else:
        # Create worker pool and start all jobs
        worker_pool = mp.Pool(processes=processes, maxtasksperchild=12)
        print('running in multiprocess mode: {} processes'.format(processes))
        for fp in experiment_files:
            if not isinstance(sdir, str): sdir = os.path.dirname(fp)
            N_opened.append(
                worker_pool.apply_async( wrapped_create_exlog,
                                         args=(fp,sdir,debug),
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
                N += n.get()
            except Exception as err:
                print(err)
            # END try
        # END for
    # END if
    t = time.time() - t
    hours = int(t/3600)
    minutes = int((t-3600*hours)/60)
    seconds = int(t - 3600*hours - 60*minutes)
    print('Total run time: {:02d}:{:02d}:{:02d}'.format(
        hours, minutes, seconds
    ))
    print('Average processing speed: {:.0f} files/min'.format(N/(t/60)))
# END main

#==============================================================================
def wrapped_create_exlog(*args, **kwargs):
    try:
        return create_experiment_log(*args, **kwargs)
    except Exception as err:
        print('{}: {}'.format(args[0], repr(err)))
        return 0
    # END try
# END wrapped_create_exlog

def create_experiment_log(exp_fp, sdir='./', debug=False):
    cwd, exp_fn = os.path.split(exp_fp)
    cwd += '/'
    print('loading ' + exp_fn)
    ex = Experiment(cwd + exp_fn, debug=debug)
    
    # collect image files
    # (*image file must be in experiment file AND a file in the directory)
    all_files = list( set(ex.get_data_filenames()) & set(os.listdir(cwd)) )
    img_files = [fn for fn in all_files if Experiment.is_image(fn)]
    sts_files = [fn for fn in all_files if Experiment.is_point_spectrum(fn)]
    
    dname_lkup = { 0: '00 trace up',   1: '01 retrace up',
                   2: '10 trace down', 3: '11 retrace down'
                 }
    IMG_entries = []
    STS_entries = []
    for fn in sorted(img_files, key=lambda f: os.path.getctime(cwd+f)):
        if debug: print('loading "{}"'.format(fn))
        # scns = [trace_up, retrace_up, trace_down, retrace_down] 
        scns = flatten_tree( ex.import_scan(cwd + fn) )
        for i in range(len(scns)):
            scns[i].props['direction'] = dname_lkup[i]
            IMG_entries.append( make_scan_entry(scns[i]) )
            #for crv in scns[i].spectra:
            #    STS_entries.append( make_spectrum_entry(crv, debug=debug) )
        # END for
    # END for
    for fn in sts_files:
        curves = ex.import_spectra(os.path.join(cwd, fn))
        for crv in curves:
            STS_entries.append( make_spectrum_entry(crv, debug=debug) )
    # END for
    
    IMG_entries.sort(key=lambda tup: tup[0])
    STS_entries.sort(key=lambda tup: tup[0])
    N_opened = len(IMG_entries) + len(STS_entries) + 1
    
    save_name = re.sub(r'_0001\.mtrx$', '_settings.csv', exp_fn)
    f = open(os.path.join(sdir, save_name), 'w')
    columns = [ 'date/time (d)',
                'sample', 'data set',
                'index', 'rep', 'dir', 'channel',
                'x (nm)', 'y (nm)',
                'scan bias (V)', 'current setpoint (pA)',
                'loop gain (%)', 'T_raster (ms)',
                'points', 'lines',
                'line width (nm)', 'image height (nm)', '', 'angle (deg)',
                'No. STS',
                'exp comment', 'img comment',
                'file'
              ]
    f.write(','.join(columns))
    f.write('\n')
    for t, ln in IMG_entries:
        f.write(ln)
    f.close()
    
    save_name = re.sub(r'_0001\.mtrx$', '_settings_STS.csv', exp_fn)
    f = open(os.path.join(sdir, save_name), 'w')
    columns = [ 'date/time (d)',
                'sample', 'data set',
                'scan index', 'rep', 'dir', 'channel',
                'spec index', 'rep', 'dir', 'channel',
                'start voltage (V)', 'end voltage (V)',
                'scan bias (V)', 'current setpoint (pA)',
                'loop gain (%)', 'T_raster (ms)',
                'points',
                'exp comment', 'spectrum comments',
                'file'
              ]
    f.write(','.join(columns))
    f.write('\n')
    for t, ln in STS_entries:
        f.write(ln)
    f.close()
    if len(os.path.join(sdir, save_name)) > 79:
        print(cwd + '\n    ' + save_name)
    else:
        print(cwd + ' ' + save_name)
    # END if
    
    return N_opened
# END create_experiment_log

#==============================================================================
def make_scan_entry(scn):
    ls = []
    # time
    ls.append( str(scn.props['time']/86400.0 + 25569 - 4.0/24) )
    # experiment sample
    ls.append( csv_safe(scn.ex.sample) )
    ls.append( csv_safe(scn.ex.data_set) )
    # img index (scan, repetition, direction) and channel
    ls.append(
        '{index:03d},{rep:04d},{direction},{channel}'.format(**scn.props)
    )
    # scan location
    ls.append('{}'.format(scn.props['XYScanner_X_Offset'].value * 1e9))
    ls.append('{}'.format(scn.props['XYScanner_Y_Offset'].value * 1e9))
    # scan voltage
    ls.append('{}'.format(scn.props['GapVoltageControl_Voltage'].value))
    # scan current
    ls.append('{:0.1f}'.format(scn.props['Regulator_Setpoint_1'].value * 1e12))
    # scan loop gain
    ls.append('{:0.2f}'.format(scn.props['Regulator_Loop_Gain_1_I'].value))
    # scan raster time
    ls.append('{:0.3f}'.format(scn.props['XYScanner_Raster_Time'].value * 1e3))
    # scan size in points and lines
    ls.append(str(scn.props['XYScanner_Points'].value))
    ls.append(str(scn.props['XYScanner_Lines'].value))
    # scan size in physical units (nm)
    ls.append('{:0.2f}'.format(scn.props['XYScanner_Width'].value * 1e9))
    ls.append('{:0.2f}'.format(scn.props['XYScanner_Height'].value * 1e9))
    # alert flag for parameter errors
    if pyMTRX.size_change(scn):
        ls.append('*')
    else:
        ls.append('')
    # END if
    # scan angle
    ls.append('{:0.1f}'.format(scn.props['XYScanner_Angle'].value))
    # number of linked point spectra
    ls.append(str(len(scn.spectra)))
    # experiment data set, comment, scan comment, and file name
    ls.append( csv_safe(scn.ex.comment) )
    ls.append( csv_safe(scn.props['comment']) )
    ls.append( '{}\n'.format(scn.props['file']) )
    
    return (scn.props['time'], ','.join(ls))
# END make_scan_entry

#==============================================================================
def make_spectrum_entry(crv, no_warn=True, debug=False):
    # Column titles
    # time, scan,,,, spec index, spec channel, start voltage, end voltage,
    # scan voltage (V), current setpoint (pA), loop gain (%), T_raster (ms) 
    # points, file, comments
    ls = []
    # time (write time in DAYS since 1900Jan1, this is MS Excel friendly)
    ls.append( str(crv.props['time']/86400.0 + 25569 - 4.0/24) )
    # experiment sample
    ls.append( csv_safe(crv.ex.sample) )
    ls.append( csv_safe(crv.ex.data_set) )
    # parent scan index (scan, repetition, direction) and channel
    if crv.is_linked:
        ls.append(
            '{0[0]:03d},{0[1]:04d},{1},{0[2]}'.format(
                pyMTRX.file_name_values(crv.props['parent']), crv.mrk.dir
            )
        )
    else:
        ls.append(',,,')
    # END try
    # spec index (scan, repetition, direction) and channel
    ls.append(
        '{index:03d},{rep:04d},{direction},{channel}'.format(**crv.props)
    )
    # spec start, end
    ls.append('{:0.3f},{:0.3f}'.format(crv.X[0], crv.X[-1]))
    # scan bias
    ls.append('{}'.format(crv.props['GapVoltageControl_Voltage'].value))
    # scan current setpoint
    ls.append(
        '{:0.1f}'.format(crv.props['Regulator_Setpoint_1'].value * 1e12)
    )
    # scan loop gain
    ls.append('{:0.2f}'.format(crv.props['Regulator_Loop_Gain_1_I'].value))
    # spec raster time
    ls.append(
        '{:0.3f}'.format(crv.props['Spectroscopy_Raster_Time_1'].value * 1e3)
    )
    # spec number of points
    ls.append(str(len(crv)))
    # experiment data set and comment, sts file name
    ls.append( csv_safe(crv.ex.comment) )
    ls.append( csv_safe(crv.props['comment']) )
    ls.append( '{}\n'.format(crv.props['file']) )
    
    return (crv.props['time'], ','.join(ls))
# END make_spectrum_entry

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
def csv_safe(s):
    return '"' + re.sub(r'[\r\n]+', ' | ', s) + '"'
# END csv_safe

#==============================================================================
def make_hms(t):
    hours = int(t/60**2)
    minutes = int((t%60**2)/60**1)
    seconds = t%60**1/60**0
    return hours, minutes, seconds
# END make_hms

#==============================================================================
def flatten_tree(A):
    flat = []
    try:
        for a in A:
            flat.extend( flatten_tree(a) )
    except TypeError:
        return [A]
    # END try
    return flat
# END flatten_tree

#==============================================================================
if __name__ == '__main__':
    if os.name == 'nt': mp.freeze_support()
    #main()
    #quit()
    #try:
    #    main()
    #except Exception as err:
    #    exc_type, exc_value, exc_tb = sys.exc_info()
    #    bad_file, bad_line, func_name, text = traceback.extract_tb(exc_tb)[-1]
    #    print 'Error in {}'.format(bad_file)
    #    print '{} on {}: {}'.format(type(err).__name__, bad_line, err)
    #    print ''
    #finally:
    #    raw_input("press enter to exit")
    ## END try
# END if
