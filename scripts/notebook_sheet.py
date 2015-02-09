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

# 3rd-party modules
#sys.path.append('C:/Users/csykes/alex/Dropbox/ampPy/spm_dev/')
from pyMTRX.experiment import Experiment

#==============================================================================
def main(cwd='./', r=True, debug=False):
    if debug:
        print '*** DEBUG MODE ON ***'
    t = [time.time()]
    if cwd[-1] != '/':
        cwd += '/'
    print 'looking for experiment files in "{}"'.format(cwd)
    # find one experiment file and then move on
    experiment_files = find_files(cwd, fext='mtrx', r=r)
    print 'Found the following .mtrx files'
    for fp in experiment_files:
        print '    ' + os.path.basename(fp)
    
    results = []
    multi = True
    if not multi:
        for fp in experiment_files:
            results.append( create_experiment_log(fp, debug=debug) )
        # END for
    else:
        # Create worker pool and start all jobs
        worker_pool = mp.Pool(processes=mp.cpu_count())
        for fp in experiment_files:
            results.append(
                worker_pool.apply_async( create_experiment_log,
                                         args=(fp,debug)
                                       )
            )
        # END for
        worker_pool.close()
        # Wait here for all work to complete
        worker_pool.join()
    # END if
    
    t.append(time.time())
    all_img_entries = []
    all_sts_entries = []
    if not multi:
        for ex_img_entries, ex_sts_entries in results:
            all_img_entries.extend(ex_img_entries)
            all_sts_entries.extend(ex_sts_entries)
        # END for
    else:
        for resultobj in results:
            try:
                ex_img_entries, ex_sts_entries = resultobj.get()
            except:
                continue
            # END try
            all_img_entries.extend(ex_img_entries)
            all_sts_entries.extend(ex_sts_entries)
        # END for
    # END if
    all_img_entries.sort(key=lambda tup: tup[0])
    all_sts_entries.sort(key=lambda tup: tup[0])
    
    t.append(time.time())
    with open('vt-stm logbook.csv', 'w') as fstm:
        fstm.write(
            'time,sample,index,rep,dir,channel,x (nm),y (nm),scan bias (V),current setpoint (pA),loop gain (%),T_raster (ms),points,lines,line width (nm),image height (nm),,angle (deg),No. STS,data set,exp comment,img comment,file\n'
        )
        for _, ls in all_img_entries:
            fstm.write(ls)
        # END for
    # END with
    with open('vt-sts logbook.csv', 'w') as fsts:
        fsts.write(
            'time,sample,scan index,rep,dir,channel,spec index,rep,dir,channel,start voltage (V),end voltage (V),scan bias (V),current setpoint (pA),loop gain (%),T_raster (ms),points,data set,exp comment,comments,file\n'
        )
        for _, ls in all_sts_entries:
            fsts.write(ls)
        # END for
    # END with
    
    t.append(time.time())
    # t = [start, read done, sort done, write done]
    N = len(experiment_files) + len(all_img_entries) + len(all_sts_entries)
    print 'Files read: {:,d}'.format(N)
    print 'Total run time: {:02d}:{:02d}:{:06.3f}'.format(
        *make_hms(t[-1]-t[0])
    )
    t_ = t[1] - t[0]
    print 'Average import speed: {:.0f} files/min'.format(N/(t_/60))
    print 'Sort time: {:02d}:{:02d}:{:06.3f}'.format(
        *make_hms(t[3]-t[2])
    )
    print 'Write time: {:02d}:{:02d}:{:06.3f}'.format(
        *make_hms(t[2]-t[1])
    )
# END main

#==============================================================================
def create_experiment_log(exp_fp, debug=False):
    cwd, exp_fn = os.path.split(exp_fp)
    cwd += '/'
    ex = Experiment(cwd + exp_fn, debug=debug)
    if debug or True:
        print exp_fn + ' loaded'
    
    # collect image files
    # (*image file must be in experiment file AND a file in the directory)
    # img_files = [ (file_name, 1st_index, 2nd_index), ... ]
    img_files = []
    all_data = set(ex.datafile_st.keys())
    for fn in os.listdir(cwd):
        fn_mat = re.search(r'\.[A-Z0-9]+_mtrx$', fn)
        if fn_mat and fn in all_data:
            img_files.append(fn)
    # END for
    if debug:
        random.shuffle(img_files)
        img_files = img_files[:5]
    # END if
    
    #dname_lkup = { 0: '00 trace up',   1: '01 retrace up',
    #               2: '10 trace down', 3: '11 retrace down'
    #             }
    IMG_entries = []
    STS_entries = []
    for fn in sorted(img_files, key=lambda f: os.path.getctime(cwd+f)):
        if debug:
            print 'loading "{}"'.format(fn)
        # scns = [trace_up, retrace_up, trace_down, retrace_down] 
        scns = ex.import_scan(cwd + fn, calc_duration=True)
        for i in range(len(scns)):
            #scns[i].props['direction'] = dname_lkup[i]
            IMG_entries.append(
                make_scan_entry(scns[i], ex, image_check(ex, scns[i]))
            )
            STS_entries.extend(make_spectra_entries(scns[i], ex, debug=debug))
        # END for
    # END for
    #IMG_entries.sort(key=lambda tup: tup[0])
    #STS_entries.sort(key=lambda tup: tup[0])
    
    return IMG_entries, STS_entries
# END create_experiment_log

#==============================================================================
def make_scan_entry(scn, ex, no_warn=True):
    ls = []
    # time
    ls.append('{},'.format((scn.props['time'])/86400.0 + 25569 - 4.0/24))
    # experiment sample
    ls.append('{0.sample},'.format(ex))
    # img index (scan, repetition, direction) and channel
    ls.append(
        '{index:03d},{rep:04d},{direction:02b},{Channel},'.format(**scn.props)
    )
    # scan location
    ls.append('{},'.format(scn.props['XYScanner_X_Offset'] * 1e9))
    ls.append('{},'.format(scn.props['XYScanner_Y_Offset'] * 1e9))
    # scan voltage
    ls.append('{},'.format(scn.props['GapVoltageControl_Voltage']))
    # scan current
    ls.append('{:0.1f},'.format(scn.props['Regulator_Setpoint_1'] * 1e12))
    # scan loop gain
    ls.append('{:0.2f},'.format(scn.props['Regulator_Loop_Gain_1_I']))
    # scan raster time
    ls.append('{:0.3f},'.format(scn.props['XYScanner_Raster_Time'] * 1e3))
    # scan size in points and lines
    ls.append('{},'.format(scn.props['XYScanner_Points']))
    ls.append('{},'.format(scn.props['XYScanner_Lines']))
    # scan size in physical units (nm)
    ls.append('{:0.2f},'.format(scn.props['XYScanner_Width'] * 1e9))
    ls.append('{:0.2f},'.format(scn.props['XYScanner_Height'] * 1e9))
    # alert flag for parameter errors
    if no_warn:
        ls +=','
    else:
        ls.append('*,')
    # END if
    # scan angle
    ls.append('{:0.1f},'.format(scn.props['XYScanner_Angle']))
    # number of linked point spectra
    ls.append('{},'.format(len(scn.spectra)))
    # experiment data set, comment, scan comment, and file name
    ls.append(
        '{0.data_set},{0.comment},{comment},{file}\n'.format(ex, **scn.props)
    )
    
    return (scn.props['time'], ''.join(ls))
# END make_scan_entry

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
            '{index}_{rep}_{direction:b}'.format(**scn.props)
        )
    for crv in scn.spectra:
        ls = []
        # time (write time in DAYS since 1900Jan1, this is MS Excel friendly)
        ls.append(
            '{},'.format((crv.props['time'])/86400.0 + 25569 - 4.0/24)
        )
        # experiment sample
        ls.append('{},'.format(ex.sample))
        # parent scan index (scan, repetition, direction) and channel
        ls.append(
            '{index:03d},{rep:04d},{direction:02b},{Channel},'.format(
                **scn.props
            )
        )
        # spec index (scan, repetition, direction) and channel
        ls.append(
            '{index:03d},{rep:04d},{direction},{Channel},'.format(**crv.props)
        )
        # spec start, end
        ls.append('{:0.3f},{:0.3f},'.format(crv.X[0], crv.X[-1]))
        # scan bias
        ls.append('{},'.format(crv.props['GapVoltageControl_Voltage']))
        # scan current setpoint
        ls.append(
            '{:0.1f},'.format(crv.props['Regulator_Setpoint_1'] * 1e12)
        )
        # scan loop gain
        ls.append('{:0.2f},'.format(crv.props['Regulator_Loop_Gain_1_I']))
        # spec raster time
        ls.append(
            '{:0.3f},'.format(crv.props['Spectroscopy_Raster_Time_1'] * 1e3)
        )
        # spec number of points
        ls.append('{},'.format(len(crv)))
        # experiment data set and comment, sts file name
        ls.append('{0.data_set},{0.comment},{1.sourcefile}\n'.format(ex, crv))
        
        out.append( (crv.props['time'], ''.join(ls)) )
    # END for
    return out
# END make_spectra_entries

#==============================================================================
def image_check(ex, scn):
    all_clear = True
    t_0 = scn.props['time'] - scn.props['duration']
    t_f = scn.props['time']
    
    # a is the index of the last parameter change before the scan starts
    # b is the index of the first parameter change after the scan ends
    a = 0
    b = len(ex.st_hist)-1
    while b-a > 1:
        i = (b+a) / 2
        if t_0 < ex.st_hist[i][0]:
            b = i
        else:
            a = i
        # END if
    # END while
    while ex.st_hist[b][0] < t_f:
        b += 1
        if b == len(ex.st_hist):
            break
        # END if
    # END while
    for i in range(a+1,b):
        if re.search(r'Width|Height', ex.st_hist[i][1].name):
            all_clear = False
            break
        # END if
    # END for
    
    return all_clear
# END image_check

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