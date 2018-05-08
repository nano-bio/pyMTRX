# -*- encoding: UTF-8 -*-
'''CurveData class
    
    Documentation needed
    TODO: make differentiators/smoothers add item to props with parameters
    used
    
    List of classes:
        CurveData
        CurveDataError
'''

# built-in modules
import re
import time

# third-party modules
import numpy as np

# internal modules
from . import numerical as num

#===============================================================================
class CurveData(object):
    '''Data Class for 2-D curves of physical values
    
    [TODO: add description]
    
    Class Methods:
        copy
        deriv_sg
        deriv_cdiff
        domain_match
        nn_smooth
        norm_deriv
        save
    Instantiation Args:
        X, Y, x_units='', y_units='', props={}
    Instance Attributes:
        X (numpy.ndarray): a copy of the input sequence X
        x_units (str): name of X units
        Y (numpy.ndarray): a copy of the input sequence Y
        y_units (str): name of Y units
        units (tup): (x_units, y_units)
    Supported Operations:
        +, -, /, *
        +=, -=, /=, *=
            These all operate on the .Y attribute
        .__call__(x)
            Returns the y-value at x using linear interpolation
        ==
            Evaluates to True if and only if the X, Y, and units match
        .__iter__()
            Iterates over the ordered sequence of data points, yielding a
            tuple of (x,y) at each point
        len()
            Number of data points in the curve
        .__getitem__(i)
            Returns the i-th data point as the tuple (x,y)
        str()
            A string containing all data points and units
    Object Methods:
        append
        extend
        deriv
        sparkstr
        x2i
        x2i_uneven
    '''
    
    def __init__(self, X, Y, x_units='', y_units='',props={}):
        if len(X) != len(Y):
            raise ValueError('X & Y arrays are of unequal length')
        
        self.X = np.array(X)
        self.x_units = str(x_units)
        self.Y = np.array(Y)
        self.y_units = str(y_units)
        self.props = dict(props)
    # END __init__
    
    # Property functions
    #-------------------
    @property
    def equip_settings(self):
        '''This property is an alias of the props attribute
            (backwards compatibility support)
        '''
        return self.props
    # END equip_settings
    
    # Special methods
    #----------------
    def __add__(self, other):
        newcrv = CurveData.copy(self)
        newcrv += other
        return newcrv
    # END __add__
    
    def __iadd__(self, other):
        if not CurveData.domain_match(self, other):
            raise ValueError('Domain mis-match during arithmetic operation')
        try:
            # other is CurveData
            self.Y = self.Y + other.Y
        except AttributeError:
            # other is anything else that will add to ndarray
            self.Y += other
        # END try
        return self
    # END __iadd__
    
    def __radd__(self, other): return self+other
    
    def __call__(self, x): return self._interp_lin(x)
    
    def __div__(self, other):
        newcrv = CurveData.copy(self)
        newcrv /= other
        try:
            newcrv.y_units = newcrv.y_units + '/' + other.y_units
        except AttributeError:
            pass
        # END try
        return newcrv
    # END __div__
    
    def __idiv__(self, other):
        if not CurveData.domain_match(self, other):
            raise ValueError('Domain mis-match during arithmetic operation')
        try:
            # other is CurveData
            self.Y /= other.Y
        except AttributeError:
            # other is anything else that will divide a ndarray
            self.Y /= other
        # END try
        return self
    # END __idiv__
    
    def __eq__(self, other):
        try:
            return (
                np.array_equal(self.X, other.X)
                and np.array_equal(self.Y, other.Y)
                and self.x_units == other.x_units
                and self.y_units == other.y_units
                )
        except AttributeError:
            raise TypeError(
                'Cannot equate CurveData to type {}'.format(
                    type(other).__name__
                    )
                )
        # END try
    # END __eq__
    
    def __iter__(self):
        for i in range(len(self)): yield self.X[i], self.Y[i]
    # END __iter__
    
    def __len__(self): return len(self.X)
    
    def __getitem__(self, i):
        return self.X[i], self.Y[i]
    # END __getitem__
    
    def __mul__(self, other):
        newcrv = CurveData.copy(self)
        newcrv *= other
        try:
            newcrv.y_units = newcrv.y_units + '*' + other.y_units
        except AttributeError:
            pass
        # END try
        return newcrv
    # END __mul__
    
    def __rmul__(self, other): return self*other
    
    def __imul__(self, other):
        if not CurveData.domain_match(self, other):
            raise ValueError('Domain mis-match during arithmetic operation')
        try:
            # other is CurveData
            self.Y *= other.Y
        except AttributeError:
            # other is anything else that will multiply a ndarray
            self.Y *= other
        # END try
        return self
    # END __imul__
    
    def __str__(self):
        # Mostly just for debuging purposes
        return '{} {}, {} {}'.format(
            str(self.X), self.x_units, str(self.Y), self.y_units
            )
    # END __str__
    
    def __sub__(self, other): return self + -1.0*other
    
    def __isub__(self, other):
        self += -1.0*other
        return self
    # END __isub__
    
    def __rsub__(self, other): return self*(-1.0) + other
    
    # Property functions
    #-------------------
    @property
    def units(self): return (self.x_units, self.y_units)
    
    # List-like methods
    #------------------
    def append(self, *args):
        '''CurveData append
        
            acceptable args:
                x, y: two numeric types or numeric strings
                (x, y): a tuple or list containing x,y points
        '''
        if len(args) == 1:
            if type(args) is str:
                raise TypeError(
                    'Cannot append str to CurveData object, only list-like objects'
                )
            # END if
            try:
                self.X.append(args[0][0])
                self.Y.append(args[0][1])
            except TypeError:
                raise TypeError(
                    'Cannot append ' + type(args[0]).__name__ +
                    ' to CurveData object, only list-like objects'
                )
             # END try
        elif len(args) == 2:
            try:
                float(args[0])
                float(args[1])
            except TypeError:
                raise TypeError('x & y must be numeric types or numeric strings')
            # END try
        elif 2 < len(args):
            raise TypeError('CurveData.append takes at most 2 arguments')
        # END if
    # END append
    
    def extend(self, *args):
        '''CurveData extend
        
            Any number of CurveData or [X, Y] objects will be used to extend the
            CurveData object.
        '''
        for obj in args:
            if type(obj) is CurveData:
                if self.units != obj.units:
                    raise ValueError(
                        'Cannot concatenate CurveData objects with different units'
                    )
                # END if
                self.X.extend(self.X)
                self.Y.extend(self.Y)
            else:
                if type(obj) is str:
                    raise TypeError(
                        'Cannot append str to CurveData object'
                    )
                # END if
                # Expecting that obj = [X, Y]
                try:
                    X = obj[0]
                    Y = obj[1]
                except TypeError:
                    raise TypeError(
                        'Invaild type, ' + type(obj).__name__ +
                        ', for extend to CurveData'
                        )
                # END try
                if len(X) != len(Y):
                    raise ValueError(
                        'X & Y arrays must be equal length in order to ' +
                        'extend to CurveData object'
                        )
                # END if
                self.X.extend(X)
                self.Y.extend(Y)
            # END if
        # END for
    # END extend
    
    # Class methods
    #--------------
    @classmethod
    def copy(cls, crv):
        return cls(
            crv.X, crv.Y, x_units=crv.x_units, y_units=crv.y_units,
            props=crv.equip_settings
            )
    # END copy
    
    @classmethod
    def deriv_sg(cls, crv, x_window, poly_order, deriv_order=0, b=None):
        '''Savitzky-Golay Smoothing & Differentiating Method
        
        Args:
            x_window (float): Target window size in units of X-axis
            poly_order (int): Order of the polynomial used in the local
                                regressions.
            deriv_order = 0 (int): The order of the derivative to take.
            b = None (matrix): Optional precomputed coefficient matrix
        Returns:
            (CurveData)  The resulting filtered curve data.
        '''
        
        # Validate input
        try:
            poly_order = np.abs(int(poly_order))
        except ValueError:
            raise ValueError("polynomial order has to be of int type")
        # END try
        
        dx = np.abs(crv.X[1] - crv.X[0])
        i_window = int(x_window/dx)
        i_window += 1 - i_window%2
        if i_window < poly_order + 2:
            raise TypeError(
                "Window of " + str(i_window) + " " +
                "pnts is too small for the polynomials order of " +
                str(poly_order)
                )
        # END if
        
        Y = crv.Y
        porder_range = list(range(poly_order+1))
        half_window = (i_window -1) / 2
        
        # Compute coefficients
        if b is None:
            b = np.mat(
                [
                    [k**i for i in porder_range] for k in range(
                        -half_window, half_window+1
                        )
                ]
                )
        # END if
        m = np.linalg.pinv(b).A[deriv_order]
        
        # pad the function at the ends with reflections
        left_pad = Y[0] - ( Y[1:half_window+1][::-1] - Y[0] )
        right_pad = Y[-1] - (Y[-half_window-1:-1][::-1] - Y[-1])
        Y = np.concatenate((left_pad, Y, right_pad))
        
        dY = ( np.power(-1, deriv_order) * np.convolve( m, Y, mode='valid')
               / np.power(dx, deriv_order)
             )
        
        return cls( crv.X, dY,
                     x_units=crv.x_units,
                     y_units=crv.y_units+'/'+crv.x_units,
                     props=crv.props
                   )
    # END deriv_sg
    
    @classmethod
    def deriv_cdiff(cls, crv):
        '''Central Difference Derivative Method
        
        Returns:
            (ndarray)  dY/dX
        '''
        
        X = crv.X
        Y = crv.Y
        dX = np.zeros(len(crv))
        dX[0] = X[1] - X[0]
        dX[1:-1] = X[2:] - X[:-2]
        dX[-1] = X[-1] - X[-2]
        dY = np.zeros(len(crv))
        dY[0] = Y[1] - Y[0]
        dY[1:-1] = Y[2:] - Y[:-2]
        dY[-1] = Y[-1] - Y[-2]
        
        return cls( X, dY/dX,
                     x_units=crv.x_units,
                     y_units=crv.y_units+'/'+crv.x_units,
                     props=crv.equip_settings
                   )
    # END deriv_cdiff
    
    @classmethod
    def domain_match(cls, A, B):
        try:
            return np.array_equal(A.X, B.X)
        except (AttributeError, TypeError) as err:
            return True
        # END try
        return True
    # END domain_match
    
    @classmethod
    def nn_smooth(cls, crv, window_size):
        '''Near-Neighbor Smoothing Function
        
        Args:
            window_size (int): Should be an odd positive integer.
        Returns:
            (numpy.ndarray)  Resulting smoothed curve data.
        '''
        
        try:
            window_size = np.abs(np.int(window_size))
        except ValueError:
            raise ValueError('window_size must be of type int')
        if window_size % 2 != 1 or window_size < 1:
            raise ValueError("window_size size must be an odd number")
        # END try
        
        Y = np.array(crv.Y)
        half_window = (window_size -1) / 2
        left_pad = Y[0] - ( Y[1:half_window+1][::-1] - Y[0] )
        right_pad = Y[-1] - (Y[-half_window-1:-1][::-1] - Y[-1])
        Y = np.concatenate((left_pad, Y, right_pad))
        
        sY = np.zeros(len(crv))
        for i in range(len(crv)):
            sY[i] = np.mean(Y[i:i+2*half_window+1])
        
        return cls( crv.X, sY,
                     x_units=crv.x_units, y_units=crv.y_units,
                     props=crv.props
                   )
    # END nn_smooth
    
    @classmethod
    def norm_deriv(cls, crv, x_window, poly_order):
        '''Wrapper for numerical.norm_deriv
        '''
        
        ndY = num.norm_deriv(crv.X, crv.Y, x_window, poly_order)
        return cls( crv.X, ndY, x_units=crv.x_units, y_units='',
                     props=crv.props
                   )
    # END norm_deriv
    
    # Object methods
    #------------------------
    def _interp_lin(self, x):
        '''Estimate y(x) using a linear interpolation
        '''
        #if x < self.X[0] or self.X[-1] < x:
        #    raise ValueError('Cannot interpolate a value outside domain')
        
        dx = self.X[1] - self.X[0]
        ia = int((x-self.X[0])/dx)
        if self.X[ia] == x:
            return self.Y[ia]
        elif self.X[ia+1] == x:
            return self.Y[ia+1]
        else:
            return self.Y[ia] + ((self.Y[ia+1]-self.Y[ia])/dx)*(x-self.X[ia])
        # END if
    # END _interp_lin
    
    def deriv(self, *args):
        # args = (x_window, poly_order, deriv_order)
        if len(args) > 3:
            args = args[:3]
        try:
            dY, params = self.__deriv
            if params == args:
                return dY
            else:
                del self.__deriv
                return self.deriv(*args)
            # END if
        except AttributeError:
            # No derivate curve has been cached
            if len(args) == 3:
                dY = CurveData.deriv_sg(self, *args)
            else:
                dY = CurveData.deriv_cdiff(self)
            # END if
            self.__deriv = (dY, args)
            return dY
        # END try
    # END deriv
    
    @classmethod
    def save(cls, crv, save_path, imgindex=None):
        '''Save the curve data as a text file
        
        This method will write the data to a text file with the
        following format:
        # <header lines>
        
        <col units>   <col units>
        <col axis>    <col axis>
        <data point>  <data point>
        
        Args:
            file_path (str): save location and file name with appropriate
                             file extension
        '''
        
        # local copy of the properties dict
        props = dict(crv.props)
        if imgindex is not None: props['Image Index'] = imgindex
        
        f = open(save_path, 'w')
        
        # Write file type label
        f.write('spec\n')
        
        # Write header
        f.write('# File Format = ASCII\n')
        f.write(
            '# Created: ' + time.strftime('%Y %b %d %H:%M:%S') + '\n'
            )
        for k in sorted(props.keys()):
            if k[0] == '_': continue
            v = props[k]
            try:
                f.write('# {0} = {1.value} {1.unit}\n'.format(k, v))
            except Exception:
                f.write('# {} = {}\n'.format(k, v))
            # END try
        # END for
        f.write('\n')
        
        # Write column labels
        f.write( '{0:12}    {1:12}\n'.format(*crv.units) )
        f.write( '{0:12}    {1:12}\n'.format('X', 'Y') )
        
        # Write data
        for i_ln in range(len(crv)):
            data_ln = '{0:0<+12.5e}    {1:0<+12.5e}\n'.format(
                crv.X[i_ln], crv.Y[i_ln]
                )
            f.write(data_ln)
        # END for
        
        f.close()
    # END save
    
    def sparkstr(self, canvas_shape=(40, 60)):
        '''.
        '''
        
        canvas_shape = (int(canvas_shape[0]), int(canvas_shape[1]))
        charlist = []
        for i in range(canvas_shape[0]):
            for j in range(canvas_shape[1]):
                charlist.append(' ')
            charlist.append('\n')
        # END for
        xmin = self.X[0]
        xres = abs(self.X[0] - self.X[-1]) / float(canvas_shape[1]-1)
        Ysorted = np.sort(self.Y)
        ymax = Ysorted[-1]
        ymin = Ysorted[0]
        yres = (ymax - ymin) / float(canvas_shape[0]-1)
        for x, y in self:
            x -= xmin
            y -= ymin
            # row
            n = (canvas_shape[0]-1-int(y/yres)) * (canvas_shape[1]+1)
            # column
            n += int(x/xres)
            try:
                charlist[n] = '*'
            except IndexError:
                pass
            # END try
        # END for
        return ''.join(charlist)
    # END sparkstr
    
    def x2i(self, x):
        return int( (x-self.X[0]) / (self.X[1]-self.X[0]) )
    # END x2i
    
    def x2i_uneven(self, x):
        a = 0
        b = len(self)
        while a + 1 < b:
            c = int((a+b)/2)
            if x < self.X[c]:
                b = c
            else:
                a = c
            # END if
        # END while
        if self.X[a] <= x and x < self.X[a+1]:
            return a
        else:
            raise RuntimeError(
                'X[{}]={} <= {} < X[{}]={} is False'.format(
                    a, self.X[a], x, a+1, self.X[a+1]
                )
            )
        # END if
    # END x2i_uneven
# END CurveData

#===============================================================================
class CurveDataError(CurveData):
    '''Data With Error Curve Class
    
    Subclass of CurveData
    
    Instance Attributes:
        X, x_units, Y, y_units, eY, props
    Class Methods:
        copy
    Static Methods:
        import_file
    Object Methods:
        append
        extend
    '''
    
    def __init__(self, X, Y, eY=0, x_units='', y_units='', props={}):
        super(CurveDataError, self).__init__(
            X, Y, x_units=x_units, y_units=y_units,
            props=props
        )
        
        try:
            # assuming eY is a list-like object
            if len(X) != len(eY):
                raise ValueError("eY array length doesn't match X & Y")
            self.eY = np.array(eY)
        except TypeError:
            # eY is a number
            self.eY = np.array([eY for i in range(len(X))])
        # END try
    # END __init__
    
    # List-like methods
    #------------------
    def append(self, *args):
        '''CurveDataError append
        
            acceptable args:
                x, y, ey: three numeric types or numeric strings
                (x, y, ey): a tuple or list containing x,y points
                            (*note lists/tups longer than 2 will be accepted
                            but extra entries will be ignored)
        '''
        if len(args) == 1:
            if type(args) is str:
                raise TypeError(
                    'Cannot append str to CurveDataError object, only list-like objects'
                    )
            # END if
            try:
                self.X.append(args[0][0])
                self.Y.append(args[0][1])
                self.eY.append(args[0][2])
            except TypeError:
                raise TypeError(
                    'Cannot append ' + type(args[0]).__name__ +
                    ' to CurveDataError object, only list-like objects'
                    )
             # END try
        elif len(args) == 3:
            try:
                float(args[0])
                float(args[1])
                float(args[2])
            except TypeError:
                raise TypeError('x & y must be numeric types or numeric strings')
            # END try
        else:
            raise TypeError('CurveDataError.append takes at most 3 arguments')
        # END if
    # END append
    
    def extend(self, *args):
        '''CurveDataError extend
        
            Any number of CurveDataError or [X, Y, eY] objects will be used
            to extend the CurveDataError object.
        '''
        for arg in args:
            if type(arg) is CurveDataError:
                if self.units != arg.units:
                    raise ValueError(
                        'Cannot concatenate CurveDataError objects with different units'
                        )
                # END if
                self.X.extend(arg.X)
                self.Y.extend(arg.Y)
                self.eY.extend(arg.eY)
            else:
                if type(arg) is str:
                    raise TypeError(
                        'Cannot append str to CurveDataError object'
                        )
                # END if
                try:
                    X = arg[0]
                    Y = arg[1]
                    eY = arg[2]
                except TypeError:
                    raise TypeError(
                        'Invaild type, ' + type(arg).__name__ +
                        ', for extend to CurveDataError'
                        )
                # END try
                if not (len(X) == len(Y) and len(X) == len(eY)):
                    raise ValueError(
                        'X & Y arrays must be equal length in order to ' +
                        'extend to CurveDataError object'
                        )
                # END if
                self.X.extend(X)
                self.Y.extend(Y)
                self.eY.extend(eY)
            # END if
        # END for
    # END extend
    
    # Class methods
    #--------------
    @classmethod
    def copy(cls, crv):
        return cls( crv.X, crv.Y, eY=crv.eY,
                     x_units=crv.x_units, y_units=crv.y_units, 
                     props=crv.props
                   )
    # END copy
    
    # Object-specific methods
    #------------------------
    def save(self, save_path):
        '''Save the curve data as a text file
        
        This method will write the data to a text file with the
        following format:
        # <header lines>
        
        <col units>   <col units>
        <col axis>    <col axis>
        <data point>  <data point>
        
        Args:
            file_path (str): save location and file name with appropriate
                             file extension
        '''
        
        props = dict(self.props)
        
        f = open(save_path, 'w')
        
        # Write file type label
        f.write('specerror\n')
        
        # Write header
        f.write('# File Format = ASCII\n')
        f.write(
            '# Created: ' + time.strftime(r'%m/%d/%Y %H:%M:%S') + '\n'
        )
        for k in sorted(self.props.keys()):
            v = self.props[k]
            f.write('# {} = {}\n'.format(k, v))
        # END for
        f.write('\n')
        
        # Write column labels
        f.write( '{0:12}    {1:12}    {1:12}\n'.format(*self.units) )
        f.write('{0:12}    {1:12}    {2:12}\n'.format('X', 'Y', 'Y_error'))
        
        # Write data
        for i_ln in range(len(self)):
            data_ln = '{0:0<+12.5e}    {1:0<+12.5e}    {2:0<+12.5e}\n'.format(
                self.X[i_ln], self.Y[i_ln], self.eY[i_ln]
                )
            f.write(data_ln)
        # END for
        
        f.close()
    # END save
# END CurveDataError
