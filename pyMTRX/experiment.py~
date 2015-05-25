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
from datetime import datetime
from StringIO import StringIO
from pprint import pprint, pformat
import pdb
from collections import namedtuple
from copy import copy

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
        _datafile_st (dict): settings state dictionaries keyed by data file
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
    
    # Class Methods
    #--------------
    @classmethod
    def is_image(self, file_name):
        if re.search(r'\.[^.()]+?_mtrx$', file_name):
            return True
        else:
            return False
    # END is_point_spectra
    
    @classmethod
    def is_point_spectrum(self, file_name):
        if re.search(r'\.[^.]+?\([^.]+?\)_mtrx$', file_name):
            return True
        else:
            return False
    # END is_point_spectra
    
    # Object instantiation
    #---------------------
    def __init__(self, file_path, debug=False):
        self.fp = file_path
        # Initial settings state dictionary
        self.init_st = {}
        self.st_hist = []
        self.timeline = Timeline()
        # Settings state to be kept current with the timeline
        self._curr_st = {}
        self._datafile_st = {}
        self.stslinks = {}
        self.sample = ''
        self.data_set = ''
        self.comment = ''
        self.cmnt_lkup = {}
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
            
            # On first pass only read in the
            # channel/axis dictionary information
            while self._init_readblock(f, axch_pass=True): pass
            
            # On second pass read everything else
            f.seek(12)
            while self._init_readblock(f): pass
        # END with
        
        # all remaining unlinked spectra did not have their "parent" images
        # saved
        self.free_spectra.extend(self.unlinked_spectra)
        
        # when debugging write some variables directly to the file
        if debug:
            exp_date = re.search(r'\d{4}\w{3}\d\d-\d{6}', file_path).group(0)
            log_sname = 'debug log {0:%Y%m%d} for {1}.txt'
            log_sname = log_sname.format(datetime.now(), exp_date)
            f = open(log_sname, 'w')
            # print out the axis hierarchy
            f.write('self.axch = \n')
            for k in sorted(self.axch.keys()):
                f.write('    {0} (x{0:0>16x}):\n'.format(k))
                #f.write('        {}').format(type(self.axch[k]).__name__)
                #i = 0
                obj_str = pformat(self.axch[k].__dict__, 2, 79-16)
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
                    if re.search(r'\.[^()]+_mtrx$', k):
                        f.write('    ')
                        kdisp = re.search(r'--.*$', k).group(0)
                        v = self.stslinks[k]
                        f.write(str(kdisp) + ': ')
                        for x in v:
                            specindex = re.search(
                                r'--([\d_]+)\.', x.spec_fn
                            ).group(1)
                            f.write(specindex + ', ')
                        f.write('\n')
                    else:
                        f.write('    ')
                        kdisp = re.search(r'--.*$', k).group(0)
                        v = self.stslinks[k]
                        scnindex = re.search(r'--.*$', v.parent_fn).group(0)
                        f.write(str(kdisp))
                        f.write(': ')
                        f.write(scnindex)
                        f.write(' ')
                        f.write(str(v.dir))
                        f.write('\n')
            except Exception:
                pass
            # END try
            f.write(self.log.getvalue())
            f.close()
        # END if
        self.log.close()
    # END __init__
    
    def _init_readblock(self, f, axch_pass=False):
        '''__init__ subroutine for reading blocks
        
        The following blocks will be ignored:
            META: file meta data
            EXPD: some unknown experiement files
            INCI: marks anytime the instrument recording state changes from
                  the user pressing the play, stop, pause, or restart buttons
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
        t = struct.unpack('<I', f.read(4))[0]
        # unknown bytes; seems to be 0 on everything but INCI where it is 1
        unbytes = struct.unpack('<I', f.read(4))[0]
        tobj = datetime.fromtimestamp(t)
        self._t_bk = t
        bkbuff = MatrixBuffer(f, bklen)
        
        # Subroutines to parse the data in the different types of blocks
        if not axch_pass:
            self.log.write(
                '{:%H:%M:%S} x{:04x} {}'.format(tobj, unbytes, name)
            )
            if re.search(r'EEPA', name):
                self._init_read_EEPA(bkbuff)
            elif re.search(r'PMOD', name):
                self._init_read_PMOD(bkbuff)
            elif re.search(r'BREF', name):
                self._init_read_BREF(bkbuff)
            elif re.search(r'MARK', name):
                self._init_read_MARK(bkbuff)
            elif re.search(r'VIEW', name):
                self._init_read_VIEW(bkbuff)
            elif re.search(r'INCI', name):
                tl_entry = self.timeline.add(t, 'INCI')
                self._datafile_st[tl_entry] = dict(self._curr_st)
                self.log.write( '\n')
            else:
                self.log.write( '    {} bytes\n'.format(len(bkbuff)) )
            # END if
        elif axch_pass and re.search(r'CCSY', name):
            self._init_read_CCSY(bkbuff)
        # END if
        bkbuff.advance()
        if len(bkbuff)>0:
            raise RuntimeError(
                'buffer and file object out of sync' +
                '{} {}, {} left'.format(name, bklen, len(bkbuff))
            )
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
                prop, x = buff.next_mtrxparam()
                self.init_st[chnl+'_'+prop] = x
            # END for
        # END for
        
        self._curr_st = dict(self.init_st)
        self.log.write('\n')
    # END _init_read_EEPA
    
    def _init_read_PMOD(self, buff):
        '''A PMOD block contains a new setting for a single parameter.
        This subroutine will parse the block into current state dict.'''
        
        #skip empty space
        buff.next(4)
        
        chnl = buff.next_mtrxstr()
        prop, x = buff.next_mtrxparam()
        self.st_hist.append( (self._t_bk, chnl, prop, x) )
        self.timeline.add(self._t_bk, 'PMOD', chnl+'_'+prop, x)
        self._curr_st[chnl+'_'+prop] = x
        self.log.write(
            '    {0}_{1} <-- {2.value} {2.unit}\n'.format(chnl, prop, x)
        )
    # END _init_read_PMOD
    
    def _init_read_VIEW(self, buff):
        '''A VIEW block contains a new view setting'''
        self.log.write('\n')
        return
        #skip empty space
        buff.next(4)
        
        self.log.write('    ')
        buff.next(8)
        self.log.write('8B, ')
        buff.next(4)
        self.log.write('4B, ')
        n = buff.next_uint()
        self.log.write('{}, '.format(n))
        self.log.write(buff.next_mtrxstr()) #Z_Fw
        self.log.write(', ')
        self.log.write(buff.next_mtrxstr()) #Z
        self.log.write(', ')
        self.log.write(buff.next_uint()) #6
        self.log.write(', ')
        self.log.write(buff.next_mtrxstr()) #LineSlopeSubtractor
        self.log.write(', ')
        #self.log.write(buff.next_mtrxstr()) #Despiker
        #self.log.write(', ')
        self.log.write(repr(str(buff)))
        #self.log.write(buff.next_uint()) #18?
        #self.log.write(', ')
        #self.log.write(buff.next_mtrxstr()) #LineDifferentiator \n Statistics?
        #self.log.write(', ')
        #self.log.write(repr(str(buff)))
        #chnl = buff.next_mtrxstr()
        #prop, x = buff.next_mtrxparam()
        #self.st_hist.append( (self._t_bk, chnl, prop, x) )
        #self._curr_st[chnl+'_'+prop] = x
        #self.log.write(
        #    '    {0}_{1} <-- {2.value} {2.unit}\n'.format(chnl, prop, x)
        #)
        self.log.write('\n')
    # END _init_read_PMOD
    
    def _init_read_BREF(self, buff):
        '''A BREF ("Bricklet REFerence") block will mark a data file saving
        event.  This subroutine will parse the block ...'''
        #skip empty space
        buff.next(4)
        fname = buff.next_mtrxstr()
        # freeze a copy of the current settings and register it
        tl_entry = self.timeline.add(self._t_bk, 'BREF', fname)
        self._datafile_st[fname] = dict(self._curr_st)
        self._datafile_st[tl_entry] = self._datafile_st[fname]
        
        # manage point-spectra linkage
        img_mat = re.search(r'\.([^()]+)_mtrx$', fname)
        # this is to make sure spectra such as I(t) are not incorrectly treated
        # as linked point spectra
        pointsts_mat = re.search(r'\.(.*?\(.+?\))_mtrx$', fname)
        if img_mat:
            # file is scan data
            img_chnl_name = img_mat.group(1)
            self.unlinked_spectra.append(None)
            while self.unlinked_spectra[0] is not None:
                mrk = self.unlinked_spectra.pop(0)
                if not mrk.parent_hash:
                    # the spectrum is either a repeat or a from a non-specific
                    # point
                    first_name = re.sub(
                        r'(\d+_)\d+(\.[^.]+$)', '\g<1>1\g<2>', mrk.spec_fn
                    )
                    if mrk.spec_fn != first_name:
                        # copy over mark for following spectra
                        try:
                            new_mrk = copy(self.stslinks[first_name])
                            new_mrk.spec_fn = mrk.spec_fn
                            self.unlinked_spectra.insert(0, new_mrk)
                        except KeyError :
                            # this is a "free-range" spectra
                            # e.g. an I(t) spectra
                            self.free_spectra.append(mrk.spec_fn)
                    # END if
                    continue
                # END if
                #try:
                sts_parent_ax = self.axch[mrk.parent_hash].depn_ax
                #except KeyError as err:
                #    self.unlinked_spectra.append( (mrk.spec_fn, mrk) )
                #    continue
                # END try
                if sts_parent_ax.name != img_chnl_name:
                    # this spectra was clicked in a different channel window
                    # e.g. user clicked in I window instead of Z
                    self.unlinked_spectra.append(mrk)
                # END if
                # update the scan --> spec lookup
                mrk.parent_fn = fname
                if fname not in self.stslinks:
                    self.stslinks[fname] = [mrk,]
                else:
                    self.stslinks[fname].append(mrk)
                # END if
                self.stslinks[mrk.spec_fn] = mrk
            # END while
            self.unlinked_spectra.pop(0)
            
            self.cmnt_lkup[fname] = []
            if img_chnl_name in self.cmnt_lkup:
                for _ in range(len(self.cmnt_lkup[img_chnl_name])):
                    self.cmnt_lkup[fname].append(
                        self.cmnt_lkup[img_chnl_name].pop(0)
                    )
                # END for
            # END if
        elif pointsts_mat:
            # file is for spectroscopy data
            chnl_name = pointsts_mat.group(1)
            # collect all comments on the data object
            self.cmnt_lkup[fname] = []
            if chnl_name in self.cmnt_lkup:
                for _ in range(len(self.cmnt_lkup[chnl_name])):
                    self.cmnt_lkup[fname].append(
                        self.cmnt_lkup[chnl_name].pop(0)
                    )
                # END for
            # END if
            # register the spectra as unlinked
            if re.search(r'\([tr]\)', chnl_name):
                self.unlinked_spectra.append( STSMark(spec_fn=fname) )
            else:
                self.last_sts_mark.spec_fn = fname
                self.unlinked_spectra.append(copy(self.last_sts_mark))
            # END if
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
        if re.search(r'Instrument information', markstr):
            self.inst_info = re.sub(r'^.*?: ', '', markstr)
        elif re.search(r'^MTRX\$STS_LOCATION', markstr):
            self.timeline.add(self._t_bk, 'MARK', markstr)
            # Example:
            # MTRX$STS_LOCATION-192,94;7e-009,-9.33333e-009%%7800440043-1-4-0%%
            # Breakdown of mark:
            # MTRX$STS_LOCATION-192,94;______,_____________%%__________-_-_-_%%
            # pixel coordinates ***,**
            # MTRX$STS_LOCATION-___,__;7e-009,-9.33333e-009%%__________-_-_-_%%
            #     physical coordinates ******,*************
            # MTRX$STS_LOCATION-___,__;______,_____________%%7800440043-_-_-_%%
            #                            parent channel hash **********
            # MTRX$STS_LOCATION-___,__;______,_____________%%__________-1-4-_%%
            #                                          unknown indicies * *
            # MTRX$STS_LOCATION-___,__;______,_____________%%__________-_-_-0%%
            #                                               direction index *
            locstr, img_chnl_hash, _, _, d = re.search(
                r'^MTRX\$STS_LOCATION-(.+?)%%([a-fA-F\d]+)-(\d+)-(\d+)-(\d+)',
                markstr
            ).groups()
            img_chnl_hash = int(img_chnl_hash, 16)
            self.last_sts_mark = STSMark(
                parent_hash=img_chnl_hash, dir=int(d), loc=locstr
            )
        elif re.search(r'MTRX\$SAMPLE_NAME', markstr):
            self.sample = re.search(r'-(.*)$', markstr).group(1)
        elif re.search(r'MTRX\$DATA_SET_NAME', markstr):
            self.data_set = re.search(r'-(.*)$', markstr).group(1)
        elif re.search(r'MTRX\$CREATION_COMMENT', markstr):
            self.comment = re.search(r'(?<=COMMENT-).*', markstr).group(0)
        elif re.search(r'MTRX\$IMAGE_COMMENT', markstr):
            # Example:
            # "MTRX$IMAGE_COMMENT-Z.-493925695555-2-0-2%this is only a test"
            # "MTRX$IMAGE_COMMENT-I(V).-47249096771-1-0--1%added -2.6 V offset manually"
            # NOTE: d may be correct
            chnl_key, d, comment = re.search(
                r'COMMENT.+?(\d+).+?\d+.+?\d+.+?(\d+)%(.*)', markstr, re.DOTALL
            ).groups()
            d = int(d)
            chnl_key = int(chnl_key)
            depn_ax = self.axch[chnl_key].depn_ax
            self.log.write(
                '    {} --> {}\n'.format( chnl_key, 
                                          self.axch[chnl_key].descrip
                                        )
            )
            if depn_ax.name in self.cmnt_lkup:
                self.cmnt_lkup[depn_ax.name].append( (d, comment) )
            else:
                self.cmnt_lkup[depn_ax.name] = [(d, comment),]
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
    
    # Magic Methods
    #--------------
    def __contains__(self, item):
        try:
            item  = os.path.basename(item.prop['file'])
        except AttributeError:
            try:
                item  = os.path.basename(item)
            except TypeError:
                raise TypeError(
                    'Experiment.__contains__ accepts only str-, CurveData-, or ScanData-like objects'
                )
            # END try
        # END try
        return item in self._datafile_st
    # END __contains__
    
    def __str__(self): return self.fp
    
    # Object data import methods
    #---------------------------
    def import_scan( self, file_path, scan_only=False, debug=False
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
        
        return import_scan(
            file_path, scan_only=scan_only, ex=self, debug=debug
        )
    # END import_scan
    
    def import_spectra(self, file_path, debug=False):
        '''Read a spectroscopy data file and return CurveData objects
        
        Args:
            file_path (str): path to .*_mtrx scan data file
            debug (bool): switch for writing a debugging file describing
                          how the data file was interpreted
        Returns:
            (list) [CurveData, CurveData, ...]
        '''
        
        return import_spectra(file_path, ex=self, debug=debug)
    # END import_spectra
    
    # Object information methods
    #---------------------------
    def get_data_filenames(self):
        return [ x for x in self._datafile_st.keys()
                  if isinstance(x, basestring)
                ]
    # END get_data_filenames
    
    def get_params(self, file_name):
        '''
        '''
        params = dict( self._datafile_st[file_name] )
        
        # retrieve all image comments
        comments = sorted(self.cmnt_lkup[file_name], key=lambda tup: tup[0])
        # TODO: correct this, it is a temporary soution
        #       comments should be attached to the specific direction they
        #       go with
        all_cmnt = '\n'.join([c for _, c in comments])
        params['comment'] = all_cmnt
        
        return params
    # END get_params
    
    def transfer_params(self, data_obj):
        fn = data_obj.props['file']
        for k in self._datafile_st[fn]:
            data_obj.props[k] = self._datafile_st[fn][k]
        
        # retrieve all image comments
        comments = sorted(self.cmnt_lkup[fn], key=lambda tup: tup[0])
        # TODO: correct this, it is a temporary soution
        #       comments should be attached to the specific direction they
        #       go with
        all_cmnt = '\n'.join([c for _, c in comments])
        data_obj.props['comment'] = all_cmnt
    # END transfer_params
    
    def get_pmods(self, file_name, t, N_points, slow_ax, fast_ax):
        fparams = self._datafile_st[file_name]
        #i_bref, _ = self.timeline.bisect(t)
        i_bref = self.timeline.find_bref(t, file_name)[0]
        i_prev = i_bref - 1
        # If stop/restart was pressed then there will be an INCI entry
        # just before the BREF entry with the same timestamp;
        # skip over this INCI, if it exists
        try:
            while self.timeline[i_prev].t == self.timeline[i_bref].t:
                i_prev -= 1
        except IndexError as err:
            print '0'
            print i_prev
            print i_bref
            print len(self.timeline)
            raise err
        # The preceding INCI or BREF will mark the beginning of the scanning,
        # but all BREFs from point spectra need to be skipped
        similar_fname = re.search(r'--\d+_\d+\.', file_name).group(0)
        while 0 <= i_prev:
            if re.search(r'INCI', self.timeline[i_prev].bknm):
                break
            elif ( re.search(r'BREF', self.timeline[i_prev].bknm) and
                   re.search(r'\.\w+_mtrx$', self.timeline[i_prev].data[0]) and
                   not re.search(similar_fname, self.timeline[i_prev].data[0])
                  ):
                    break
            else:
                i_prev -= 1
        # END while
        # i_prev is now the index of a timeline entry with a timestamp that
        # is equal to the time the data acquisition started
        t_start = self.timeline[i_prev].t
        init_params = self._datafile_st[self.timeline[i_prev]]
        
        # check for changes in raster time or point spectra
        steady = True
        for x in self.timeline[i_prev+1:i_bref]:
            try:
                if re.search( r'XYScanner.*?Raster_Time|STS_LOCATION',
                              x.data[0] ):
                    steady = False
                    #print '    dynamic point: {}'.format(x)
                    break
                # END if
            except IndexError:
                pass
            # END try
        # END for
        
        # remove all timeline entries that are not PMODs
        scn_tl = self.timeline[i_prev+1:i_bref].filter('PMOD')
        
        # pmods will be the return value
        # pmods should be the same shape as the return of import_scan
        pmods = [[]]
        if slow_ax.mirrored: pmods.append([])
        
        if steady:
            # calculate the half-way point in time, and split the timeline
            # at that point
            t_half = ( fparams['XYScanner_Points'].value *
                       fparams['XYScanner_Raster_Time'].value +
                       fparams['XYScanner_Move_Raster_Time'].value
                     ) * fparams['XYScanner_Lines'].value
            if fast_ax.mirrored: t_half *= 2
            t_half += self.timeline[i_prev].t
            scn_tl_pieces = scn_tl.split(t_half)
            for i in range(len(pmods)):
                pmods[i] = [ (x.t-t_start, x.data[0], x.data[1])
                             for x in scn_tl_pieces[i]
                           ]
            # END for
        else:
            #print 'WARNING: Dynamic scan encountered: ...{}'.format(
            #    file_name[-18:]
            #)
            for i in range(len(pmods)):
                pmods[i] = [ (x.t-t_start, x.data[0], x.data[1])
                             for x in scn_tl
                           ]
        # END if
        
        return pmods
        
    # END get_pmods
    
    def get_state(self, fn):
        if isinstance(fn, basestring):
            return self._datafile_st[fn]
        else:
            raise TypeError('File name argument must be str')
        # END if
    # END get_state
# END Experiment

#==============================================================================
def import_scan( file_path,
                 scan_only=False,
                 ex=None, mirroring=(True, True),
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
    if debug:
        fdebug = open(file_name + '-debug.txt', 'w')
    else:
        fdebug = None
    # END if
    filebuff, _, t = MatrixBuffer.from_file(file_path)
    
    if fdebug: fdebug.write(datetime.now().ctime(t)+'\n')
    
    # Skip empty space
    filebuff.advance(4)
    if fdebug: fdebug.write('empty 4B\n')
    # Read blocks
    while filebuff:
        bkbuff, bkname = filebuff.next_bk()
        if fdebug: fdebug.write( '{} {}B\n'.format(bkname, len(bkbuff)) )
        if re.search(r'DESC', bkname):
            chnl_key, Npnt_set, Npnt_act, _ = _read_DESC(bkbuff, fdebug)
            # check for a link to an existing Experiment object
            # or make up false axes
            try:
                depn_ax = ex.axch[chnl_key].depn_ax
                fast_ax = depn_ax.indp_ax
                slow_ax = fast_ax.next_ax
            except AttributeError:
                Nimg = 1
                if mirroring[0]: Nimg *= 2
                if mirroring[1]: Nimg *= 2
                slow_len = int( np.sqrt(float(Npnt_set)/Nimg) )
                fast_len = int(slow_len)
                if mirroring[0]: slow_len *= 2
                if mirroring[1]: fast_len *= 2
                slow_ax = IndependentAxis(
                    None, qual_name='Y', mirrored=mirroring[0], len=slow_len, next_ax=None
                )
                fast_ax = IndependentAxis(
                    None, qual_name='X', mirrored=mirroring[1], len=fast_len, next_ax=slow_ax
                )
                depn_ax = DependentAxis(
                    None,
                    name=re.search(r'[^._]+(?=_mtrx$)', file_name).group(0),
                    unit='',
                    trans_func=TransferFunction('TFF_Identity', ''),
                    indp_ax=fast_ax
                )
            # END try
        elif re.search(r'DATA', bkname):
            scans = _read_DATA_scan(bkbuff, depn_ax)
        # END if
        # Heuristic to force the file closed after the data block
        bkbuff.advance()
    # END while
    filebuff.close()
    
    if fdebug: fdebug.close()
    
    # Create parameters dictionary
    try:
        # make param dict from Experiment object
        params = ex.get_params(file_name)
    except (AttributeError, KeyError):
        # make an incomplete param dict from available information
        params = {}
    # END try
    params['file'] = file_name
    # pull index and repetition values from file_name
    index_str, rep_str = re.search(r'--(\d+)_(\d+)\.', file_name).groups()
    params['index'] = int(index_str)
    params['rep'] = int(rep_str)
    params['channel'] = depn_ax.name
    params['time'] = t
        
    # Calculate how long it took to take the scan
    fast_ax = depn_ax.indp_ax
    try:
        mods = ex.get_pmods(file_name, t, Npnt_act, slow_ax, fast_ax)
    except RuntimeError as err:
        mods = [[], []]
        print err
        print '  on "{}"'.format(file_name)
    #try:
    #    #print file_name
    #    #print 'saved at {:%H:%M:%S}'.format(datetime.fromtimestamp(t))
    #    #print ''
    #    #for m in mods:
    #    #    for tpmod, pname, x in m:
    #    #        print '    +{:%M:%S} | {} <-- {} {}'.format(
    #    #            datetime.fromtimestamp(tpmod), pname, x.value, x.unit
    #    #        )
    #    #    print ''
    #except KeyError as err:
    #    print 'KeyError in pyMTRX.import_scan: ex= {!s}'.format(ex)
    #    print err
    ## END try
    
    # create X & Y axes
    try:
        # X & Y offset specify where the center of the map is
        N = params['XYScanner_Points'].value
        a = -1*(N-1)/2.0
        b = -1*a
        dx = float(params['XYScanner_Width'].value) / (N-1)
        X_ax = params['XYScanner_X_Offset'].value + np.linspace(a, b, N)*dx
        N = params['XYScanner_Lines'].value
        a = -1*(N-1)/2.0
        b = -1*a
        dy = float(params['XYScanner_Height'].value) / (N-1)
        Y_ax = params['XYScanner_Y_Offset'].value + np.linspace(a, b, N)*dy
    except KeyError:
        X_ax = np.arange(float(fast_ax.len))
        Y_ax = np.arange(float(slow_ax.len))
    # END try
    
    # Create tree of ScanData objects
    scans_flat = []
    for i in range(len(scans)):
        for j in range(len(scans[i])):
            params['direction'] = 2*i + j
            params['pmods'] = mods[i]
            scans[i][j] = ScanData( X_ax, Y_ax, scans[i][j], params)
            if not (ex is None): scans[i][j].ex = ex
            scans[i][j].spectra = []
            scans_flat.append(scans[i][j])
        # END for
    # END for
    
    # return prematurely and skip attachment of linked spectra
    if scan_only or ex is None: return scans
        
    # import any linked spectra and attach them in the .spectra attribute
    # stslinks[fname] = [(mrk, spectra_fname), (mrk, spectra_fname), ...]
    # mrk = ('ii', 'i', 'd', 'xpx,ypx;xpy,ypy', chnl_name)
    file_sts_links = []
    if file_name in ex.stslinks:
        file_sts_links = ex.stslinks[file_name]
    for mrk in file_sts_links:
        try:
            crvs = ex.import_spectra( os.path.join(file_dir, mrk.spec_fn) )
            scans_flat[mrk.dir].spectra.extend(crvs)
            for x in crvs: x.parent = scans_flat[mrk.dir]
        except IOError:
            pass
        # END try
    # END for 
    
    return scans
# END import_scan
    
def _read_DESC(buff, fdebug=None):
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
    
def _read_DATA_scan(bkbuff, depn_ax):
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
    
def import_spectra(file_path, ex=None, mirroring=False, debug=False):
    '''Read a spectroscopy data file and return CurveData objects
    
    Args:
        file_path (str): standard full path
    Returns:
        (list) [CurveData, CurveData, ...]
    '''
    
    file_name = os.path.basename(file_path)
    if debug:
        fdebug = open(file_name + '-debug.txt', 'w')
    else:
        fdebug = None
    # END if
    
    filebuff, _, t = MatrixBuffer.from_file(file_path)
    
    # Skip empty space
    filebuff.next(4)
    # Read sub-blocks (DESC & DATA)
    while filebuff:
        bkbuff, bkname = filebuff.next_bk()
        if fdebug: fdebug.write( '{} {}B\n'.format(bkname, len(bkbuff)) )
        if re.search(r'DESC', bkname):
            chnl_key, Npnt_set, Npnt_act, _ = _read_DESC(bkbuff, fdebug)
            # check for a link to an existing Experiment object
            # or make up false axes
            try:
                depn_ax = ex.axch[chnl_key].depn_ax
                indp_ax = depn_ax.indp_ax
            except AttributeError:
                Ncrv = 1
                if mirroring: Ncrv *= 2
                indp_len = Npnt_set / Ncrv
                ynm, xnm = re.search(
                    r'([^._()]+)\((\w)\)(?=_mtrx$)', file_name
                ).groups()
                indp_ax = IndependentAxis(
                    None, qual_name=xnm, mirrored=mirroring, len=indp_len, next_ax=None
                )
                depn_ax = DependentAxis(
                    None, name=ynm, unit='',
                    trans_func=TransferFunction('TFF_Identity', ''),
                    indp_ax=indp_ax
                )
            # END try
        elif re.search(r'DATA', bkname):
            all_Ys = _read_DATA_spectra(bkbuff, depn_ax)
        # END if
        # Heuristic to force the file closed after the data block
        bkbuff.advance()
    # END while
    filebuff.close()
    
    if fdebug: fdebug.close()
    
    # Create parameters dictionary
    try:
        # make param dict from Experiment object
        params = ex.get_params(file_name)
        
        if file_name in ex.stslinks:
            params['parent'] = ex.stslinks[file_name].parent_fn
        else:
            params['parent'] = ''
        
        try:
            # Example locstr:
            #  "-193,205;7.16667e-009,9.16667e-009"
            # pixel coordinates are relative to bottom left corner
            # physical coordinates are relative to scan center
            coords = re.split(r';|,', ex.stslinks[file_name].loc)
            params['coord_px'] = ( int(coords[0]), int(coords[1]) )
            params['coord_phys'] = ( float(coords[2]), float(coords[3]) )
        except Exception:
            pass
        # END try
    except (AttributeError, KeyError) as err:
        # make an incomplete param dict from available information
        params = {'parent': '',}
    # END try
    params['file'] = file_name
    # pull index and repetition values from file_name
    index_str, rep_str = re.search(r'--(\d+)_(\d+)\.', file_name).groups()
    params['index'] = int(index_str)
    params['rep'] = int(rep_str)
    params['channel'] = depn_ax.name
    params['time'] = t
    
    # make X array
    try:
        #if indp_ax.elem == 'Spectroscopy' and indp_ax.name == 'V':
        if indp_ax.qual_name[-1] == 'V':
            x0 = params['Spectroscopy_Device_1_Start'].value
            xf = params['Spectroscopy_Device_1_End'].value
            X = np.linspace(x0, xf, len(all_Ys[0]))
            x_units = params['Spectroscopy_Device_1_Start'].unit
        elif indp_ax.qual_name[-1] == 'Z':
            x0 = params['Spectroscopy_Device_2_Start'].value
            xf = params['Spectroscopy_Device_2_End'].value
            X = np.linspace(x0, xf, len(all_Ys[0]))
            x_units = params['Spectroscopy_Device_2_Start'].unit
        elif re.search('Clock2', indp_ax.qual_name):
            tstep = params['Clock2_Period'].value
            N = params['Clock2_Samples'].value
            X = (np.arange(N) + N*(params['rep'] - 1)) * tstep
            x_units = 's'
        else:
            raise ValueError(
                'Cannot parse independent axis {}'.format(indp_ax.__dict__)
            )
        # END if
    except KeyError:
        X = np.arange( float(len(all_Ys[0])) )
        x_units = ''
    # END try
    
    for i, Y in enumerate(all_Ys):
        params['direction'] = i
        all_Ys[i] = MTRXCurve(
            X, Y, x_units=x_units, y_units=depn_ax.unit,
            props=params
        )
        if not (ex is None): all_Ys[i].ex = ex
    # END for
    
    return all_Ys
# END import_spectra
    
def _read_DATA_spectra(buff, depn_ax):
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

#==============================================================================
class MTRXCurve(CurveData):
    '''CurveData sub-class with extra methods taylored for MTRX data'''
    
    @property
    def is_free(self): return not self.is_linked
    
    @property
    def is_linked(self): return self.props['file'] in self.ex.stslinks
    
    @property
    def mrk(self): return self.ex.stslinks[self.props['file']]
    
# END MTRXCurve

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
# END unwind_split

#=============================================================================
def file_name_values(fn):
    try:
        mats = re.search(r'--(\d+)_(\d+)\.([^.]+?)_mtrx$', fn).groups()
        return (int(mats[0]), int(mats[1]), mats[2])
    except AttributeError:
        raise ValueError('file name does not conform to MATRIX convention')
# END file_name_values

#==============================================================================
TimelineEntry = namedtuple('TimelineEntry', ['t', 'bknm', 'data'])

class Timeline(object):
    '''Sorted list of TimelineEntry objects
    '''
    
    def __init__(self, tl=None):
        if tl is None: self._tl = []
        else: self._tl = list(tl)
    # END __init__
    
    def __call__(self, t):
        if self._tl[-1].t <= t:
            return self._tl[-1:]
        elif t < self._tl[0].t:
            return self._tl[:0]
        else:
            i, j = self.bisect(t)
            return self._tl[i:j]
        # END if
    # END __call__
    
    def __getitem__(self, i):
        if isinstance(i, slice):
            return Timeline(self._tl[i])
        return self._tl[i]
    # END __getitem__
    
    def __iter__(self):
        for x in self._tl: yield x
    # END __iter__
    
    def __len__(self): return len(self._tl)
    
    def add(self, t, bknm, *data):
        new_entry = TimelineEntry(t, bknm, data)
        if len(self._tl) == 0:
            self._tl.append(new_entry)
        else:
            self._tl.insert( self.bisect(t)[-1], new_entry)
        # END if
        return new_entry
    # END add
    
    def bisect(self, t):
        if self._tl[-1].t <= t:
            return len(self._tl)-1, len(self._tl)
        elif t < self._tl[0].t:
            return None, 0
        else:
            i = 0
            j = len(self._tl)
            while i + 1 < j:
                k = int((i+j)/2)
                if t < self._tl[k].t: j = k
                else: i = k
            # END while
            # t is now bound...
            # self._tl[i].t <= t < self._tl[i+1].t
            return i, i+1
    # END bisect
    
    def filter(self, bknm_ptn):
        return Timeline(
            [x for x in self._tl if re.search(bknm_ptn, x.bknm)]
        )
    # END filter
    
    def find_bref(self, t, file_name):
        '''Some entries have the same time value, this method will search
            by time first then by file_name for a more exact result
        '''
        i = self.bisect(t)[1]
        if i is None:
            raise ValueError('No TimelineEntry with matching time value')
        
        for i in range(i+1)[::-1]:
            if self[i].bknm == 'BREF':
                if self[i].data[0] == file_name:
                    break
        # END for
        
        return i, self[i]
    # END find_bref
    
    def pop(self, i): return self._tl.pop(i)
    
    def split(self, t):
        if len(self._tl) == 0:
            return Timeline(), Timeline()
        # END if
        y = self.bisect(t)
        return self[:y[-1]], self[y[-1]:]
    # END split
        
# END Timeline

#==============================================================================
class InstrChannel(object):
    def __init__(self, mtrx_hash_value, descrip='', depn_ax=None):
        self.descrip = descrip
        self.depn_ax = depn_ax
        self._mtrx_hash_value = mtrx_hash_value
    # END __init__
    
    def __hash__(self): return self._mtrx_hash_value
    
    def __str__(self):
        return '<InstrChannel @ MTRX {}>'.format(self._mtrx_hash_value)
    
    def __repr__(self):
        return self.__str__()
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
        return '<DependentAxis @ MTRX {}>'.format(self._mtrx_hash_value)
    
    def __repr__(self):
        return self.__str__()
    # END __str__
# END DependentAxis

#==============================================================================
class IndependentAxis(object):
    def __init__( self, mtrx_hash_value, qual_name='', mirrored=False,
                  len=0, next_ax=None
                ):
        self._mtrx_hash_value = mtrx_hash_value
        self.qual_name = qual_name
        #self.instr, self.elem, self.name = qual_name.split('::')
        self.mirrored = mirrored
        self.len = len
        self.next_ax = next_ax
    # END __init__
    
    def __hash__(self): return self._mtrx_hash_value
    
    def __len__(self): return self.len
    
    def __str__(self):
        return '<IndependentAxis @ MTRX {}>'.format(self._mtrx_hash_value)
    
    def __repr__(self):
        return self.__str__()
# END IndependentAxis

#==============================================================================
class STSMark(object):
    def __init__( self, spec_fn='', parent_fn='', parent_hash=0,
                  dir=0, loc=''
                ):
        self.spec_fn = spec_fn
        self.parent_fn = parent_fn
        self.parent_hash = parent_hash
        self.dir = dir
        self.loc = loc
    # END __init__
    
    def __str__(self):
        return '[{} {:02b} {:>012d} <-- {}]'.format(
            self.parent_fn[-18:], self.dir, self.parent_hash,
            self.spec_fn[-18:]
        )
    # END __str__
# END STSMark

#==============================================================================
PhysicalValue = namedtuple('PhysicalValue', ['value', 'unit'])

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
            raise RuntimeError(
                'MatrixBuffer over-read: ' +
                'self._N = {}, self._i = {}'.format(self._N, self._i)
            )
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
    
    def next_mtrxparam(self):
        prop = self.next_mtrxstr()
        unit = self.next_mtrxstr()
        #skip empty space
        self.next(4)
        value = self.next_mtrxtype()
        
        return prop, PhysicalValue(value, unit)
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

#==============================================================================
def size_change(scn):
    for _, pname, _ in scn.props['pmods']:
        if re.search(r'XYScanner_Width|XYScanner_Height', pname):
            return True
    
    return False
# END size_change


