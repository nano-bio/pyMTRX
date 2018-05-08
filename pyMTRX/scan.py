# -*- encoding: utf-8 -*-
'''Scanning Probe Microscopy Analysis Module (version 2)
    
    List of classes:
        ScanData
'''

# built-in modules
import re
import struct

# third-party modules
import numpy as np
from PIL import Image
#import png
#import matplotlib.colors as mplcolors
#import matplotlib as mpl


#==============================================================================
class ScanData(object):
    '''2-D Scanned Data
    
    Class Methods:
        copy
        import_spip_ascii
        max
        min
        median
        mean_std
        global_leveled
        linewise_leveled
    Instantiation Args:
        chnl_files (dict): file names keyed with channel names
    Instance Attributes:
        X_ax, Y_ax (ndarray): X/Y axis points
        Z (ndarray): 2-D array of Z points
        props (dict): header parameter values, keyed by parameter name
        shape (tup): equivalent to .Z.shape
    Instance Methods:
        save_ascii
        save_png
        global_level
        linewise_level
    '''
    # TODO list:
    #   add arimetic operations
    #   add rotation
    
    def __init__(self, X_ax, Y_ax, Z, props={}):
        self.X_ax = np.array(X_ax)
        self.Y_ax = np.array(Y_ax)
        self.Z = np.array(Z)
        self.props = dict(props)
        
        # make private master copies of the originals
        self._X_ax = np.array(self.X_ax)
        self._Y_ax = np.array(self.Y_ax)
        self._XX, self._YY = np.meshgrid(self.X_ax, self.Y_ax[::-1])
        self._props = dict(self.props)
    # END __init__
    
    # Class methods for object creation
    #----------------------------------
    @classmethod
    def copy(cls, scn):
        return cls(scn.X_ax, scn.Y_ax, scn.Z, scn.props)
    # END copy
    
    # TODO: move to importers sub-package
    @classmethod
    def import_spip_ascii(cls, file_name):
        '''Create a new ScanData object from a ASCII text file exported by SPIP
        '''
        
        f = open(file_name)
        # collect all header data into 'props dict'
        props = {}
        subheading = ''
        for ln in f:
            if ln[0] == '#':
                header_mat = re.search(r'^# ([^=]+?) = ([^\n]+)[\r\n]+$', ln)
                if not header_mat: continue
                try:
                    value = int(header_mat.group(2))
                except:
                    try:
                        value = float(header_mat.group(2))
                    except:
                        value = header_mat.group(2)
                    # END try
                # END try
                props[header_mat.group(1)] = value
            elif ln[:6] == '.  .  ':
                header_mat = re.search(
                    r'^\.  \.  ([^ ]+) = ([^ ]+) ([^\n]+)[\r\n]+$', ln
                )
                ln_data = list(header_mat.groups())
                if ln_data[1][0] == '"':
                    ln_data[1] = ln_data[1].strip('"')
                else:
                    try:
                        ln_data[1] = int(ln_data[1])
                    except:
                        ln_data[1] = float(ln_data[1])
                    # END try
                # END if
                props[subheading+ln_data[0]] = (ln_data[1], ln_data[2])
            elif ln[:3] == '.  ':
                header_mat = re.search(r'^\.  ([^ ]+:)[\r\n]+$', ln)
                subheading = header_mat.group(1)
            else:
                break
            # END if
        # END for
        
        # Set up XY mesh
        N = props['x-pixels']
        a = -1*(N-1)/2.0
        b = -1*a
        dx = float(props['x-length']) / (props['x-pixels']-1)
        X_ax = props['x-offset'] + np.linspace(a, b, N)*dx
        dy = float(props['y-length']) / (props['y-pixels']-1)
        Y_ax = props['y-offset'] + np.linspace(a, b, N)*dy
        
        # Record channel data
        Z_mtx = []
        for ln in f:
            # Skip lines that don't begin with a number
            if not re.search(r'[+\-\d]', ln[0]): continue
            
            ln_data = re.split(r'\s+', re.sub(r'^\s+|\s+$', '', ln))
            for i in range(len(ln_data)):
                ln_data[i] = float(ln_data[i])
            Z_mtx.append(ln_data)
        # END for
        f.close()
        
        return cls(X_ax, Y_ax, Z_mtrx, props)
    # END import_spip_ascii
    
    # Property descriptor functions
    #------------------------------
    @property
    def shape(self):
        return self.Z.shape
    # END shape
    
    # Object methods: I/O
    #--------------------
    # TODO: move to exporters sub-package
    def save_ascii(self, save_name):
        with open(save_name, 'w') as f:
            f.write('# File Format = ASCII\n')
            f.write('# Created by Python\n')
            for p in sorted(self.props.keys()):
                f.write('# {} = {}\n'.format(p, self.props[p]))
            # END for
            f.write('\n')
            f.write('# Start of Data:\n')
            N_rows, N_cols = self.Z.shape
            for i_row in range(N_rows):
                for i_col in range(N_cols):
                    f.write('{:0.8e}  '.format(self.Z[i_row,i_col]))
                # END for
                f.write('\n')
            # END for
        # END with
    # END save_ascii
    
    # TODO: move to exporters sub-package
    def save_png(self, save_name):
        '''Save data as image file: PNG
        
        *for now this will only save in gray-scale, covering the full range
        TODO: add color mapping
        '''
        
        imgdata = np.zeros(self.shape, dtype='uint32')
        zlst = np.sort( np.ravel(self.Z) )
        z_min = zlst[len(zlst)*25/1000]
        z_max = zlst[len(zlst)*975/1000]
        for i in range(self.Z.shape[0]):
            for j in range(self.Z.shape[1]):
                ynorm = (self.Z[i,j]-z_min) / (z_max-z_min)
                if ynorm > 1:
                    ynorm = 1
                elif ynorm < 0:
                    ynorm = 0
                # END if
                imgdata[i,j] = int(255*ynorm)
            # END for
        # END for
        
        imgdata = imgdata.flatten()
        bytes = struct.pack( ' '.join(len(imgdata)*['B']), *imgdata )
        #pngwriter = png.Writer(size=self.Z.shape, greyscale=True)
        with open(save_name, 'wb') as f:
            Image.frombytes('L', self.Z.shape, bytes).save(
                f, format='png'
            )
            #pngwriter.write(f, imgdata)
        # END with
    # END save_png
    
    # Object methods: manipulation
    #-----------------------------
    def global_level(self, method='plane', plane=None):
        '''Level the scan channel using a global adjustment
        
        Possible methods: average profile, polynomial fit
        '''
        
        XX = self._XX
        YY = self._YY
        Z = self.Z
        if plane is None:
            A = np.ones((self.shape[0]*self.shape[1], 3))
            B = np.zeros((self.shape[0]*self.shape[1], 1))
            n = 0
            for i in range(self.shape[1]):
                for j in range(self.shape[0]):
                    A[n,0] = self._XX[i,j]
                    A[n,1] = self._YY[i,j]
                    B[n,0] = self.Z[i,j]
                    n += 1
                # END for
            # END for
            c = np.linalg.lstsq(A, B)[0]
        else:
            c = plane
        # END if
        for i in range(self.shape[1]):
            for j in range(self.shape[0]):
                self.Z[i,j] = (
                    self.Z[i,j]
                    - c[0]*self._XX[i,j] - c[1]*self._YY[i,j] - c[2]
                )
            # END for
        # END for
        
        return c
    # END global_level
    
    def linewise_level(self, poly_order=0):
        '''Level the scan channel using a line-by-line adjustments
        '''
        
        for i in range(self.shape[1]):
            Xi = np.array( list(range(len(self.Z[i,:]))) )
            self.Z[i,:] = (
                self.Z[i,:]
                - np.polyval(np.polyfit(Xi, self.Z[i,:], poly_order), Xi)
            )
        # END for
    # END linewise_level
    
    # Class methods: analysis
    #-------------------------
    @classmethod
    def max(cls, scn):
        return max( np.ravel(scn.Z) )
    # END max
    
    @classmethod
    def min(cls, scn):
        return min( np.ravel(scn.Z) )
    # END min
    
    @classmethod
    def median(cls, scn):
        Z_lst = np.ravel(scn.Z)
        Z_lst.sort()
        ihalf = len(Z_lst)/2.0
        if ihalf == int(ihalf):
            # even-length array, interpolate midpoint value
            ihalf = int(ihalf)
            mdn = 0.5 * ( Z_lst[ihalf] + Z_lst[ihalf+1] )
        else:
            # odd-length array, use middle value
            mdn = Z_lst[int(ihalf)]
        # END if
        
        return mdn
    # END median
    
    @classmethod
    def mean_std(cls, scn):
        N = 0
        S = 0
        S_sqr = 0
        Z_lst = np.sort( np.ravel(scn.Z) )
        for x in Z_lst:
            N += 1
            S += x
            S_sqr += x**2
        # END for
        
        mean = S/N
        stdev = np.sqrt( S_sqr/N - (S/N)**2 )
        return mean, stdev
    # END mean_std
    
    # Class methods: manipulation
    #-----------------------------
    @classmethod
    def global_leveled(cls, scn, *args, **kwargs):
        '''Level the scan channel using a global adjustment
        
        Possible methods: average profile, polynomial fit
        '''
        
        new_scn = ScanData.copy(scn)
        new_scan.global_level(*args, **kwargs)
        return new_scn
    # END global_level
    
    @classmethod
    def linewise_leveled(cls, scn, *args, **kwargs):
        '''Level the scan channel using a line-by-line adjustments
        '''
        
        new_scn = ScanData.copy(scn)
        new_scan.linewise_level(*args, **kwargs)
        return new_scn
    # END linewise_level
# END ScanData