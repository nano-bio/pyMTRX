# -*- encoding: UTF-8 -*-
'''Omicron MATRIX Results Files Reading Module
    
    List of classes:
        Experiment
        MatrixProperty
        ByteBuffer
        TransferFunction
    List of functions:
        s2x
'''

# The "Colin" bug: if the experimenter changes the scan settings right before
#                  taking a spectra and then changes them back, the settings
#                  saved in the CurveData of the spectra will be the wrong
#                  settings.  The scan settings state at the END of the scan
#                  are what is attached to the point spectra.

# built-in modules
import os
import struct
import re
import time
from StringIO import StringIO
from pprint import pprint, pformat
import pdb

# third-party modules
import numpy as np
from scan import ScanData
from curves import CurveData

#==============================================================================
class Experiment(object):
    '''MATRIX Experiment Class
    
    When opening MATRIX SPM data the end file (*.mtrx) must first be read and
    parsed into an Experiment object.  This object can then be used to get
    information on setting and open data files (*.Z_mtrx etc.)
    
    Instantiation Args:
        file_path (str): path and file name of *.mtrx experiment file
        debug (bool): When True a file describing how the experiment file is
                      interpreted will be written
    Instance Attributes:
        fp (str): the file path used for instantiation
        datafile_st (dict): settings state dictionaries keyed by data file
                            name
        stslinks (dict): image-spectra linkage information
            stslinks[spectra_fname] = (mrk, fname)
            stslinks[scn_fname] = [(mrk, spec_fname), (mrk, spec_fname), ...]
            mrk = (ii, i, d, locstr, chnl_hash)
        unlinked_spectra (list)
        axch (dict): pseudo-graph structure describing data axes linkage
            axch[h] = ("ChannelData...", hash_for_dependent_ax)
            
            axch[h_dependent_ax] = ( chnl_name, chnl_unit, TransferFunction,
                                     h_independent_fast_ax
                                   )
            example: ("I", "A", tf, 600 ...)
            
            axch[h_independent_fast_ax] = ( device_name,
                                            device_looping_pattern, ppl,
                                            h_independent_slow_ax
                                          )
            example: ("Default::XYScanner::X", "triangular", 600, ...)
            
            axch[h_independent_slow_ax] = ( device_name,
                                            device_looping_pattern, ppl, 0
                                          )
            example: ("Default::XYScanner::Y", "triangular", 600, 0)
        log (StingIO): string buffer for constructing the debugging file
                       on-the-fly
    Example:
        TODO fill this in
    '''
    
    def __init__(self, file_path, debug=False):
        self.fp = file_path
        # Initial settings state dictionary
        self.init_st = {}
        self.st_hist = []
        # Settings state to be kept current with the timeline
        self._curr_st = {}
        self.datafile_st = {}
        self.stslinks = {}
        self.sample = ''
        self.data_set = ''
        self.comment = ''
        self.img_comments = {}
        self.last_sts_mark = None
        self.unlinked_spectra = []
        self.free_spectra = []
        self.axch = {}
        self.bref_mark_cache = []
        
        # for debugging
        self.debug = debug
        self.log = StringIO()
        
        # ONMATRIX0101
        with open(file_path, 'rb') as f:
            magicword = f.read(12)
            if not re.search('ONTMATRX0101', magicword):
                f.close()
                raise ValueError(
                    'Incorrect file type, "{}"'.format(magicword)
                )
            # END if
            
            while self._init_readblock(f):
                pass
        # END with
        
        # Parse all of the MARKs now that all of the channels/axes have been
        # registered
        
        # when debugging write some variables directly to the file
        if debug:
            timestamp = time.strftime(' %Y%m%d')
            exp_date = re.search(r'\d{4}\w{3}\d\d-\d{6}', file_path).group(0)
            log_sname = 'debug log {0} for {1}.txt'.format( timestamp,
                                                            exp_date
                                                          )
            f = open(log_sname, 'w')
            # print out the axis hierarchy
            f.write('self.axch = \n')
            for k in sorted(self.axch.keys()):
                f.write('    {0} (x{0:0>16x}):\n'.format(k))
                #f.write('        {}').format(type(self.axch[k]).__name__)
                #i = 0
                obj_str = pformat(self.axch[k].__dict__, 2, 79-8)
                obj_str = re.sub(r'^', '        ', obj_str, flags=re.M)
                #f.write(8*' ')
                f.write(obj_str)
                f.write('\n')
                #for x in self.axch[k]:
                #    f.write(8*' ' + '{:02d} ({}): {}\n'.format(
                #        i, type(x).__name__, str(x))
                #    )
                #    i += 1
            # END for
            f.write('\n')
            # print out the STS linkage dict
            try:
                f.write('self.stslinks = \n')
                skeys = sorted(
                    self.stslinks.keys(),
                    key=lambda s: re.sub(r'(^.*?)(\..*$)', r'\2\1', s)
                )
                for k in skeys:
                    if re.search(r'\.[ZI]_mtrx$', k):
                        f.write('    ')
                        kdisp = re.search(r'--.*$', k).group(0)
                        v = self.stslinks[k]
                        f.write(str(kdisp) + ': ')
                        for x in v:
                            specindex = re.search(r'--([\d_]+)\.', x[-1]).group(1)
                            f.write(specindex + ', ')
                        f.write('\n')
                    else:
                        f.write('    ')
                        kdisp = re.search(r'--.*$', k).group(0)
                        v = self.stslinks[k]
                        f.write(str(kdisp) + ': ' + str(v[0][:3]) + ', ')
                        scnindex = re.search(r'--.*$', v[1]).group(0)
                        f.write(scnindex + '\n')
            except Exception:
                pass
            # END try
            f.write(self.log.getvalue())
            f.close()
        # END if
        self.log.close()
    # END __init__
    
    def _init_readblock(self, f):
        '''__init__ subroutine for reading blocks
        
        The following blocks will be ignored:
            META: file meta data
            EXPD: some unknown experiement files
            INCI: is 8B of empty space, there positions don't seem to
              correspond to STS events
            PROC: is info about plug-ins (e.g. CurveAverager or Despiker)
            VIEW: window view settings
            CCSY: not fully understood, contains some information on
              transfer function and possible some spectra-scan linkage info
            FSEQ: unknown block
        '''
        
        name = f.read(4)
        name = name[::-1]
        if not name:
            return False
        bklen = struct.unpack('<I', f.read(4))[0]
        t = struct.unpack('<Q', f.read(8))[0]
        self._t_bk = t
        try:
            timestr = time.ctime(t)
        except ValueError:
            # the INCI block has no timestamp
            timestr = ''
        # END try
        bkbuff = MatrixBuffer(f, bklen)
        
        # Subroutines to parse the data in the different types of blocks
        if re.search(r'EEPA', name):
            self._init_read_EEPA(bkbuff)
        elif re.search(r'PMOD', name):
            self.log.write(
                '{} {} '.format(
                    time.strftime('%H:%M:%S', time.localtime(t)), name, bklen
                )
            )
            self._init_read_PMOD(bkbuff)
        elif re.search(r'BREF', name):
            self.log.write(
                '{} {} '.format(
                    time.strftime('%H:%M:%S', time.localtime(t)), name, bklen
                )
            )
            self._init_read_BREF(bkbuff)
        elif re.search(r'MARK', name):
            self.log.write(
                '{} {} '.format(
                    time.strftime('%H:%M:%S', time.localtime(t)), name
                )
            )
            self._init_read_MARK(bkbuff)
        elif re.search(r'CCSY', name):
            self.log.write(
                '{} {} \n'.format(
                    time.strftime('%H:%M:%S', time.localtime(t)), name
                )
            )
            self._init_read_CCSY(bkbuff)
        # END if
        bkbuff.advance()
        if len(bkbuff)>0:
            print '{} {}, {} left'.format(name, bklen, len(bkbuff))
            raise RuntimeError('buffer and file object out of sync')
        # END if
        return True
    # END _init_readblock
    
    def _init_read_EEPA(self, buff):
        '''The EEPA block contains the initial parameter settings.
        This subroutine will parse the block into the _init_st dict'''
        
        #skip empty space
        buff.next(4)
        for _ in range(buff.next_uint()):
            chnl = buff.next_mtrxstr()
            for _ in range(buff.next_uint()):
                param = buff.next_mtrxparam(chnl)
                self.init_st[param.name] = param
            # END for
        # END for
        
        self._curr_st = dict(self.init_st)
    # END _init_read_EEPA
    
    def _init_read_PMOD(self, buff):
        '''A PMOD block contains a new setting for a single parameter.
        This subroutine will parse the block into current state dict.'''
        
        #skip empty space
        buff.next(4)
        
        chnl = buff.next_mtrxstr()
        param = buff.next_mtrxparam(chnl)
        self.st_hist.append( (self._t_bk, param) )
        self._curr_st[param.name] = param
        self.log.write(4*' ' + str(param) + '\n')
    # END _init_read_PMOD
    
    def _init_read_BREF(self, buff):
        '''A BREF ("Bricklet REFerence") block will mark a data file saving
        event.  This subroutine will parse the block ...'''
        #skip empty space
        buff.next(4)
        fname = buff.next_mtrxstr()
        # freeze a copy of the current settings and register it
        self.datafile_st[fname] = dict(self._curr_st)
        
        # manage point-spectra linkage
        img_mat = re.search(r'\.([^()]+)_mtrx$', fname)
        # this is to make sure spectra such as I(t) are not incorrectly treated
        # as linked point spectra
        pointsts_mat = re.search(r'\..*?\(V\)_mtrx$', fname)
        if img_mat:
            # file is scan data
            img_chnl_name = img_mat.group(1)
            # NOTE: unable to parse which channel window the point-STS was
            #       taken in, so all spectra will be attached to Z_mtrx files
            self.unlinked_spectra.append(None)
            while self.unlinked_spectra[0] is not None:
                spectra_fname, mrk = self.unlinked_spectra.pop(0)
                try:
                    sts_parent_ax = self.axch[mrk[4]].depn_ax
                except KeyError as err:
                    self.unlinked_spectra.append( (spectra_fname, mrk) )
                    continue
                # END try
                if mrk is None:
                    # this is a "free-range" spectra
                    # e.g. an I(t) spectra
                    self.free_spectra.append(spectra_fname)
                    continue
                elif sts_parent_ax.name != img_chnl_name:
                    # this spectra was clicked in a different channel window
                    # e.g. user clicked in I window instead of Z
                    self.unlinked_spectra.append( (spectra_fname, mrk) )
                # END if
                # update the scan --> spec lookup
                if fname not in self.stslinks:
                    self.stslinks[fname] = [ (mrk, spectra_fname) ]
                else:
                    self.stslinks[fname].append( (mrk, spectra_fname) )
                # END if
                # make a link for spec --> scan lookup
                i, ii = re.search(r'--(\d+)_(\d+)\.[^.]+$', fname).groups()
                try:
                    # This replaces the spectra's image indices so that they
                    # are correct.
                    # (NOTE: this makes the indices IMPLICIT data)
                    mrk = ( int(i), int(ii), mrk[2], mrk[3],
                            sts_parent_ax.name
                          )
                except TypeError as err:
                    print 'i ='
                    pprint(i)
                    print 'ii ='
                    pprint(ii)
                    print 'mark {} ='.format(repr(type(mrk)))
                    pprint(mrk)
                    print 'self.unlinked_spectra ='
                    pprint(self.unlinked_spectra)
                    print 'self.stslinks[fname] ='
                    pprint(self.stslinks[fname])
                    raise err
                self.stslinks[spectra_fname] = (mrk, fname)
            # END while
            self.unlinked_spectra.pop(0)
            
            if fname not in self.img_comments:
                self.img_comments[fname] = []
            if img_chnl_name in self.img_comments:
                self.img_comments[img_chnl_name].append(None)
                while self.img_comments[img_chnl_name][0] is not None:
                    img_chnl, d, cmnt = self.img_comments[img_chnl_name].pop(0)
                    self.img_comments[fname].append((d, cmnt))
                # END while
                self.img_comments[img_chnl_name].pop(0)
            # END if
        elif pointsts_mat:
            # file is for spectroscopy data
            self.unlinked_spectra.append( (fname, self.last_sts_mark) )
            self.last_sts_mark = None
        # END if
        
        self.log.write(4*' ' + fname + '\n')
    # END _init_read_BREF
    
    def _init_read_MARK(self, buff):
        '''A MARK blocks are used for marking the time and position of a
        spectroscopy event, as well as the user's experimental comments.
        Example MARK block strings: 
            "MTRX$STS_LOCATION-129,102;-3.5e-009,-8e-009%%400440043-8-1-0%%"
            "MTRX$CREATION_COMMENT-"
        
        TODO: figure out what "PROFILE_LOCATIONS" represents
              "MTRX$PROFILE_LOCATIONS-135,132;83,170;-5e-010,-6e-010;-2.23333e-009,6.66667e-010%%b00440043-43-3-2%%"
              voltage pulse tool where you set V & t on click?
        TODO: add recognition of rating changes
        '''
        
        markstr = buff.next_mtrxstr()
        self.log.write('    ' + markstr + '\n')
        if re.search(r'^MTRX\$STS_LOCATION', markstr):
            # Example:
            # MTRX$STS_LOCATION-192,94;7e-009,-9.33333e-009%%7800440043-1-4-0%%
            # locstr: string containing physical and pixel coordinates of the
            #  spectroscopy location
            # img_chnl_hash
            # _unknown: unknown, first suspected it to be run number, but
            #     that is either not correct or, more likely, it is something
            #     else
            # TODO: figure out what ii is
            # ii: MATRIX scan number index for the parent scan
            # d: direction of the parent scan where the spectra was taken
            locstr, img_chnl_hash, _unknown, ii, d = re.search(
                r'^MTRX\$STS_LOCATION-(.+?)%%(\w+)-(\d+)-(\d+)-(\d+)', markstr
            ).groups()
            img_chnl_hash = int(img_chnl_hash, 16)
            self.last_sts_mark = ( int(ii), int(_unknown), int(d),
                                    locstr, img_chnl_hash 
                                 )
        elif re.search(r'MTRX\$SAMPLE_NAME', markstr):
            self.sample = re.search(r'-(.*)$', markstr).group(1)
        elif re.search(r'MTRX\$DATA_SET_NAME', markstr):
            self.data_set = re.search(r'-(.*)$', markstr).group(1)
        elif re.search(r'MTRX\$CREATION_COMMENT', markstr):
            try:
                self.comment = re.search(r'(?<=COMMENT-).*', markstr).group(0)
            except AttributeError:
                print 'parse warning on "{}"'.format(markstr)
                self.comment = markstr
            # END try
        elif re.search(r'MTRX\$IMAGE_COMMENT', markstr):
            # Example:
            # "MTRX$IMAGE_COMMENT-Z.-493925695555-2-0-2%this is only a test"
            # "MTRX$IMAGE_COMMENT-I(V).-47249096771-1-0--1%added -2.6 V offset manually"
            # NOTE: ii not correctly assigned
            # NOTE: d may be correct
            print '"{}"'.format(markstr)
            chnl_name, chnl_key, _unknown, ii, d, comment = re.search(
                r'^MTRX\$IMAGE_COMMENT-(.+?)\.-(\w+)-(\d+)-(\d+)-+(\d+)%(.*)',
                markstr
            ).groups()
            d = int(d)
            chnl_key = int(chnl_key) #Used to be base 16
            try:
                depn_ax = self.axch[chnl_key].depn_ax
                self.log.write(
                    '    {} --> {}\n'.format( chnl_key, 
                                              self.axch[chnl_key].descrip
                                            )
                )
                chnl_name = depn_ax.name
            except KeyError as err:
                # TODO remove this quick fix with a real fix
                print '{} while trying to attach image comment'.format(
                    repr(err)
                )
                chnl_name = 'Z'
                return
                #print 'working file: "{}"'.format(self.fp)
                #raise err
            # END try
            if chnl_name in self.img_comments:
                self.img_comments[chnl_name].append( (chnl_name, d, comment) )
            else:
                self.img_comments[depn_ax.name] = [(chnl_name, d, comment),]
            # END if
        # END if
    # END _init_read_MARK
    
    def _init_read_CCSY(self, buff):
        '''The CCSY block contains transfer function information.
        This subroutine will parse the block into the state dictionaries
        '''
        
        #skip empty space
        buff.next(4)
        while buff:
            subbuff, subname = buff.next_bk()
            #subname = buff.next(4)[::-1]
            self.log.write(4*' ' + subname + '\n')
            #subblk_len = buff.next_uint()
            #subbuff = ByteBuffer( buff.next(subblk_len) )
            if subname == 'DICT':
                # skip opening space
                subbuff.next(8)
                # ***It is assumed that the axis hierarchy is listed from
                #    the bottom up.***
                # Device and scan pattern dictionary
                # 1st sub-dictionary
                # Independent Axes information
                # [ axis_key, following_axis_key,
                #   qualified_name, looping_pattern
                # ]
                dict_len = subbuff.next_uint()
                for i in range(dict_len):
                    axis_key = struct.unpack('<Q', subbuff.next(8))[0]
                    following_axis_key = struct.unpack(
                        '<Q', subbuff.next(8)
                    )[0]
                    qualified_name = subbuff.next_mtrxstr()
                    # Next string is the looping pattern.
                    # 'linear' ==> not mirrored
                    # 'triangular' ==> mirrored
                    mirrored = False
                    if subbuff.next_mtrxstr() == 'triangular':
                        mirrored = True
                    try:
                        following_ax = self.axch[following_axis_key]
                    except KeyError:
                        if following_axis_key != 0:
                            raise KeyError(
                                'link to following axis declared before' +
                                'following axis was defined'
                            )
                        else:
                            following_ax = None
                        # END if
                    # END try
                    try:
                        self.axch[axis_key] = IndependentAxis(
                            axis_key, qualified_name, mirrored,
                            next_ax=following_ax
                        )
                    except ValueError as err:
                        raise ValueError(
                            '{}, {}, {}, {}\n'.format(
                                axis_key, following_axis_key,
                                qualified_name, mirrored
                            )
                        )
                    # END try
                    self.log.write(8*' ')
                    self.log.write(
                        '{}, {}, {}, {}\n'.format(
                            axis_key, following_axis_key,
                            qualified_name, mirrored
                        )
                    )
                # END for
                self.log.write(8*' '  + '---\n')
                
                # 2nd sub-dictionary
                # Dependent Axes information
                # [ axis_key, indp_axis_key, name, unit ]
                dict_len = subbuff.next_uint()
                for i in range(dict_len):
                    axis_key = struct.unpack('<Q', subbuff.next(8))[0]
                    indp_axis_key = struct.unpack(
                        '<Q', subbuff.next(8)
                    )[0]
                    name = subbuff.next_mtrxstr()
                    unit = subbuff.next_mtrxstr()
                    self.axch[axis_key] = DependentAxis(
                        axis_key, name, unit, indp_ax=self.axch[indp_axis_key]
                    )
                    self.log.write(8*' ')
                    self.log.write(
                        '{}, {}, {}, {}\n'.format(
                            axis_key, indp_axis_key, name, unit
                        )
                    )
                # END for
                self.log.write(8*' '  + '---\n')
                
                # 3rd sub-dictionary
                # Channel information
                # [ chnl_key, depn_axis_key, descrip ]
                dict_len = subbuff.next_uint()
                for i in range(dict_len):
                    chnl_key = struct.unpack('<Q', subbuff.next(8))[0]
                    depn_axis_key = struct.unpack(
                        '<Q', subbuff.next(8)
                    )[0]
                    descrip = subbuff.next_mtrxstr()
                    self.axch[chnl_key] = InstrChannel(
                        chnl_key, descrip, self.axch[depn_axis_key]
                    )
                    self.log.write(8*' ')
                    self.log.write(
                        '{}, {}, {}\n'.format(
                            chnl_key, depn_axis_key, descrip
                        )
                    )
                # END for
                self.log.write(8*' '  + '---\n')
            elif subname == 'CHCS':
                # The first sub-dictionary is for independent axes
                # axis_key, N_points, N_following_axes, 0
                # *not sure what the zero is for
                n = subbuff.next_uint()
                for i in range(n):
                    axis_key = struct.unpack('<Q', subbuff.next(8))[0]
                    Ns = [subbuff.next_uint() for _ in range(3)]
                    self.axch[axis_key].len = Ns[0]
                    self.log.write(8*' ')
                    self.log.write(
                        '{}, {}, {}, {}\n'.format(axis_key, *Ns)
                    )
                # END for
                self.log.write('        ---\n')
                # The 2nd dictionary is for dependent axes
                # axis_key, 1, 0
                # *not sure what the 1 & 0 are for
                n = subbuff.next_uint()
                for i in range(n):
                    axis_key = struct.unpack('<Q', subbuff.next(8))[0]
                    Ns = [subbuff.next_uint() for j in range(2)]
                    self.log.write(8*' ')
                    self.log.write('{}, {}, {}\n'.format(axis_key, *Ns))
                # END for
                self.log.write('        ---\n')
                # The 3rd dictionary is for channels
                # chnl_key, N_depn_axes, N_bits
                n = subbuff.next_uint()
                for i in range(n):
                    axis_key = struct.unpack('<Q', subbuff.next(8))[0]
                    Ns = [subbuff.next_uint() for j in range(2)]
                    self.log.write(8*' ')
                    self.log.write('{}, {}, {}\n'.format(axis_key, *Ns))
                # END for
                self.log.write('        ---\n')
            elif subname == 'XFER':
                while len(subbuff) > 0:
                    depn_axis_key = struct.unpack('<Q', subbuff.next(8))[0]
                    tf_type = subbuff.next_mtrxstr()
                    unit = subbuff.next_mtrxstr()
                    n_params = subbuff.next_uint()
                    tf_params = {}
                    self.log.write(8*' ')
                    self.log.write(
                        '{}: {} ({})\n'.format(depn_axis_key, tf_type, unit)
                    )
                    for j in range(n_params):
                        param_name = subbuff.next_mtrxstr()
                        value = subbuff.next_mtrxtype()
                        tf_params[param_name] = value
                        self.log.write(
                            12*' ' + '{} = {}\n'.format(param_name, value)
                        )
                    # END for
                    
                    self.axch[depn_axis_key].trans_func = TransferFunction(
                        tf_type, unit, **tf_params
                    )
                # END while
            else:
                subbuff.advance()
            # END if
        # END while
    # END _init_read_CCSY
    
    def _parse_marks(self):
        pass
    # END _parse_marks
    
    def import_scan( self, file_path, scan_only=False, calc_duration=False,
                     debug=False
                   ):
        '''Read a scan file and return ScanData objects
        
        Args:
            file_path (str): path to .*_mtrx scan data file
            scan_only (bool): When True function will not attach linked spectra
                              to the ScanData objects
            debug (bool): switch for writing a debugging file describing
                          how the data file was interpreted
        Returns:
            (list(ScanData)) [trace_up, retrace_up, trace_down, retrace_down]
        '''
        
        file_dir, file_name = os.path.split(file_path)
        file_dir += '/'
        params = self.datafile_st[file_name]
        if debug:
            fdebug = open(file_name + '-debug.txt', 'w')
        else:
            fdebug = None
        # END if
        filebuff, _, t = MatrixBuffer.from_file(file_path)
        timestr = time.ctime(t)
        
        if fdebug:
            fdebug.write(timestr+'\n')
        # END if
        
        # Skip empty space
        filebuff.advance(4)
        if fdebug:
            fdebug.write('empty 4B\n')
        # END if
        # Read blocks
        while filebuff:
            bkbuff, bkname = filebuff.next_bk()
            if fdebug:
                fdebug.write('{} {}B\n'.format(bkname, len(bkbuff)))
            # END if
            if re.search(r'DESC', bkname):
                chnl_key, _, N_act, _ = self._read_DESC(bkbuff, fdebug)
                # Look up transfer function and convert values in Zs
                depn_ax = self.axch[chnl_key].depn_ax
            elif re.search(r'DATA', bkname):
                Zs = self._read_DATA_scan(bkbuff, depn_ax)
                # Heuristic to force the file closed after the data block
            # END if
            bkbuff.advance()
        # END while
        filebuff.close()
        
        if fdebug:
            fdebug.close()
        # END if
        
        # Calculate how long it took to take the scan
        scn_t = [0.0, 0.0]
        fast_ax = depn_ax.indp_ax
        if calc_duration:
            N = 1
            while N <= N_act:
                i = (N-1) / (fast_ax.len*params['XYScanner_Lines'].value)
                scn_t[i] += params['XYScanner_Raster_Time'].value
                N += 1
            # END while
        # END if
        
        # X & Y offset specify where the center of the map is
        N = params['XYScanner_Points'].value
        a = -1*(N-1)/2.0
        b = -1*a
        dx = float(params['XYScanner_Width'].value) / (N-1)
        X_ax = params['XYScanner_X_Offset'].value + np.linspace(a, b, N)*dx
        #print 'width = {} nm'.format(params['XYScanner_Width'].value*1E9)
        #print 'X_ax = [{:+0.2e}, {:+0.2e}]'.format(X_ax[0], X_ax[-1])
        N = params['XYScanner_Lines'].value
        a = -1*(N-1)/2.0
        b = -1*a
        dy = float(params['XYScanner_Height'].value) / (N-1)
        Y_ax = params['XYScanner_Y_Offset'].value + np.linspace(a, b, N)*dy
        #print 'height = {} nm'.format(params['XYScanner_Height'].value*1E9)
        #print 'Y_ax = [{:+0.2e}, {:+0.2e}]'.format(Y_ax[0], Y_ax[-1])
        
        # order of scns list will be:
        #   [trace_up, retrace_up, trace_down, retrace_down]
        Nscn, Nrun = re.search(r'--(\d+)_(\d+)\.', file_name).groups()
        params_alt = { 'file': file_name, 'time': t,
                       'index': int(Nscn), 'rep': int(Nrun),
                       'Channel': depn_ax.name
                     }
        for pname in params:
            params_alt[pname] = params[pname].value
        scans = []
        
        # retrieve all image comments
        if file_name in self.img_comments:
            comments = sorted(
                self.img_comments[file_name], key=lambda tup: tup[0]
            )
        else:
            comments = []
        # END if
        # TODO: correct this, it is a temporary soution
        #       comments should be attached to the specific direction they
        #       do with
        all_cmnt = ''
        for d, cmnt in comments:
            all_cmnt += ' ' + cmnt
        # END for
        if all_cmnt:
            all_cmnt = re.sub(r'[\n\r]+', ' ', all_cmnt[1:])
        params_alt['Comment'] = all_cmnt
        
        for i in range(len(Zs)):
            params_alt['duration'] = scn_t[i]
            for j in range(len(Zs[i])):
                params_alt['direction'] = 2*i + j
                scans.append( ScanData(X_ax, Y_ax, Zs[i][j], params_alt) )
            # END for
        # END for
        for s in scans:
            s.spectra = []
        # END for
        
        if scan_only:
            # return prematurely and skip attachment of linked spectra
            return scans
        # END if
        
        # import any linked spectra and attach them in the .spectra attribute
        # stslinks[fname] = [(mrk, spectra_fname), (mrk, spectra_fname), ...]
        # mrk = ('ii', 'i', 'd', 'xpx,ypx;xpy,ypy', chnl_name)
        file_sts_links = []
        if file_name in self.stslinks:
            file_sts_links = self.stslinks[file_name]
        for mrk, spec_file in file_sts_links:
            d = int(mrk[2])
            try:
                scans[d].spectra.extend(
                    self.import_spectra(file_dir+spec_file)
                )
                for c in scans[d].spectra:
                    # TODO: try to find a solution where you don't have to
                    # change a private attribute
                    #c._xphys  = c.px_coord(0)*dx + X_ax[0]
                    #c._yphys  = c.px_coord(1)*dy + Y_ax[0]
                    pass
            except IOError:
                pass
            # END try
        # END for 
        
        return scans
    # END import_scan
    
    def _read_DESC(self, buff, fdebug=None):
        chnl_hash = struct.unpack('<Q', buff.next(8))[0]
        # Unknown 12B
        buff.advance(12)
        # Number of data points set to be recorded in the DATA block
        Npoints_set = buff.next_uint()
        # Actual number of data points recorded in the DATA block
        Npoints_act = buff.next_uint()
        # data type as a string, should be "SI32" (32-bit Signed Integer)
        data_type_str = buff.next_mtrxstr()
        # Number of images recorded? (i.e. tu, ru, td, and rd would be 4)
        Nimages = buff.next_uint()
        # Unknown, 1? could be bool
        buff.advance(4)
        # Unknown, 0? could be bool
        buff.advance(4)
        # set data point count is repeated, again
        Npoints_set_alt = buff.next_uint()
        
        if fdebug:
            fdebug.write('<x{:08X}>\n'.format(chnl_hash))
            fdebug.write('Max No. points {}\n'.format(Npoints_set))
            fdebug.write('No. points {}\n'.format(Npoints_act))
            fdebug.write('Data type {}\n'.format(data_type_str))
            fdebug.write('No. recorded axes {}\n'.format(Nimages))
            fdebug.write(
                'Max No. points (again?) {}\n'.format(Npoints_set_alt)
            )
        # END if
        
        return chnl_hash, Npoints_set, Npoints_act, Nimages
    # END _read_DESC
    
    def _read_DATA_scan(self, bkbuff, depn_ax):
        '''ScanData data reading function for import_scan
        
        Args:
            buff (ByteBuffer): binary data buffer
            params (dict): settings state dict for the scan
        Returns:
            (list)(list)(NxM ndarray) [ [Z_traceup,   Z_retraceup  ],
                                        [Z_tracedown, Z_retracedown]
                                      ]
        '''
        
        # axes
        fast_ax = depn_ax.indp_ax
        slow_ax = fast_ax.next_ax
        
        if len(bkbuff)%4 != 0:
            raise RuntimeError('Hanging bytes')
        try:
            Z_tree = np.zeros(slow_ax.len*fast_ax.len)
        except TypeError as err:
            pdb.set_trace()
            quit()
        i = 0
        # TODO: test that this doesn't fail on an incomplete scan
        for j in range(len(bkbuff)/4):
            Z_tree[j] = bkbuff.next_uint() #tf( bkbuff.next_uint() )
        # END while
        
        if not slow_ax.mirrored:
            Ypx = slow_ax.len
            Z_tree = [Z_tree]
        else:
            Ypx = slow_ax.len / 2
            Z_tree = [ Z_tree[:Ypx*fast_ax.len],
                       Z_tree[Ypx*fast_ax.len:][::-1]
                     ]
        # END if
        if not fast_ax.mirrored:
            Xpx = fast_ax.len
            for i in range(len(Z_tree)):
                Z_tree[i] = [Z_tree[i]]
        else:
            Xpx = fast_ax.len / 2
            for i in range(len(Z_tree)):
                Z_tree[i] = np.split(Z_tree[i], Ypx*2)
                Z_tree[i] = [ np.concatenate(Z_tree[i][::2]),
                              np.concatenate(Z_tree[i][1::2])
                            ]
            # END for
        # END if
        
        for i in range(len(Z_tree)):
            for j in range(len(Z_tree[i])):
                if j%2 == 0:
                    Z_tree[i][j] = np.flipud(
                        np.reshape(Z_tree[i][j], (Ypx,Xpx))
                    )
                else:
                    Z_tree[i][j] = np.fliplr(np.flipud(
                        np.reshape(Z_tree[i][j], (Ypx,Xpx))
                    ))
            # END for
        # END for
        
        return Z_tree
    # END _read_DATA_scan
    
    def import_spectra(self, file_path):
        '''Read a spectroscopy data file and return CurveData objects
        
        Args:
            file_path (str): standard full path
        Returns:
            (list) [CurveData, CurveData, ...]
        '''
        # TODO: add transfer function, it will not be the same as a scan
        # TODO: add parsing and storing of coordinates
        
        file_name = os.path.basename(file_path)
        params = self.datafile_st[file_name]
        
        filebuff, _, t = MatrixBuffer.from_file(file_path)
        
        # Skip empty space
        filebuff.next(4)
        # Read sub-blocks (DESC & DATA)
        while filebuff:
            bkbuff, bkname = filebuff.next_bk()
            if re.search(r'DESC', bkname):
                chnl_key, Npt_set, Npt_act, _ = self._read_DESC(bkbuff)
                depn_ax = self.axch[chnl_key].depn_ax
                indp_ax = depn_ax.indp_ax
            elif re.search(r'DATA', bkname):
                all_Ys = self._read_DATA_spectra(bkbuff, depn_ax, indp_ax)
                # Heuristic to force the file closed after the data block
            # END if
            if len(bkbuff) > 0:
                raise RuntimeError('hanging bytes')
        # END while
        filebuff.close()
        
        # make X array
        #if indp_ax.elem == 'Spectroscopy' and indp_ax.name == 'V':
        if indp_ax.qual_name[-1] == 'V':
            x0 = params['Spectroscopy_Device_1_Start'].value
            xf = params['Spectroscopy_Device_1_End'].value
            X = np.linspace(x0, xf, len(all_Ys[0]))
            x_units = params['Spectroscopy_Device_1_Start'].unit
        elif re.search('Clock2', indp_ax.qual_name):
            tstep = params['Clock2_Period'].value
            N = params['Clock2_Samples'].value
            X = np.arange(N) * tstep
            x_units = 's'
        else:
            raise ValueError(
                'Cannot parse independent axis {}'.format(indp_ax.__dict__)
            )
        # END if
        
        # make a simplified version of the params dict
        params_alt = {k: params[k].value for k in params}
        # Channel = Z(V) <-- read this when you look for the TF
        params_alt['channel'] = depn_ax.name
        params_alt['time'] = t
        try:
            # stslinks[spectra_fname] = ((ii, i, d, locstr, chnl_hash), scn_fname)
            params_alt['parent'] = self.stslinks[file_name][1]
            # Example locstr:
            #  "-193,205;7.16667e-009,9.16667e-009"
            # pixel coordinates are relative to bottom left corner
            # physical coordinates are relative to scan center
            coords = re.split(r';|,', self.stslinks[file_name][0][3])
            #coords = self.stslinks[file_name][0][3].split(';')
            params_alt['coord_px'] = ( int(coords[0]), int(coords[1]) )
            params_alt['coord_phys'] = ( float(coords[2]), float(coords[3]) )
        except KeyError:
            params_alt['parent'] = None
            params_alt['coord_px'] = None
            params_alt['coord_phys'] = None
        # END try
        spec_indices = re.search(r'^.*?--(\d+)_(\d+).*$', file_name).groups()
        params_alt['index'] = int(spec_indices[0])
        params_alt['rep'] = int(spec_indices[1])
        
        if re.search('Clock2', indp_ax.qual_name):
            X += (params_alt['rep']-1) * len(X) * tstep
        # END if
        
        for i, Y in enumerate(all_Ys):
            params_alt['direction'] = i
            all_Ys[i] = CurveData(
                X, Y, x_units=x_units, y_units=depn_ax.unit,
                props=params_alt
            )
        # END for
        
        return all_Ys
    # END import_spectra
    
    def _read_DATA_spectra(self, buff, depn_ax, indp_ax):
        '''Reads DATA block of a spectroscopy data file
        
        Private helper function for import_spectra
        
        Args:
            buff (ByteBuffer): file read buffer
            depn_ax (tuple): dependent axis information
        Returns:
            (list) [y_0, y_1, y_2, ...]
            y_i (ndarray)
        '''
        if not depn_ax.indp_ax.mirrored:
            Ncrv = 1
            ppc = int(depn_ax.indp_ax.len)
        else:
            Ncrv = 2
            ppc = int(depn_ax.indp_ax.len)/2
        # END if
        all_Ys = [np.zeros(ppc) for i in range(Ncrv)]
        i = 0
        while buff:
            c = i/ppc
            ii = (c%2)*(ppc-1-i) + ((c+1)%2)*i
            all_Ys[c][ii] = depn_ax.trans_func( buff.next_int() )
            i += 1
        # END while
        
        return all_Ys
    # END _read_DATA_spectra
# END Experiment

#==============================================================================
def import_scan(file_path, lp=('triangular', 'triangular'), debug=False):
    '''
    '''
    
    file_dir, file_name = os.path.split(file_path)
    file_dir += '/'
    if debug:
        fdebug = open(file_name + '-debug.txt', 'w')
    else:
        fdebug = None
    # END if
    filebuff, _, t = MatrixBuffer.from_file(file_path)
    
    if fdebug:
        #fdebug.write(magicword+'\n')
        timestr = time.ctime(t)
        fdebug.write(timestr+'\n')
    # END if
    
    # Skip empty space
    filebuff.next(4)
    # Read blocks
    while filebuff:
        bkbuff, bkname = filebuff.next_bk()
        if fdebug:
            fdebug.write( '{} {}B\n'.format(bkname, len(bkbuff)) )
        # END if
        if re.search(r'DESC', bkname):
            _, Npnt_set, Npnt_act = list( _read_DESC(bkbuff, fdebug) )
        elif re.search(r'DATA', bkname):
            Zs = _read_DATA_scan(bkbuff, lp, Npnt_set, Npnt_act)
            # Heuristic to force the file closed after the data block
        # END if
        bkbuff.advance()
    # END while
    filebuff.close()
    
    if fdebug:
        fdebug.close()
    # END if
    
    Nscn, Nrun = re.search(r'--(\d+)_(\d+)\.', file_name).groups()
    params = { 'file': file_name, 'time': t,
                   'index': int(Nscn), 'rep': int(Nrun)
                 }
    scans = []
    
    for i in range(len(Zs)):
        for j in range(len(Zs[i])):
            params['direction'] = 2*i + j
            scans.append(
                ScanData( range(Zs[i][j].shape[0]), range(Zs[i][j].shape[1]),
                      Zs[i][j], params
                    )
            )
        # END for
    # END for
    for s in scans:
        s.spectra = []
    # END for
    
    return scans
# END import_scan
    
def _read_DESC(buff, fdebug=None):
    x = buff.next(8)
    chnl_hash = struct.unpack('<Q', x)[0]
    # Unknown 12B
    buff.next(12)
    #a = buff.next_uint()
    #b = buff.next_uint()
    #c = buff.next_uint()
    # Number of data points set to be recorded in the DATA block
    Npoints_set = buff.next_uint()
    # Actual number of data points recorded in the DATA block
    Npoints_act = buff.next_uint()
    # data type as a string, should be "SI32" (32-bit Signed Integer)
    data_type_str = buff.next_mtrxstr()
    buff.next(12)
    # Unknown, 4?
    #unbytes_4 = buff.next_uint()
    # Unknown, 1? could be bool
    #unbytes_2 = buff.next_uint()
    # Unknown, 0? could be bool
    #unbytes_3 = buff.next_uint()
    # set data point count is repeated, again
    Npoints_set_alt = buff.next_uint()
    
    if fdebug:
        fdebug.write('channel hash <x{:08X}>\n'.format(chnl_hash))
        #fdebug.write('{} {} {}'.format(a,b,c)+'\n')
        fdebug.write('Max No. points {}\n'.format(Npoints_set))
        fdebug.write('No. points {}\n'.format(Npoints_act))
        fdebug.write('Data type {}\n'.format(data_type_str))
        #fdebug.write('{}\n'.format(unbytes_4))
        #fdebug.write('{} \n'.format(unbytes_2))
        #fdebug.write('{} \n'.format(unbytes_3))
        fdebug.write(
            'Max No. points (again?) {}\n'.format(Npoints_set_alt)
        )
    # END if
    
    return chnl_hash, Npoints_set, Npoints_act
# END _read_DESC

def _read_DATA_scan(bkbuff, lp, Npnts_set, Npnts_act):
    '''ScanData data reading function for import_scan
    
    Args:
        buff (ByteBuffer): binary data buffer
        lp (tup): looping pattern (lp[0], lp[1])
        Npnt_set (int)
        Npnt_act (int)
    Returns:
        (list)(list)(NxN ndarray) [ [Z_traceup,   Z_retraceup  ],
                                    [Z_tracedown, Z_retracedown]
                                  ]
    '''
    
    # ***This function assumes that the scan image is square ***
    Nimg = 1
    if lp[0] == 'triangular':
        Nimg *= 2
    if lp[1] == 'triangular':
        Nimg *= 2
    slow_Npnts = int( np.sqrt(float(Npnts_set)/Nimg) )
    fast_Npnts = int(slow_Npnts)
    if lp[0] == 'triangular':
        slow_Npnts *= 2
    if lp[1] == 'triangular':
        fast_Npnts *= 2
    
    Z_tree = np.zeros(slow_Npnts*fast_Npnts)
    if len(Z_tree) < len(bkbuff)/4:
        raise RuntimeError(
            '{}B in block, len(Z_tree) = {}'.format( len(bkbuff)/4,
                                                     len(Z_tree)
                                                   )
        )
    for i in range(len(bkbuff)/4):
        Z_tree[i] = bkbuff.next_uint()
    # END while
    
    if lp[0] == 'linear':
        Ypx = slow_Npnts
        Z_tree = [Z_tree]
    elif lp[0] == 'triangular':
        Ypx = slow_Npnts / 2
        Z_tree = [Z_tree[:Ypx*fast_Npnts], Z_tree[Ypx*fast_Npnts:][::-1]]
        #Z_tree = unwind_split(Z_tree, Ypx*fast_Npnts)
    else:
        raise RuntimeError(
            'Cannot understand value of {}'.format(lp[0])
            + 'for slow scan axis looping pattern.'
        )
    # END if
    if lp[1] == 'linear':
        Xpx = fast_Npnts
        for i in range(len(Z_tree)):
            Z_tree[i] = [Z_tree[i]]
    elif lp[1] == 'triangular':
        Xpx = fast_Npnts / 2
        for i in range(len(Z_tree)):
            Z_tree[i] = np.split(Z_tree[i], Ypx*2)
            Z_tree[i] = [ np.concatenate(Z_tree[i][::2]),
                          np.concatenate(Z_tree[i][1::2])
                        ]
            #Z_tree[i] = unwind_split(Z_tree[i], Xpx)
        # END for
    else:
        raise RuntimeError(
            'Cannot understand value of {}'.format(lp[1])
            + 'for fast scan axis looping pattern.'
        )
    # END if
    
    for i in range(len(Z_tree)):
        for j in range(len(Z_tree[i])):
            if j%2 == 0:
                Z_tree[i][j] = np.flipud(
                    np.reshape(Z_tree[i][j], (Ypx,Xpx))
                )
            else:
                Z_tree[i][j] = np.fliplr(np.flipud(
                    np.reshape(Z_tree[i][j], (Ypx,Xpx))
                ))
    # END for
    
    return Z_tree
# END _read_DATA_scan
    
def import_spectra(self, file_path, lp='linear', debug=True):
    '''Read a spectroscopy data file and return CurveData objects
    
    Args:
        file_path (str): standard full path
    Returns:
        (list) [CurveData, CurveData, ...]
    '''
    # TODO: add transfer function, it will not be the same as a scan
    # TODO: add parsing and storing of coordinates
    
    file_name = os.path.basename(file_path)
    
    filebuff, _, t = MatrixBuffer(file_path)
    
    # Skip empty space
    filebuff.next(4)
    # Read sub-blocks (DESC & DATA)
    while filebuff:
        bkbuff, bkname = filebuff.next_bk()
        if re.search(r'DESC', bkname):
            _, Npnt_set, Npnt_act = _read_DESC(bkbuff)
        elif re.search(r'DATA', bkname):
            all_Ys = _read_DATA_spectra(bkbuff, lp, Npnt_set, Npnt_act)
            # Heuristic to force the file closed after the data block
            filebuff.next(len(filebuff))
        # END if
    # END while
    filebuff.close()
    
    # make X array
    X = np.arange( float(len(all_Ys[0])) )
    
    # make a simplified version of the DELETE_params dict
    params = {}
    # Channel = Z(V) <-- read this when you look for the TF
    params['time'] = t
    spec_indices = re.search(r'^.*?--(\d+)_(\d+).*$', file_name).groups()
    params['Spec Index'] = '{0:0>3s}-{1:0>2s}'.format(*spec_indices)
    
    d = ['f', 'r']
    all_Ys.append(None)
    while all_Ys[0] is not None:
        Y = all_Ys.pop(0)
        params['Spec Index'] = params['Spec Index'] + d[0]
        d.append( d.pop(0) )
        crv = CurveData(
            X, Y, sourcefile=file_name, eqpsets=params
        )
        all_Ys.append(crv)
    # END for
    all_Ys.pop(0)
    
    return all_Ys
# END import_spectra

def _read_DATA_spectra(self, buff, lp, Npnts_set, Npnts_act):
    '''Reads DATA block of a spectroscopy data file
    
    Private helper function for import_spectra
    
    Args:
        buff (ByteBuffer): file read buffer
        depn_ax (tuple): dependent axis information
        indp_ax (tuple): independent axis information
    Returns:
        (list) [y_0, y_1, y_2, ...]
        y_i (ndarray)
    '''
    #  depn_ax = (chnl_name, chnl_unit, TransferFunction, h_indp_ax)
    #  indp_ax = (device_name, device_looping_pattern, ppl, 0)
    if lp == 'linear':
        Ncrv = 1
        ppc = int(Npnts_set)
    elif lp == 'triangular':
        Ncrv = 2
        ppc = int(Npnts_set)/2
    else:
        raise RuntimeError('Cannont parse independent axis looping pattern')
    # END if
    all_Ys = [np.zeros(ppc) for i in range(Ncrv)]
    i = 0
    while buff:
        c = i/ppc
        ii = (c%2)*(ppc-1-i) + ((c+1)%2)*i
        all_Ys[c][ii] = buff.next_uint()
        i += 1
    # END while
    
    return all_Ys
# END _read_DATA_spectra

#==============================================================================
def unwind_split(A, n):
    # A is a numpy.ndarray
    B = np.zeros(len(A)/2, dtype=A.dtype)
    i_B = 0
    C = np.zeros(len(A)/2, dtype=A.dtype)
    i_C = 0
    for i in range(0, len(A), 2*n):
        for j in range(0, n):
            B[i_B] = A[i+j]
            i_B += 1
        for j in range(n, 2*n)[::-1]:
            C[i_C] = A[i+j]
            i_C += 1
    # END for
    return [B, C]
# END unravel_list

#==============================================================================
class InstrChannel(object):
    def __init__(self, mtrx_hash_value, descrip='', depn_ax=None):
        self.descrip = descrip
        self.depn_ax = depn_ax
        self._mtrx_hash_value = mtrx_hash_value
    # END __init__
    
    def __hash__(self): return self._mtrx_hash_value
# END InstrChannel

#==============================================================================
class DependentAxis(object):
    def __init__( self, mtrx_hash_value, name='', unit='', trans_func=None,
                  indp_ax = None
                ):
        self.name = name
        self.unit = unit
        self.trans_func = trans_func
        self.indp_ax = indp_ax
        self._mtrx_hash_value = mtrx_hash_value
    # END __init__
    
    def __call__(self, *args, **kwargs):
        return self.trans_func(*args, **kwargs)
    # END __call__
    
    def __hash__(self): return self._mtrx_hash_value
    
    def __str__(self):
        return '<DependentAxis @ MTRX {}>'.format(self.mtrx_hash_value)
    # END __str__
# END DependentAxis

#==============================================================================
class IndependentAxis(object):
    def __init__( self, mtrx_hash_value, qual_name='', mirrored=False, len=0,
                  next_ax=None
                ):
        self.qual_name = qual_name
        #self.instr, self.elem, self.name = qual_name.split('::')
        self.mirrored = mirrored
        self.len = len
        self.next_ax = next_ax
        self._mtrx_hash_value = mtrx_hash_value
    # END __init__
    
    def __hash__(self): return self._mtrx_hash_value
    
    def __len__(self): return self.len
# END IndependentAxis

#==============================================================================
class MatrixProperty(object):
    '''Class structure for storing property settings in an Experiment
    
    MatrixProperty objects can be used to represent settings or physical
    quantities.  They will have hash values equal to the hash value of their
    name string.
    
    Instantiation Args:
        channel (str)
        name (str)
        unit (str)
        value (str)
    Instance Attributes:
        name (str): property name, this will be a concat. of channel_name
        unit (str): property units
        value (str): property value
    '''
    
    def __init__(self, channel, name, unit, value):
        self._ptup = (channel + '_' + name, unit, value)
    # END __init__
    
    def __getitem__(self, i):
        return self._ptup[i]
    # END __getitem__
    
    def __hash__(self):
        return str(self)
    # END __hash__
    
    def __str__(self):
        return '{0} = {2} {1}'.format(*self._ptup)
    # END __str__
    
    @property
    def name(self):
        return self._ptup[0]
    # END name
    
    @property
    def unit(self):
        return self._ptup[1]
    # END unit
    
    @property
    def value(self):
        return self._ptup[2]
    # END value
# END MatrixProperty

#==============================================================================
class MatrixBuffer(object):
    '''Buffer class for byte stream in a MATRIX file format
    
    Instantiation Args:
        s (str): string object that will serve as the buffer data
    Instance Attributes:
        s (str)
    '''
    
    def __init__(self, *args):
        self._f = args[0]
        self._N = args[-1]
        if len(args) == 3:
            # args = [f, i_start, bklen]
            self._i = args[1]
        elif len(args) == 2:
            self._i = 0
        else:
            raise TypeError(
                'Incorrect number of arguments for MatrixBuffer, ' +
                '{} given'.format(len(args))
            )
        # END if
        self._subbuff = None
    # END __init__
    
    def __len__(self):
        y = self._N-self._i
        if y >= 0:
            return y
        else:
            print 'self._N = {}, self._i = {}'.format(self._N, self._i)
            raise RuntimeError('MatrixBuffer over-read')
    # END __len__
    
    def __nonzero__(self):
        if len(self) > 0:
            return True
        else:
            return False
        # END if
    # END __nonzero__
    
    def __str__(self):
        out = self._f.read(self._N-self._i)
        self._f.seek(-(self._N-self._i), 1)
        return out
    # END __str__
    
    @property
    def active(self):
        if self._i >= self._N:
            return False
        # END if
        return True
    # END active
    
    def advance(self, n=None):
        if n is None:
            n = len(self)
        self._f.seek(n,1)
        self._i += n
    # END advance
    
    def _subbuff_check(self):
        if self._subbuff is not None:
            if self._subbuff:
                raise RuntimeError( 'Cannot access MatrixBuffer while a ' +
                                      'sub-buffer is currently active'
                                    )
            else:
                self._subbuff = None
            # END if
        # END if
        return None
    # END _subbuff_check
    
    @classmethod
    def from_file(cls, file_path):
        f = open(file_path, 'rb')
        # ONMATRIX0101
        magicword = f.read(12)
        if not re.search('ONTMATRX0101', magicword):
            f.close()
            raise ValueError(
                'Incorrect file type, "{}"'.format(magicword)
            )
        # END if
        # Name of whole file block
        bkname = f.read(4)
        # file length
        bklen = struct.unpack('<I', f.read(4))[0]
        # file timestamp
        bkt = struct.unpack('<Q', f.read(8))[0]
        
        return cls(f, bklen), bkname, bkt
    # END from_file
    
    def close(self):
        self._f.close()
    # END close
    
    def next(self, n=1):
        if self._subbuff is not None:
            if self._subbuff:
                raise RuntimeError( 'Cannot access MatrixBuffer while a ' +
                                      'sub-buffer is currently active'
                                    )
            else:
                self._subbuff = None
            # END if
        elif n < 1:
            raise ValueError('Cannot get less than 1 byte from ByteBuffer')
        elif self._N < self._i + n:
            raise ValueError(
                'asked for {} bytes, but only {} left'.format(
                    n, len(self)
                )
            )
        # END if
        self._i += n
        return self._f.read(n)
    # END next
    
    def next_bk(self, timestamp=False):
        if self._subbuff is not None:
            if self._subbuff:
                raise RuntimeError( 'Cannot access MatrixBuffer while a ' +
                                      'sub-buffer is currently active'
                                    )
            else:
                self._subbuff = None
            # END if
        # END if
        bytes_needed = 8
        if timestamp:
            bytes_needed += 8
        if len(self) < bytes_needed:
            raise RuntimeError('Not enough bytes left for a block')
        # END if
        bkname = []
        self._i += 4
        for i in range(4):
            bkname.insert(0, self._f.read(1))
        bkname = ''.join(bkname)
        self._i += 4
        bklen = struct.unpack('<I', self._f.read(4))[0]
        # END if
        if timestamp:
            # block timestamp
            self._i += 8
            bkt = struct.unpack('<Q', self._f.read(8))[0]
        # END if
        if self._N < self._i+bklen:
            raise RuntimeError('next_bk asked for over-read')
        self._subbuff = MatrixBuffer(self._f, bklen)
        self._i += bklen
        if timestamp:
            return self._subbuff, bkname, bkt
        else:
            return self._subbuff, bkname
        # END if
    # END next_buff
    
    def next_uint(self):
        return struct.unpack('<I', self.next(4))[0]
    # END next_uint
    
    def next_int(self):
        return struct.unpack('<i', self.next(4))[0]
    # END next_uint
    
    def next_double(self):
        return struct.unpack('d', self.next(8))[0]
    # END next_double
    
    def next_mtrxstr(self):
        '''Each string starts with a 4-byte unsigned integer declaring the
        string length'''
        
        strlen = self.next_uint()
        if strlen > 10000:
            # This can't be right...  That would be a ridiculously long str!
            raise RuntimeError('String is too long ({})'.format(strlen))
        else:
            # Grab the set number of bytes and read it as UTF-16 characters
            return unicode(self.next(2*strlen), 'utf-16')
        # END if
    # END next_mtrxstr
    
    def next_mtrxtype(self):
        mtrxtype = self.next(4)[::-1]
        if mtrxtype == 'BOOL':
            # boolean type, 4B
            value = bool(self.next_uint())
        elif mtrxtype == 'LONG':
            # unsigned int type, 4B
            value = self.next_uint()
        elif mtrxtype == 'STRG':
            # string type
            value = self.next_mtrxstr()
        elif mtrxtype == 'DOUB':
            # double-length floating point real number, 8B
            value = self.next_double()
        else:
            raise RuntimeError( 'unknown matrix type, "{}"'.format(mtrxtype) )
        # END if
        
        return value
    # END next_mtrxtype
    
    def next_mtrxparam(self, chnl):
        prop = self.next_mtrxstr()
        unit = self.next_mtrxstr()
        #skip empty space
        self.next(4)
        value = self.next_mtrxtype()
        
        return MatrixProperty(chnl, prop, unit, value)
    # END next_mtrxparam
# END MatrixBuffer

#==============================================================================
class TransferFunction(object):
    '''MATRIX Transfer Function
    
    A TransferFunction object can be used to convert the raw data point to
    physical quantities
    
    Instance Attributes:
        name (str): ?
        tf_func (str): label describing which equation to use for conversion
        unit (str): physical units of converted values
        params (dict): parameters for the conversion equation, see MATRIX
                       documentation for details
    Example:
        TODO fill in this example
    '''
    
    def __init__(self, name, unit, **params):
        self.name = name
        self.tf_func = {
            'TFF_Identity': self._call_identity,
            'TFF_Linear1D': self._call_linear_1d,
            'TFF_MultiLinear1D': self._call_multilinear_1D
        }
        self.unit = unit
        self.params = params
    # END __init__
    
    def __call__(self, x):
        return self.tf_func[self.name](x)
    
    def _call_identity(self, x):
        return float(x)
    # END _call_identity
    
    def _call_linear_1d(self, x):
        return (x - self.params['Offset']) / self.params['Factor']
    # END _call_linear_1d
    
    def _call_multilinear_1D(self, x):
        return (
            (self.params['Raw_1'] - self.params['PreOffset'])
            * (x - self.params['Offset'])
            / self.params['NeutralFactor'] / self.params['PreFactor']
        )
    # END _call_multilinear_1D
# END TransferFunction


