#!/usr/bin/python
# -*- encoding: UTF-8 -*-
'''Spectroscopy Tests
    
    List of functions:
        main
'''

# built-in modules
import sys
sys.path.insert(0, '../')
import os
import time
import re
from pprint import pformat

# third-party modules
import pyMTRX
import matplotlib.pyplot as plt

#==============================================================================
def main(*args):
    tdir = './test_data/'
    sdir = '../test_results/'
    if not os.path.exists(sdir): os.mkdir(sdir)
    print('saving to {}'.format(sdir))
    
    print('found pyMTRX in... {}'.format(pyMTRX.__file__))
    
    print('')
    print('*** BEGIN TESTS FOR pyMTRX.Experiment CLASS ***')
    print('')
    
    #ex = pyMTRX.Experiment('test_data/2014Oct09-090049_0001.mtrx')
    #files = [ '2014Oct09-090049--438_1.I(V)_mtrx',
    #          '2014Oct09-090049--439_1.I(V)_mtrx',
    #          '2014Oct09-090049--440_1.I(V)_mtrx',
    #          '2014Oct09-090049--441_1.I(V)_mtrx',
    #          '2014Oct09-090049--442_1.I(V)_mtrx',
    #          '2014Oct09-090049--1_122.Z_mtrx'
    #        ]
    #for fn in files:
    #    scn_st = ex.get_state(fn)
    #    print 'Settings for "{}"'.format(fn)
    #    print '    V= {0.value:0.3f} {0.unit}'.format(
    #        scn_st['GapVoltageControl_Voltage']
    #    )
    #    print '    I= {0.value:0.2e} {0.unit}'.format(
    #        scn_st['Regulator_Setpoint_1']
    #    )
    ## END for
    
    print('')
    print('Testing scripts...')
    print('')
    print('convert_all_pntspec_to_txt.py')
    print('-----------------------------')
    pyMTRX.convert_spec('test_data/', sdir=sdir)
    
    print('')
    print('notebook_sheet.py')
    print('-----------------')
    pyMTRX.notebook_sheet('test_data/', sdir=sdir)
    
    print('')
    print('notebook_slides.py')
    print('------------------')
    pyMTRX.notebook_slides('test_data/', sdir=sdir)
    
    #print ''
    #print '    PngMaker'
    #scans = PngMaker.main(save_dir=sdir)
    #print 'len(main.scans) = {}'.format(len(scans))
    #with open(sdir+'Scan.__dict__.txt', 'w') as f:
    #    f.write( pformat(scans[0].__dict__) )
    #for scn in scans:
    #    if scn.spectra:
    #        break
    #with open(sdir+'pyMTRX.CurveData.__dict__.txt', 'w') as f:
    #    f.write( pformat(scn.spectra[0].__dict__) )
    #
    #scans = PngMaker.main(save_dir=sdir)
    #print 'len(main.scans) = {}'.format(len(scans))
    #with open(sdir+'Scan.__dict__.txt', 'w') as f:
    #    f.write( pformat(scans[0].__dict__) )
    #for scn in scans:
    #    if scn.spectra:
    #        break
    #with open(sdir+'pyMTRX.CurveData.__dict__.txt', 'w') as f:
    #    f.write( pformat(scn.spectra[0].__dict__) )
    
    print('')
    print('*** BEGIN TESTS FOR pyMTRX.CurveData CLASS ***')
    print('')
    
    print('running arithmatic tests...')
    A = pyMTRX.CurveData([1.0,2.0,3.0], [1.0,4.0,9.0], x_units='s', y_units='m')
    B = pyMTRX.CurveData([1.0,2.0,3.0], [0.0,5.0,0.0], x_units='s', y_units='m')
    C = pyMTRX.CurveData(
        [1.5,2.5,3.5], [1.5**2,2.5**2,3.5**2], x_units='s', y_units='m'
        )
    print('A = '+str(A))
    print(A.sparkstr((12,12)))
    print('B = '+str(B))
    print(B.sparkstr((12,12)))
    print('C = '+str(C))
    print(C.sparkstr((12,12)))
    print('A + B = '+str(A+B))
    try:
        print('A + C = {}'.format( A + C ))
    except Exception as err:
        print(repr(err))
    # END try
    print('A - B = '+str(A-B))
    print('A * B = '+str(A*B))
    print('B / A = '+str(B/A))
    
    print('testing iteration...')
    for xy in A: print(xy)
    
    print('testing comparisons...')
    print('A == B is ' + str(A==B))
    print('A != B is ' + str(A!=B))
    print('A == A is ' + str(A==A))
    print('A == C is ' + str(A==C))
    
    print('testing call...')
    print('A(1.5) = {0:0.3f}'.format(A(1.5)))
    
    print('testing other methods...')
    print('A.units() = ' + str(A.units))
    print('')
    
    fname = (
        tdir +
        'Aux2(V) (STS_LOCATION-176,270;8.66667e-009,4e-008) ' +
        'Forward Fri Jun 21 14.13.28 2013 [51-1]  ' +
        'STM_AtomManipulation STM.asc'
        )
    
    #print 'trying to import a spec file with forward and backward data'
    #crv_f, crv_r = pyMTRX.CurveData.import_file(fname)
    #plt.plot(crv_f.X, crv_f.Y, 'b', crv_r.X, crv_r.Y, 'r')
    #plt.title('file: '+crv_f.sourcefile)
    #plt.xlabel('Gap Bias ('+crv_f.x_units+')')
    #plt.ylabel('Tip Retraction ('+crv_f.y_units+')')
    #plt.savefig(sdir+'import rr test fig.png')
    #plt.close()
    #print '  saved: ' + sdir + 'import rr test fig.png'
    #print ''
    
    #print 'trying to differentiate the curves'
    #dcrv_f = pyMTRX.CurveData.deriv_sg(crv_f, 0.5, 2, 1)
    #dcrv_r = pyMTRX.CurveData.deriv_sg(crv_r, 0.5, 2, 1)
    #plt.plot(dcrv_f.X, dcrv_f.Y, 'b', dcrv_r.X, dcrv_r.Y, 'r')
    #cdcrv_f = pyMTRX.CurveData.deriv_cdiff(crv_f)
    #plt.plot(cdcrv_f.X, cdcrv_f.Y, 'gray')
    #plt.title('file: '+crv_f.sourcefile)
    #plt.xlabel('Gap Bias ('+dcrv_f.x_units+')')
    #plt.ylabel('Tip Retraction Rate ('+dcrv_f.y_units+')')
    #plt.savefig(sdir+'deriv test fig.png')
    #plt.close()
    #print '  saved: ' + sdir + 'deriv test fig.png'
    #print ''
    
    #print 'near-neighbor smoothing of the central difference'
    #nncdcrv_f = pyMTRX.CurveData.nn_smooth(cdcrv_f, 5)
    #plt.plot(cdcrv_f.X, cdcrv_f.Y, 'gray')
    #plt.plot(nncdcrv_f.X, nncdcrv_f.Y, 'green')
    #plt.savefig(sdir+'nnsmooth and cdiff test fig.png')
    #plt.close()
    #print '  saved: ' + sdir + 'nnsmooth and cdiff test fig.png'
    #print ''
    
    #print 'testing .spec.asc importing...'
    #fname = tdir+'20130605-1030-11_01_td-mol.miv.spec.asc'
    #mcrv = pyMTRX.CurveDataError.import_file(fname)
    #plt.plot(mcrv.X, mcrv.Y)
    #plt.plot(mcrv.X, mcrv.Y+3*mcrv.eY, 'gray')
    #plt.plot(mcrv.X, mcrv.Y-3*mcrv.eY, 'gray')
    #plt.title('file: '+mcrv.sourcefile)
    #plt.xlabel('Gap Bias ('+mcrv.x_units+')')
    #plt.ylabel('Tip Retraction ('+mcrv.y_units+')')
    #plt.savefig(sdir+'import curve error test fig.png')
    #plt.close()
    #print '  saved: ' + sdir + 'import curve error test fig.png'
    #print ''
# END main

#==============================================================================
class PngMaker(object):
    t_0 = 0.0
    t_1 = 0.0
    t_all = 0.0
    n_all = 0
    
    @classmethod
    def main(cls, cwd='./', save_dir=None, top=True):
        if save_dir is None: save_dir = cwd
        cls.t_all = time.time()
        if cwd[-1] != '/': cwd += '/'
        files = sorted(
            os.listdir(cwd), key=lambda f: os.path.getmtime(cwd+f),
            reverse=True
        )
        # find one experiment file and then move on
        experiement_files = []
        out_scans = []
        for fn in files:
            if re.search(r'\.mtrx$', fn):
                experiement_files.append((cwd+fn, save_dir))
            elif os.path.isdir(cwd+fn):
                out_scans.extend(
                    cls.main(cwd + fn + '/', save_dir=save_dir, top=False)
                )
                print('len(PngMaker.main.out_scans) = {}'.format(len(out_scans)))
            # END if
        # END for
        for tup in experiement_files:
            print('found "{}"'.format(tup[0]))
            out_scans.extend( cls.submain(*tup) )
            print('len(PngMaker.main.out_scans) = {}'.format(len(out_scans)))
        # END for
        
        if top:
            print(cls.t_0)
            print(cls.t_1)
            print('t_exp:t_other = {:0.1f}'.format(cls.t_0/cls.t_1))
            cls.t_all = time.time() - cls.t_all
            print('total processing time: {:0.2f} s for {:} images'.format(
                cls.t_all, cls.n_all
            ))
            print('                       {:0.1f} img/min'.format(
                float(cls.n_all) / cls.t_all / 60.0
            ))
        # END if
        
        return out_scans
    # END main
    
    @classmethod
    def submain(cls, exp_fp, save_dir):
        cwd, exp_fn = os.path.split(exp_fp)
        cwd += '/'
        ex = pyMTRX.Experiment(exp_fp, debug=True)
        exp_name = re.search(r'^.+?(?=_\d{4}.mtrx$)', exp_fn).group(0)
        print('"{}" loaded'.format(exp_fn))
        
        # collect scan files
        scn_files = []
        for fn in os.listdir(cwd):
            if fn in ex and not pyMTRX.Experiment.is_point_spectrum(fn):
                scn_files.append(fn)
            # END if
        # END for
        scn_files.sort(key=lambda f: os.path.getmtime(cwd+f))
        print('{} scans found in "{}"'.format(len(scn_files), cwd))
        
        out_scans = []
        for fn in scn_files:
            # scns = [trace_up, retrace_up, trace_down, retrace_down]
            cls.t_0 -= time.time()
            print('importing "{}"...'.format(fn))
            scans = ex.import_scan(cwd + fn)
            cls.n_all += 1
            cls.t_0 += time.time()
            for scn in scans:
                cls.t_1 -= time.time()
                scn.linewise_level(1)
                save_name = '{:}--{:03d}_{:03d}_{:02b}.png'.format(
                    exp_name,
                    scn.props['index'], scn.props['rep'],
                    scn.props['direction']
                )
                try:
                    scn.save_png(save_dir + save_name)
                    print('saved "{}"'.format(save_name))
                except Exception as err:
                    print('{}: skipping "{}"'.format(repr(err), fn))
                # END try
                cls.t_1 += time.time()
            # END for
            out_scans.extend(scans)
        # END for
        
        return out_scans
    # END submain
# END PngMaker

#==============================================================================
if __name__ == '__main__': main(*sys.argv[1:])