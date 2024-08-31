#!/usr/bin/python3

import sys
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
try:
    NaN = np.nan
except AttributeError:
    NaN = np.NaN
from html import escape
from bisect import bisect
try:
    from itertools import pairwise
except ImportError:
    pairwise = None
from mpl_toolkits.mplot3d import Axes3D
from argparse import ArgumentParser, HelpFormatter
from matplotlib import cm, __version__ as matplotlib_version, rcParams, ticker
from matplotlib.widgets import Slider
from matplotlib.patches import Rectangle
try:
    from smithplot.smithaxes import SmithAxes
except ImportError:
    SmithAxes = None
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import pandas         as pd
except ImportError:
    px = None
try:
    import stl
    from scipy.spatial import Delaunay
except ImportError:
    stl = None
    pass

matplotlib_version_float = float ('.'.join (matplotlib_version.split ('.')[:2]))

Omega = "\u2126"
ohm = ' %s' % Omega

def blend (color, alpha = 0x80, bg = '#FFFFFF'):
    """ Blend a color with a background color, default white with a
        given alpha channel, the input color is in #RRGGBB format
    """
    alpha = alpha / 255
    color = np.array ([int (color [n:n+2], 16) for n in range (1, 6, 2)]) / 255
    bg    = np.array ([int (bg    [n:n+2], 16) for n in range (1, 6, 2)]) / 255
    rgb   = (((1 - alpha) * bg + alpha * color) * 255).astype (int)
    return '#%02X%02X%02X' % tuple (rgb)
# end def blend

class Scaler:

    @property
    def tick_values (self):
        g = self.ticks
        return self.scale (0, g)
    # end def tick_values

    @property
    def tick_text (self):
        g = self.ticks
        return [''] + [('%d' % i) for i in g [1:]]
    # end def tick_text

    def set_ticks (self, ax):
        g = self.ticks
        ax.set_rticks (self.tick_values)
        ax.set_yticklabels (self.tick_text, ha = 'center')
    # end def set_ticks

# end class Scaler

class Linear_Scaler (Scaler):
    ticks = np.array ([0, -3, -6, -10])
    title = 'Linear scale'

    def scale (self, max_gain, gains):
        return 10 ** ((gains - max_gain) / 10)
    # end def scale

    def invscale (self, v):
        """ Test
        >>> sc = Linear_Scaler ()
        >>> for db in range (0, 25, 10):
        ...     print ("%.2f" % sc.invscale (sc.scale (0, db)))
        0.00
        10.00
        20.00
        """
        return 10 * np.log (v) / np.log (10)
    # end def invscale

# end class Linear_Scaler

scale_linear = Linear_Scaler ()

class Linear_Voltage_Scaler (Scaler):
    ticks = np.array ([0, -3, -6, -10, -20])
    title = 'Linear voltage'

    def scale (self, max_gain, gains):
        return 10 ** ((gains - max_gain) / 20)
    # end def scale

    def invscale (self, v):
        """ Test
        >>> sc = Linear_Voltage_Scaler ()
        >>> for db in range (0, 25, 10):
        ...     print ("%.2f" % sc.invscale (sc.scale (0, db)))
        0.00
        10.00
        20.00
        """
        return 20 * np.log (v) / np.log (10)
    # end def invscale

# end class Linear_Voltage_Scaler

scale_linear_voltage = Linear_Voltage_Scaler ()

class ARRL_Scaler (Scaler):
    ticks = np.array ([0, -3, -6, -10, -20, -30])
    title = 'ARRL'

    def scale (self, max_gain, gains):
        return (1 / 0.89) ** ((gains - max_gain) / 2)
    # end def scale

    def invscale (self, v):
        """ Test
        >>> sc = ARRL_Scaler ()
        >>> for db in range (0, 35, 10):
        ...     print ("%.2f" % sc.invscale (sc.scale (0, db)))
        0.00
        10.00
        20.00
        30.00
        """
        return np.log (v) / np.log (1 / 0.89) * 2
    # end def invscale

# end class ARRL_Scaler

scale_arrl = ARRL_Scaler ()

class Linear_dB_Scaler (Scaler):
    title = 'Linear dB'

    def __init__ (self, min_db = -50):
        if min_db >= 0:
            raise ValueError ("min_db must be < 0")
        self.min_db = min_db
        self.ticks = np.arange (0, self.min_db - 10, -10)
    # end def __init__

    def scale (self, max_gain, gains):
        return \
            ( (np.maximum (self.min_db, (gains - max_gain)) - self.min_db)
            / -self.min_db
            )
    # end def scale

    def invscale (self, v):
        """ Test
        >>> sc = Linear_dB_Scaler ()
        >>> for db in range (0, -sc.min_db + 1, 10):
        ...     print ("%.2f" % sc.invscale (sc.scale (0, db)))
        0.00
        10.00
        20.00
        30.00
        40.00
        50.00
        """
        return v * -self.min_db + self.min_db
    # end def invscale

# end class Linear_dB_Scaler

class Plot_Range:
    """ Sensible Y range so that all different Y coordinates can
        share a grid.
    """

    def __init__ (self, y, min_y = None):
        self.max = max (y)
        self.min = min_y
        if min_y is None:
            self.min = min (y)
        self.exp = int \
            (np.log (max (abs (self.max), abs (self.min))) / np.log (10))
        self.max /= 10 ** self.exp
        self.min /= 10 ** self.exp
        assert abs (self.max) < 10 and abs (self.min) < 10
        # round mn to lower int
        self.min = np.floor (self.min)
        # round mx to higher int
        self.max = np.ceil (self.max)
        self.rng, self.tck = self.compute ()
    # end def __init__

    def compute (self):
        for k in 1, 2, 4, 8, 10:
            if self.max - self.min <= k:
                rng = np.array ([self.min, self.min + k]) * 10 ** self.exp
                tck = (k / 4) * 10 ** self.exp
                return rng, tck
        rng = np.array ([self.min, self.min + 12]) * 10 ** self.exp
        tck = 3 * 10 ** self.exp
        return rng, tck
    # end def compute

    def as_plotly (self):
        return dict (range = self.rng, dtick = self.tck, tick0 = self.rng [0])
    # end def as_plotly

    def as_matplot (self):
        r1, r2 = self.rng
        t = self.tck
        return dict (yticks = np.arange (r1, r2 + t, t), ylim = self.rng)
    # end def as_matplot

    def fmt (self, tail = '', precision = 1):
        strf  = ticker.FormatStrFormatter
        fmt = ('%%.%df' % precision) + tail
        if self.tck == int (self.tck):
            fmt = '%.0f' + tail
        return strf (fmt)
    # end def fmt

# end class Plot_Range:

def format_f (f, precision = 3):
    fmt = '%%.%df ' % precision
    if f < 1e-3:
        ff = (fmt + 'Hz') % (f * 1e6)
    elif f < 1:
        ff = (fmt + 'kHz') % (f * 1e3)
    elif f >= 1e6:
        ff = (fmt + 'THz') % (f / 1e6)
    elif f >= 1e3:
        ff = (fmt + 'GHz') % (f / 1e3)
    else:
        ff = (fmt + 'MHz') % f
    return ff
# end def format_f

class Gain_Data:
    """ Store gain data by key
        This is used during all sorts of parsing and/or generating
        values some other way.
        The key is a tuple, the first (index 0) value is the frequency.
        Next value (optionally) is the polarization, the values we're
        using are 'H' for horizontal, 'V' for vertical and 'sum' for the
        sum, but other parsers may use different values.
        Circular polarization is not yet parsed from NEC output, MININEC
        doesn't compute circular polarization.
    """

    def __init__ (self, key, parent = None):
        self.parent   = parent
        self.key      = key
        self.pattern  = {}
    # end def __init__

    @property
    def do_polarization (self):
        """ This is implemented as a property because it can't be
            computed in __init__ because parent not yet known
        """
        # Special case for plotly if we're plotting a single
        # polarization which is *not* the sum
        if  (  self.parent.do_plotly
            and len (self.parent.pol_keys) == 1
            and next (iter (self.parent.pol_keys)) != 'sum'
            ):
            return True
        return \
            (   (  len (self.parent.pol_keys) > 1
                or next (iter (self.parent.pol_keys)) != 'sum'
                )
            and self.parent.mpl_plot_key is None
            and not self.parent.do_plotly
            )
    # end def do_polarization

    @property
    def maxgain (self):
        return self.parent.maxgain
    # end def maxgain

    def compute (self):
        thetas = set ()
        phis   = set ()
        gains  = []
        for theta, phi in sorted (self.pattern):
            thetas.add (theta)
            phis.add   (phi)
        self.max_phi_diff = self.max_theta_diff = 1e-9
        if pairwise is not None:
            tdiff = None
            for a, b in pairwise (sorted (thetas)):
                if tdiff is None or abs (a - b) > tdiff:
                    tdiff = abs (a - b)
            self.max_theta_diff = tdiff
            pdiff = None
            for a, b in pairwise (sorted (phis)):
                if pdiff is None or abs (a - b) > pdiff:
                    pdiff = abs (a - b)
            self.max_phi_diff = pdiff

        td = list (sorted (thetas))
        pd = list (sorted (phis))
        self.thetas_d = np.array (td)
        self.phis_d   = np.array (pd)
        self.thetas   = self.thetas_d * np.pi / 180
        self.phis     = self.phis_d   * np.pi / 180

        gains = self.gains = np.full ((len (thetas), len (phis)), NaN)
        for theta, phi in sorted (self.pattern):
            tidx = td.index (theta)
            pidx = pd.index   (phi)
            self.gains [tidx][pidx] = self.pattern [(theta, phi)]

        self.maxg = np.nanmax (gains)
        idx = np.unravel_index (np.nanargmax (self.gains), self.gains.shape)
        self.theta_maxidx, self.phi_maxidx = idx
        # Special case: If theta is 0° or 180° recompute phi_maxidx
        # since in that case all values are the same at that theta angle
        if self.thetas_d [self.theta_maxidx] == 0:
            self.phi_maxidx = np.nanargmax (self.gains [1])
        elif self.thetas_d [self.theta_maxidx] == 180:
            self.phi_maxidx = np.nanargmax (self.gains [-1])
        self.theta_max = self.thetas_d [self.theta_maxidx]
        self.phi_max   = self.phis_d   [self.phi_maxidx]
        self.desc      = ['Title: %s' % self.parent.title]
        self.desc.append ('Frequency: ' + format_f (self.key [0], 2))
        self.lbl_deg   = 0
        self.labels    = None
    # end def compute

    def azimuth_gains (self, scaler):
        g = self.gains [self.parent.theta_angle_idx]
        gains = scaler.scale (self.maxgain, g)
        return gains, g
    # end def azimuth_gains

    def azimuth_text (self, scaler):
        desc = self.desc.copy ()
        desc.insert (0, 'Azimuth Pattern')
        unit = self.parent.args.dB_unit
        if self.do_polarization:
            desc.append ('Polarization: ' + self.key [1])
        desc.append ('Outer ring: %.2f %s' % (self.maxgain, unit))
        desc.append ('Scaling: %s' % scaler.title)
        desc.append \
            ( 'Elevation: %.2f°'
            % (90 - self.thetas_d [self.parent.theta_angle_idx])
            )
        return desc
    # end def azimuth_text

    def elevation_gains (self, scaler):
        gains1 = self.gains.T [self.parent.phi_angle_idx].T
        # Find index of the other side of the azimuth
        pmx = self.phis.shape [0] - self.phis.shape [0] % 2
        idx = (self.parent.phi_angle_idx + pmx // 2) % pmx
        assert idx != self.parent.phi_angle_idx
        phis = self.phis
        diff = abs (phis [idx] - phis [self.parent.phi_angle_idx])
        # This should really be a very low value but if these are
        # measurements with uneven angles this may be larger
        assert diff - np.pi <= self.max_phi_diff
        gains2 = self.gains.T [idx].T
        g = np.append (gains1, np.flip (gains2))
        gains = scaler.scale (self.maxgain, g)
        return gains, g
    # end def elevation_gains

    def elevation_text (self, scaler):
        desc = self.desc.copy ()
        desc.insert (0, 'Elevation Pattern')
        unit = self.parent.args.dB_unit
        if self.do_polarization:
            desc.append ('Polarization: ' + self.key [1])
        desc.append ('Outer ring: %.2f %s' % (self.maxgain, unit))
        desc.append ('Scaling: %s' % scaler.title)
        desc.append \
            ( 'Azimuth: %.2f° (X=0°)'
            % self.phis_d [self.parent.phi_angle_idx]
            )
        return desc
    # end def elevation_text

    def interpolate_azimuth (self, step_deg, start_deg = 0, end_deg = 360):
        thetas   = set ()
        by_theta = {}
        for theta, phi in sorted (self.pattern):
            thetas.add (theta)
            if theta not in by_theta:
                by_theta [theta] = []
            by_theta [theta].append (phi)

        pattern_new = {}
        for theta in thetas:
            phis = by_theta [theta]
            stop = end_deg + step_deg
            for azi in np.arange (start_deg, stop, step_deg, dtype = float):
                idx = bisect (phis, azi % 360)
                if idx == 0 or idx == len (phis):
                    if start_deg > 0 or end_deg < 360:
                        continue
                    if idx == 0:
                        p_l = phis [-1]
                        p_r = phis [idx]
                    else:
                        p_l = phis [idx - 1]
                        p_r = phis [0]
                else:
                    p_l = phis [idx - 1]
                    p_r = phis [idx]
                assert p_l >= 0
                assert p_r >= 0
                l = self.pattern [(theta, p_l)]
                r = self.pattern [(theta, p_r)]
                if p_r < p_l:
                    p_l -= 360
                if p_r == p_l:
                    v = l
                else:
                    v = (((azi % 360) - p_l) / (p_r - p_l) * (r - l) + l)
                    assert l <= v <= r or l >= v >= r
                pattern_new [(theta, azi)] = v
        self.pattern = pattern_new
    # end def interpolate_azimuth

    def plot3d_gains (self, scaler):
        gains  = scaler.scale (self.parent.maxg, self.gains)
        P, T   = np.meshgrid (self.phis, self.thetas)
        X = np.cos (P) * np.sin (T) * gains
        Y = np.sin (P) * np.sin (T) * gains
        Z = np.cos (T) * gains
        # t must be same shape as X, Y, Z
        t = np.stack \
            ([ self.gains
             , self.gains - self.parent.maxg
             , P / np.pi * 180
             , 90 - T / np.pi * 180
            ], axis = -1)
        # Workaround: plotly swaps the axes, see
        # https://github.com/plotly/plotly.js/issues/5003
        t = np.moveaxis (t, (0, 1, 2), (1, 0, 2))
        return t, gains, X, Y, Z
    # end def plot3d_gains

# end class Gain_Data

class Geo_Data:

    def __init__ (self, has_ground = None):
        self.entries    = []
        self.wires      = []
        self.has_ground = has_ground
    # end def __init__

    def __bool__ (self):
        """ Always True, we compare with None etc.
        """
        return True
    # end def __bool__

    def __len__ (self):
        return len (self.entries)
    # end def __len__

    def __getitem__ (self, idx):
        return self.entries [idx]
    # end def __getitem__

    def __setitem__ (self, idx, value):
        self.entries [idx] = value
    # end def __setitem__

    def append (self, item):
        self.entries.append (item)
    # end def append

    def fix_wires (self):
        for w, g in zip (self.wires, self.entries):
            if not g or w [0] != g [0]:
                g.insert (0, w [0])
            if w [-1] != g [-1]:
                g.append (w [-1])
    # end def fix_wires

# end class Geo_Data

class Impedance_Data:

    def __init__ (self, frequency, impedance):
        self.frequency = frequency
        self.impedance = impedance
    # end def __init__

# end class Impedance_Data

def nearest_angle_idx (angles, dst_angle):
    """ Compute index of angle nearest to dst_angle in angles.
        The sequence angles is sorted.
    """
    idx  = bisect (angles, dst_angle)
    if idx >= len (angles):
        idx = len (angles) - 1
    if idx < 0:
        idx = 0
    if idx == 0:
        return idx
    if (abs (angles [idx] - dst_angle) < abs (angles [idx - 1] - dst_angle)):
        return idx
    return idx - 1
# end def nearest_angle_idx

class Loaded_Segment:
    """ A segment either loaded with an impedance or an excitation
    """

    nec_types = \
        [ 'Series RLC, absolute'
        , 'Parallel RLC, absolute'
        , 'Series RLC, per m'
        , 'Parallel RLC, per m'
        , 'Impedance'
        , 'Wire conductivity'
        ]

    def __init__ (self, by_name, coord, name):
        self.coord   = coord
        self.name    = name
        self.by_name = by_name
        if name not in self.by_name:
            self.by_name [name] = []
        self.by_name [name].append (self)
    # end def __init__

# end class Loaded_Segment

class Gain_Plot:
    plot_names   = \
        ( 'azimuth', 'elevation'
        , 'plot_vswr', 'plot3d', 'plot_geo', 'plot_smith'
        )
    update_names = set (('azimuth', 'elevation', 'plot3d'))
    font_sans    = \
        "Helvetica, Nimbus Sans, Liberation Sans, Open Sans, arial, sans-serif"
    # Default colors for swr plot
    c_real = '#AE4141'
    c_imag = '#FFB329'

    def __init__ \
        ( self, args, gdata
        , loaded_segs = None
        ):
        self.args        = args
        self.dpi         = args.dpi
        # fix_x and fig_y are used for matplotlib only
        self.fig_x       = args.width  or 512
        self.fig_y       = args.height or 384
        self.filename    = args.filename
        self.outfile     = args.output_file
        self.save_format = getattr (args, 'save_format', None)
        self.wireframe   = args.wireframe
        self.scalers     = dict \
            ( linear_db      = Linear_dB_Scaler (args.scaling_mindb)
            , linear_voltage = scale_linear_voltage
            , linear         = scale_linear
            , arrl           = scale_arrl
            )
        self.scaler = self.scalers [args.scaling_method]
        self.cur_scaler = self.scaler

        # Default title from filename
        self.title = os.path.splitext (os.path.basename (args.filename)) [0]
        self.gdata = gdata
        for key in self.gdata:
            gd = self.gdata [key]
            assert gd.parent is None
            gd.parent = self
        self.geo          = {}
        self.idata        = {}
        self.seg_by_tag   = {}
        self.segments     = []
        self.loaded_segs  = loaded_segs or {}
        self.frq_keys     = set ()
        self.pol_keys     = set ()
        self.mpl_by_f     = {}
        self.mpl_plot_key = None
        self.do_plotly    = (getattr (self.args, 'export_html', None)
                            or getattr (self.args, 'show_in_browser', None))
        if  (   getattr (args, 'plot_smith', None)
            and SmithAxes is None and not self.do_plotly
            ):
            exit ('Error: Smith chart with matplotlib is only supported with '
                  'patched smithplot library')
    # end def __init__

    @classmethod
    def from_file (cls, args, filename = None):
        filename = filename or args.filename
        # This populates gdata and might override title:
        gp = cls (args, gdata = {})
        gp.read_file (filename)
        return gp
    # end def from_file

    @property
    def legend_name (self):
        pol_key = ''
        if len (self.pol_keys) > 1:
            pol_key = 'pol=' + self.plot_key [1]
        frq_key = "f=" + format_f (self.plot_key [0])
        if pol_key:
            if len (self.frq_keys) > 1:
                key = ' '.join ((frq_key, pol_key))
            else:
                key = pol_key
        else:
            key = frq_key
        return key
    # end def legend_name


    @property
    def plotly_polar_default (self):
        d = dict \
            ( layout = dict
                ( showlegend = True
                , colorway   = self.colormap
                , polar = dict
                    ( angularaxis = dict
                        ( rotation  = 0
                        , direction = 'counterclockwise'
                        , dtick     = 15
                        , linecolor = "#B0B0B0"
                        , gridcolor = "#B0B0B0"
                        )
                    , radialaxis = dict
                        ( tickmode  = 'array'
                        , tickvals  = self.scaler.tick_values
                        , ticktext  = self.scaler.tick_text
                        , linecolor = "#B0B0B0"
                        , gridcolor = "#B0B0B0"
                        )
                    , bgcolor = '#FFFFFF'
                    )
                , title = dict
                    ( font = dict
                        ( family = self.font_sans
                        , color  = "#010101"
                        )
                    )
                , legend = {}
                )
            )
        if self.args.width:
            d ['layout'].update (width = self.args.width)
        if self.args.height:
            d ['layout'].update (height = self.args.height)
        if self.args.legend_x:
            d ['layout']['legend'].update (x = self.args.legend_x)
        return d
    # end def plotly_polar_default

    @property
    def plotly_line_default (self):
        d = dict \
            ( layout = dict
                ( showlegend = True
                , colorway   = self.colormap
                , xaxis = dict
                    ( linecolor   = "#B0B0B0"
                    , gridcolor   = "#B0B0B0"
                    , domain      = [0, 0.9]
                    #, ticksuffix  = ' MHz'
                    , tickformat  = '.1f'
                    , hoverformat = '.2f'
                    , zeroline    = False
                    )
                , yaxis = dict
                    ( color       = self.c_vswr
                    , linecolor   = self.c_vswr
                    , showgrid    = True
                    , gridcolor   = blend (self.c_vswr)
                    , title       = {}
                    , anchor      = "x"
                    , side        = "left"
                    , hoverformat = '.3f'
                    , zeroline    = False
                    )
                , yaxis2 = dict
                    ( color       = self.c_real
                    , linecolor   = self.c_real
                    , showgrid    = False
                    , gridcolor   = blend (self.c_real)
                    , title       = {}
                    , overlaying  = "y"
                    , side        = "right"
                    , anchor      = "x2"
                    , hoverformat = '.1f'
                    , zeroline    = False
                    )
                , yaxis3 = dict
                    ( color       = self.c_imag
                    , linecolor   = self.c_imag
                    , showgrid    = False
                    , gridcolor   = blend (self.c_imag)
                    , title       = {}
                    , overlaying  = "y"
                    , side        = "right"
                    , position    = self.args.axis_3_position
                    , anchor      = "free"
                    , hoverformat = '.1f'
                    , zeroline    = False
                    )
                , paper_bgcolor = 'white'
                , plot_bgcolor  = 'white'
                , hovermode     = 'x unified'
                , title = dict
                    ( font = dict
                        ( family = self.font_sans
                        , color  = "#010101"
                        , size   = 24
                        )
                    )
                , legend = {}
                )
            )
        if self.args.width:
            d ['layout'].update (width = self.args.width)
        if self.args.height:
            d ['layout'].update (height = self.args.height)
        if self.args.legend_x:
            d ['layout']['legend'].update (x = self.args.legend_x)
        return d
    # end def plotly_line_default

    @property
    def plotly_3d_default (self):
        # Hmm: How to set scaleanchor? Used to couple ratio of axes
        # constrain and constraintoward  need also to be set
        # Hmm, rangemode (one of nonnegative, tozero, normal) does nothing
        # Ah: This applies only if we do not specify an explicit range
        d = dict \
            ( layout = dict
                ( showlegend    = True
                , colorway      = self.colormap
                , paper_bgcolor = 'white'
                , plot_bgcolor  = 'white'
                , margin        = dict
                    ( l = self.args.margin_3d
                    , r = self.args.margin_3d
                    , t = self.args.margin_3d
                    , b = self.args.margin_3d
                    )
                , scene = dict
                    ( xaxis = dict
                        ( linecolor      = "#B0B0B0"
                        , gridcolor      = "#B0B0B0"
                        , showbackground = False
                        , tickformat     = '.3f'
                        )
                    , yaxis = dict
                        ( linecolor      = "#B0B0B0"
                        , gridcolor      = "#B0B0B0"
                        , showbackground = False
                        , tickformat     = '.3f'
                        )
                    , zaxis = dict
                        ( linecolor      = "#B0B0B0"
                        , gridcolor      = "#B0B0B0"
                        , showbackground = False
                        , tickformat     = '.3f'
                        )
                    , aspectratio = dict (x=1, y=1, z=1)
                    )
                , title = dict
                    ( font = dict
                        ( family = self.font_sans
                        , color  = "#010101"
                        , size   = 24
                        )
                    , y = 0.99
                    )
                , legend = {}
                )
            )
        if self.args.width:
            d ['layout'].update (width = self.args.width)
        if self.args.height:
            d ['layout'].update (height = self.args.height)
        if self.args.legend_x:
            d ['layout']['legend'].update (x = self.args.legend_x)
        return d
    # end def plotly_3d_default

    @property
    def plotly_smith_default (self):
        d = dict \
            ( layout = dict
                ( title = dict
                    ( font = dict
                        ( family = self.font_sans
                        , color  = "#010101"
                        , size   = 20
                        )
                    )
                , legend = {}
                )
            )
        if self.args.width:
            d ['layout'].update (width = self.args.width)
        if self.args.height:
            d ['layout'].update (height = self.args.height)
        if self.args.legend_x:
            d ['layout']['legend'].update (x = self.args.legend_x)
        return d
    # end def plotly_smith_default

    def all_gains (self):
        xyz = None
        for key in self.plot_keys:
            g = self.gdata [key]
            _, _, X, Y, Z = g.plot3d_gains (self.scaler)
            if xyz is None:
                xyz = np.array ([X, Y, Z]).T
            else:
                xyz = np.concatenate ((xyz, np.array ([X, Y, Z]).T))
        return xyz.T
    # end def all_gains

    def compute (self):
        # Borrow colormap from matplotlib to use in plotly
        self.colormap = []
        for cn in mcolors.TABLEAU_COLORS:
            self.colormap.append (mcolors.TABLEAU_COLORS [cn])
        self.c_vswr = self.colormap [0]
        # If there is a title option it wins:
        if self.args.title is not None:
            self.title = self.args.title
        if not self.gdata:
            return
        self.plot_keys = []
        self.maxg = None
        theta_idx = {}
        phi_idx   = {}
        pol_keys  = set ()
        f_keys    = set ()
        # First interpolate if necessary
        for key in sorted (list (self.gdata)):
            gdata = self.gdata [key]
            if self.args.interpolate_azimuth_step:
                gdata.interpolate_azimuth (self.args.interpolate_azimuth_step)
            if len (key) > 1:
                pol_keys.add (key [1])
            f_keys.add (key [0])
        # Now add polarization sum if H and V are in data but sum is not
        dbmul = 10 / np.log (10)
        if 'H' in pol_keys and 'V' in pol_keys and self.args.polarization:
            if 'sum' in self.args.polarization and 'sum' not in pol_keys:
                for f in f_keys:
                    h = self.gdata [(f, 'H')]
                    v = self.gdata [(f, 'V')]
                    hp = h.pattern
                    vp = v.pattern
                    if len (hp) != len (vp):
                        raise ValueError \
                            ('Polarization sum: H/V angles do not match')
                    gsum = Gain_Data ((f, 'sum'), self)
                    self.gdata [(f, 'sum')] = gsum
                    for kh, kv in zip (hp, vp):
                        if kh != kv:
                            raise ValueError \
                                ('Polarization sum: H/V angles do not match')
                        g = np.log (10 ** (hp [kh] / 10) + 10 ** (vp [kv] / 10))
                        g *= dbmul
                        gsum.pattern [kh] = g
        for key in sorted (list (self.gdata)):
            if len (key) > 1:
                if self.args.polarization:
                    if key [1] not in self.args.polarization:
                        del self.gdata [key]
                        continue
                elif key [1] != 'sum':
                    del self.gdata [key]
                    continue
            gdata = self.gdata [key]
            self.frq_keys.add (key [0])
            if len (key) > 1:
                self.pol_keys.add (key [1])
            gdata.compute ()
            f = key [0]
            if f not in self.mpl_by_f:
                self.mpl_by_f [f] = []
            self.mpl_by_f [f].append (gdata)
            self.plot_keys.append (key)
            if gdata.theta_maxidx not in theta_idx:
                theta_idx [gdata.theta_maxidx] = 0
            theta_idx [gdata.theta_maxidx] += 1
            if gdata.phi_maxidx not in phi_idx:
                phi_idx [gdata.phi_maxidx] = 0
            phi_idx [gdata.phi_maxidx] += 1
            if self.maxg is None or self.maxg < gdata.maxg:
                self.maxg = gdata.maxg
        self.maxgain = self.args.maxgain
        if self.maxgain is None:
            self.maxgain = self.maxg
        self.mpl_plot_keys = list (sorted (self.mpl_by_f))
        # Compute the theta index that occurs most often over all frequencies
        self.theta_maxidx = list \
            (sorted (theta_idx, key = lambda a: theta_idx [a])) [-1]
        self.phi_maxidx = list \
            (sorted (phi_idx, key = lambda a: phi_idx [a])) [-1]
        if self.args.angle_azimuth is not None:
            phis = next (iter (self.gdata.values ())).phis_d
            self.phi_angle_idx = nearest_angle_idx \
                (phis, self.args.angle_azimuth)
        else:
            self.phi_angle_idx = self.phi_maxidx
        if self.args.angle_elevation is not None:
            thetas = next (iter (self.gdata.values ())).thetas_d
            self.theta_angle_idx = nearest_angle_idx \
                (thetas, 90 - self.args.angle_elevation)
        else:
            self.theta_angle_idx = self.theta_maxidx
    # end def compute

    def new_geo (self, gnd = False):
        if not self.geo:
            k = 0
        else:
            k = max (self.geo) + 1
        self.geo [k] = Geo_Data (has_ground = gnd)
        return self.geo [k]
    # end def new_geo

    def read_file (self, filename):
        guard     = 'not set'
        delimiter = guard
        gdata     = None
        idata     = None
        status    = 'start'
        impedance = None
        z_offset  = None
        geowire   = None
        geo       = None
        asap_p    = 'THETA PHI ' * 2 + 'REAL IMAG MAGN PHASE ' * 2
        asap_p    = asap_p.strip ()
        gain_fmt  = ('gnn', 'mininec-gain', 'nec-gain', 'asap-gain')
        log10     = np.log (10)
        f         = None
        # NEC can use Major/Minor axis or Vertc/Horiz polarizations
        # Depending on the 'X' of the 'XNDA' field of the RP card
        # We fill in the polarization only if we see VERTC/HORIZ
        nec_vh    = True
        gnd       = False
        has_gnd   = None
        with open (filename, 'r') as fp:
            for line in fp:
                line = line.strip ()
                splt = ' '.join (line.split ())
                if splt == 'X Y Z RADIUS END1 END2 NO.':
                    status  = 'geo'
                    geowire = None
                    if geo is None:
                        # Only one geo in mininec, continued
                        if self.geo:
                            gidx = max (self.geo)
                            geo = self.geo [gidx]
                        else:
                            geo = self.new_geo (has_gnd)
                    geo.append ([])
                    continue
                if splt == 'X Y Z RADIUS CONNECTION SEGMENTS':
                    status = 'wire'
                    if geo is None:
                        if self.geo:
                            gidx = max (self.geo)
                            geo = self.geo [gidx]
                        else:
                            geo = self.new_geo (has_gnd)
                    geo.wires.append ([])
                    continue
                if  (  line.startswith ('END ONE COORDINATES')
                    or line.startswith ('END TWO COORDINATES')
                    ):
                    if not geo:
                        geo = self.new_geo (has_gnd)
                    if 'TWO' not in line:
                        geo.wires.append ([])
                    r = line.split (':', 1)[-1].strip ()
                    geo.wires [-1].append ([float (x) for x in r.split (',')])
                if  (   splt.startswith ('No: X Y Z')
                    and splt.endswith ('I- I I+ No:')
                    ):
                    status = 'necgeo'
                    assert not geo
                    geo = self.new_geo (has_gnd)
                    necidx = {}
                    continue
                if splt == 'NO. NO. X Y Z NO. X Y Z':
                    status = 'asap-geo'
                    geo = self.new_geo (has_gnd)
                    continue
                if line.startswith ('NO. OF SOURCES'):
                    status = 'source'
                    continue
                if line.startswith ('NO. OF EXCITATIONS'):
                    status = 'source'
                    continue
                if line.startswith ('NUMBER OF LOADS'):
                    status = 'load'
                    continue
                if line.startswith ('ENVIRONMENT'):
                    gp = int (line.split (':', 1) [-1])
                    has_gnd = gp < 0
                    if not has_gnd and '2-GROUND' in line:
                        has_gnd = gp == 2
                    if geo:
                        geo.has_ground = True
                        has_gnd = None
                    elif self.geo:
                        gidx = max (self.geo)
                        if self.geo [gidx].has_ground is None:
                            self.geo [gidx].has_ground = has_gnd
                            has_gnd = None
                    continue
                if line.startswith ('GROUND PLANE SPECIFIED'):
                    gnd = True
                    continue
                if line.startswith ('GROUND PLANE (NO/YES)'):
                    has_gnd = line.endswith ('YES')
                    if geo:
                        geo.has_ground = True
                        has_gnd = None
                    continue
                if line.startswith ('ANTENNA HEIGHT (METERS)'):
                    z_offset = float (line.split () [-1])
                    continue
                if line == 'ANTENNA FEEDS':
                    status = 'asap-feed'
                    continue
                if line == 'STRUCTURE LOADS':
                    status = 'asap-load'
                    continue
                if line.startswith ('DATA CARD No:'):
                    ll = line.split ()
                    if ll [4] == 'EX':
                        typ, tag, n = (int (x) for x in ll [5:8])
                        if typ in (0, 5):
                            assert n >= 1
                            name  = 'Excitation'
                            if tag == 0:
                                seg = self.segments [n - 1]
                            else:
                                seg = self.seg_by_tag [tag][n - 1]
                            Loaded_Segment (self.loaded_segs, seg, name)
                    if ll [4] == 'LD':
                        typ, tag, m, n = (int (x) for x in ll [5:9])
                        name = Loaded_Segment.nec_types [typ]
                        if tag == 0:
                            segs = self.segments
                        else:
                            segs = self.seg_by_tag [tag]
                        if m == 0:
                            for s in segs:
                                Loaded_Segment (self.loaded_segs, s, name)
                        else:
                            if n == 0:
                                n = m
                            for i in range (n - 1, m):
                                Loaded_Segment \
                                    (self.loaded_segs, segs [i], name)
                    if ll [4] == 'GN':
                        typ = int (ll [5])
                        if typ >= 0:
                            if self.geo:
                                gidx = max (self.geo)
                                if self.geo [gidx].has_ground is None:
                                    self.geo [gidx].has_ground = True
                    continue
                if status != 'start' and not line:
                    status  = 'start'
                    geo     = None
                    has_gnd = None
                    continue
                if status == 'asap-feed':
                    if splt == 'NODE VOLTS':
                        continue
                    if splt == 'NO. REAL IMAGINARY':
                        continue
                    n, re, im = line.split ()
                    name = 'Excitation'
                    tag  = int (n)
                    Loaded_Segment \
                        (self.loaded_segs, self.seg_by_tag [tag], name)
                    continue
                if status == 'asap-load':
                    if splt == 'SEGMENT OHMS':
                        status = 'start'
                        continue
                    if splt == 'NODE OHMS':
                        continue
                    if splt == 'NO REAL IMAGINARY':
                        continue
                    if splt == 'NO. REAL IMAGINARY':
                        continue
                    n, re, im = line.split ()
                    name = 'Impedance'
                    tag  = int (n)
                    Loaded_Segment \
                        (self.loaded_segs, self.seg_by_tag [tag], name)
                    continue
                if status == 'asap-geo':
                    sn, n1, x1, y1, z1, n2, x2, y2, z2 = \
                        (float (x) for x in line.split ())
                    if z_offset:
                        z1 += z_offset
                        z2 += z_offset
                    e1  = np.array ([x1, y1, z1])
                    e2  = np.array ([x2, y2, z2])
                    n1, n2 = (int (x) for x in (n1, n2))
                    mid = (e1 + e2) / 2
                    if n1 not in self.seg_by_tag:
                        self.seg_by_tag [n1] = e1
                    if n2 not in self.seg_by_tag:
                        self.seg_by_tag [n2] = e2
                    self.segments.append (mid)
                    geo.append ([e1, e2])
                    continue
                if status == 'geo':
                    if not line [-1].isnumeric ():
                        status  = 'start'
                        geo     = None
                        has_gnd = None
                        continue
                    x, y, z, r, e1, e2, n = line.split ()
                    n = int (n)
                    # Single segment case with no pulses
                    if x == '-':
                        self.seg_by_tag [n] = []
                    else:
                        e1, e2 = (abs (int (x)) for x in (e1, e2))
                        if geowire is not None and max (e1, e2) > geowire:
                            if not geo:
                                geo = self.new_geo (has_gnd)
                            geo.append ([])
                        geowire = max (e1, e2)
                        self.seg_by_tag [n] = np.array ([x, y, z])
                        assert geo is not None
                        geo [-1].append ([float (a) for a in (x, y, z)])
                    continue
                if status == 'load':
                    if line.startswith ('PULSE'):
                        txt, l = line.split (':', 1)
                        tag, r, x = l.split (',')
                        tag = int (tag)
                        name = txt.split (',', 1) [-1]
                        if name == 'RESISTANCE,REACTANCE':
                            name = 'Impedance'
                        Loaded_Segment \
                            (self.loaded_segs, self.seg_by_tag [tag], name)
                        continue
                if status == 'source':
                    if line.startswith ('PULSE'):
                        l = line.split (':')[1]
                        tag, v, p = l.split (',')
                        tag = int (tag)
                        name = 'Excitation'
                        Loaded_Segment \
                            (self.loaded_segs, self.seg_by_tag [tag], name)
                        continue
                if status == 'wire':
                    l = line.split ()
                    geo.wires [-1].append ([float (a) for a in l [:3]])
                    continue
                if status == 'necgeo':
                    # Fixme: This should really be lambda-dependent
                    eps = 1e-3
                    started = False
                    ll = line.split ()
                    idx = int (ll [0])
                    x, y, z, l, alpha, beta = (float (a) for a in ll [1:7])
                    tag = int (ll [-1])
                    if tag not in self.seg_by_tag:
                        self.seg_by_tag [tag] = []
                    mid = np.array ([x, y, z])
                    self.seg_by_tag [tag].append (mid)
                    self.segments.append (mid)
                    prev, cur, next = (int (a) for a in ll [8:11])
                    assert cur == idx
                    aprev = abs (prev)
                    if prev == 0 or aprev > idx:
                        geo.append ([])
                        started = True
                    elif aprev != idx - 1 and aprev != idx:
                        geo.append ([])
                        a, b = necidx [aprev]
                        if prev > 0:
                            b += 1
                        geo [-1].append (self.geo [a][b])
                        started = True
                    elif prev == cur and gnd:
                        geo.append ([])
                        started = True
                        gnd = None
                    necidx [idx] = (len (geo) - 1, len (geo [-1]) - 1)
                    alpha = alpha / 180 * np.pi
                    beta  = beta  / 180 * np.pi
                    cos_t = np.cos (alpha)
                    # Unit vector in direction of segment
                    xu = cos_t * np.cos (beta)
                    yu = cos_t * np.sin (beta)
                    zu = np.sin (alpha)
                    uvec = np.array ([xu, yu, zu])
                    # startpoint is midpoint - uvec * (l / 2)
                    st = mid - uvec * (l / 2)
                    # endpoint   is midpoint + uvec * (l / 2)
                    en = mid + uvec * (l / 2)
                    if started:
                        geo [-1].append (st)
                        geo [-1].append (en)
                    else:
                        assert np.linalg.norm (geo [-1][-1] - st) < eps
                        geo [-1].append (en)
                    continue
                # Similar for NEC, MININEC, ASAP:
                if line.startswith ('FREQUENCY'):
                    if ':' in line:
                        f = float (line.split (':') [1].split () [0])
                    else:
                        f = float (line.split () [-1])
                    delimiter = guard
                    continue
                if line.startswith ('IMPEDANCE ='):
                    m = line.split ('(', 1)[1].split (')')[0].rstrip ('J')
                    a, b = (float (x) for x in m.split (','))
                    impedance = a + 1j * b
                    idata = self.idata [f] = Impedance_Data (f, impedance)
                    delimiter = guard
                    continue
                # ASAP antenna impedance
                if line.startswith ('THE ANTENNA IMPEDANCE IS'):
                    re, _, im = line.split () [-3:]
                    assert _ == '+J'
                    impedance = float (re) + 1j * float (im)
                    idata = self.idata [f] = Impedance_Data (f, impedance)
                    delimiter = guard
                    continue
                # NEC2 file
                if 'ANTENNA INPUT PARAMETERS' in line:
                    status = 'antenna-input'
                    continue
                # NEC2 file
                if status == 'antenna-input' and line [0].isnumeric ():
                    l = line.split ()
                    assert len (l) == 11
                    a, b = (float (x) for x in l [6:8])
                    impedance = a + 1j * b
                    idata  = self.idata [f] = Impedance_Data (f, impedance)
                    status = 'start'
                    continue
                # File might end with Ctrl-Z (DOS EOF)
                if line.startswith ('\x1a'):
                    break
                if status == 'antenna-input':
                    continue
                if delimiter == guard:
                    # NEC Radiation pattern specify type of polarization
                    # vs. Major/Minor axis
                    if splt.startswith ('THETA PHI VERTC HORIZ TOTAL'):
                        nec_vh = True
                    if splt.startswith ('THETA PHI MAJOR MINOR TOTAL'):
                        nec_vh = False
                    # Original Basic implementation gain output
                    if line.endswith (',D'):
                        status = 'gnn' # old Basic gain file
                        delimiter = ','
                        f = self.args.default_frequency
                        k = (f,)
                    elif line.startswith ('ANGLE') and line.endswith ('(DB)'):
                        delimiter = None
                        status = 'mininec-gain'
                    # NEC file
                    elif  (   line.startswith ('DEGREES   DEGREES        DB')
                        and line.endswith ('VOLTS/M   DEGREES')
                        ):
                        delimiter = None
                        status = 'nec-gain'
                    elif splt == asap_p:
                        delimiter = None
                        status = 'asap-gain'
                        if not f:
                            f = 300.0
                    if status in gain_fmt:
                        for p in 'H', 'V', 'sum':
                            if not nec_vh and p in ('H', 'V'):
                                continue
                            k = (f, p)
                            gdata = self.gdata [k] = Gain_Data (k, self)
                        continue
                else:
                    if not line or not line [0].isnumeric () or line == '0':
                        delimiter = guard
                        gdata = None
                        status = 'start'
                        continue
                    fields = line.split (delimiter)
                    # Special case of older mininec format, w
                    old_mininec = False
                    if len (fields) == 4 and fields [0][0].isnumeric ():
                        old_mininec = True
                    elif len (fields) < 5 or not fields [0][0].isnumeric ():
                        delimiter = guard
                        gdata = None
                        continue
                    if old_mininec:
                        zen, azi, vp, hp = (float (x) for x in fields [:4])
                        v = 10 ** (vp / 10) + 10 ** (hp / 10)
                        tot = np.log (v) / log10
                    elif status == 'asap-gain':
                        zen, azi, vpl, hpl = (float (x) for x in fields [:4])
                        if vpl <= 0:
                            vp = -999.
                        else:
                            vp = np.log (vpl) / log10 * 10
                        if hpl <= 0:
                            hp = -999.
                        else:
                            hp = np.log (hpl) / log10 * 10
                        if hpl + vpl <= 0:
                            tot = -999.
                        else:
                            tot = np.log (hpl + vpl) / log10 * 10
                    else:
                        zen, azi, vp, hp, tot = (float (x) for x in fields [:5])
                    # GNN-file, mininec gain and nec gain share the format
                    # for the first 5 columns of gain data
                    for p, v in (('H', hp), ('V', vp), ('sum', tot)):
                        if not nec_vh and p in ('H', 'V'):
                            continue
                        gdata = self.gdata [(f, p)]
                        gdata.pattern [(zen, azi)] = v
        for g in self.geo.values ():
            g.fix_wires ()
    # end def read_file

    def plot (self, key = None):
        if key is None and self.gdata:
            key = next (iter (sorted (self.gdata)))
        self.plot_key = key
        self.cur_key  = key
        self.impedance = getattr (self.args, 'system_impedance', None)
        if getattr (self.args, 'as_stl', None):
            self.plot3d_stl (key)
        elif self.do_plotly:
            self.plot_plotly (key)
        else:
            if self.args.mpl_pol_in_1:
                self.mpl_plot_key = self.mpl_plot_keys [0]
            self.plot_matplotlib (key)
    # end def plot

    def plot_plotly (self, key):
        m = {}
        for name in self.plot_names:
            if getattr (self.args, name, None):
                method = getattr (self, name, None)
                if method is None:
                    method = getattr (self, name + '_plotly', None)
                if method is None:
                    print \
                        ( 'Warning: No method for "%(name)s" for plotly'
                        % locals ()
                        )
                else:
                    if name in ('azimuth', 'elevation', 'plot3d'):
                        if not key:
                            raise ValueError ('No gain data to plot')
                        self.data = self.gdata [key]
                        self.plotly_lastfig  = False
                        self.plotly_firstfig = True
                        if name == 'plot3d':
                            if len (self.plot_keys) > 1:
                                w = 0.035
                                if self.args.decibel_style == 'both':
                                    w = 0.1
                                self.legend_width = w
                                self.plotly_fig = make_subplots \
                                    ( rows=1, cols=2
                                    , specs=[ [ {'type': 'surface'}
                                              , {'type': 'xy'}
                                              ]
                                            ]
                                    , column_widths = [1-w, w]
                                    )
                            else:
                                self.legend_width = 0
                                self.plotly_fig = make_subplots \
                                    ( rows=1, cols=1
                                    , specs=[ [ {'type': 'surface'}
                                              ]
                                            ]
                                    , column_widths = [1]
                                    )
                            self.plotly_fig.update (self.plotly_3d_default)
                            self.plotly_fig.layout.title.text = self.title
                        else:
                            self.plotly_fig = go.Figure \
                                (** self.plotly_polar_default)
                        for n, key in enumerate (self.plot_keys):
                            self.plotly_count = n
                            self.plot_key = key
                            self.cur_key  = key
                            self.data = self.gdata [key]
                            if key == self.plot_keys [-1]:
                                self.plotly_lastfig = True
                            method (name)
                            self.plotly_firstfig = False
                    else:
                        method (name)
    # end def plot_plotly

    def plot_matplotlib (self, plotkey):
        dpi  = self.dpi
        x, y = np.array ([self.fig_x, self.fig_y]) / 80 * dpi

        d = {}
        a = {}
        count = 0
        for name in self.plot_names:
            if getattr (self.args, name, None):
                p = dict (projection = 'polar')
                if name == 'plot_vswr':
                    p = {}
                elif name == 'plot3d' or name == 'plot_geo':
                    p = dict (projection = '3d')
                elif name == 'plot_smith':
                    p = dict \
                        ( projection = 'smith'
                        , grid_major_fancy  = True
                        , grid_minor_enable = True
                        , grid_minor_fancy  = True
                        , axes_impedance = self.args.system_impedance
                        , axes_normalize = True
                        , axes_normalize_label = True
                        , axes_labelpos = -1.5-1.1j
                        )
                d [name] = p
                a [name] = dict (arg = count + 1)
                count += 1
        if len (d) > 4:
            args       = [2, 3]
            figsize    = [x * 2 / dpi, y * 3 / dpi]
        if len (d) > 2:
            args       = [2, 2]
            figsize    = [x * 2 / dpi, y * 2 / dpi]
        elif len (d) == 2:
            args       = [1, 2]
            figsize    = [x * 2 / dpi, y / dpi]
        else:
            args       = [1, 1]
            figsize    = [x / dpi, y / dpi]
        self.fig = fig = plt.figure (dpi = dpi, figsize = figsize)
        fig.canvas.manager.set_window_title (self.title)
        self.axes = {}
        self.gui_objects = {}
        if plotkey:
            self.data = self.gdata [plotkey]
        for name in self.plot_names:
            if name not in a:
                continue
            arg = a [name]['arg']
            kw  = d [name]
            self.offset = np.array \
                ([((arg - 1) % 2), ((arg - 1) // 2)]) * .5
            self.axes [name] = fig.add_subplot (*args, arg, **kw)
            method = getattr (self, name, None)
            if method is None:
                method = getattr (self, name + '_matplotlib')
            method (name)
        # Add keypress events only when interactive
        if not self.outfile and plotkey:
            # Add keypress events '+' and '-' and some more
            fig.canvas.mpl_connect ('key_press_event', self.keypress)
            # Remove default keybindings for some keys:
            kmap = dict (yscale = 'l', all_axes = 'a')
            for k in kmap:
                try:
                    rcParams ['keymap.' + k].remove (kmap [k])
                except KeyError:
                    pass
        if self.outfile:
            d = {}
            if self.save_format:
                d.update (format = self.save_format)
            fig.savefig (self.outfile, **d)
            plt.close ()
        else:
            plt.show ()
    # end def plot_matplotlib

    def azimuth (self, name):
        self.desc = self.data.azimuth_text (self.scaler)
        self.lbl_deg = self.data.phis_d [self.phi_angle_idx]
        self.labels  = 'XY'
        if self.mpl_plot_key is not None:
            self.polargains = []
            self.angles     = []
            for dat in self.mpl_by_f [self.mpl_plot_key]:
                pg, self.unscaled = dat.azimuth_gains (self.scaler)
                indexes = np.logical_not (np.isnan (pg))
                self.polargains.append (pg [indexes])
                self.angles.append (dat.phis  [indexes])
        else:
            self.polargains, self.unscaled = self.data.azimuth_gains \
                (self.scaler)
            indexes = np.logical_not (np.isnan (self.polargains))
            self.polargains = self.polargains [indexes]
            self.angles = self.data.phis  [indexes]
        # The unscaled values are not used by matplotlib, so no need to
        # keep multiple copies.
        self.unscaled   = self.unscaled   [indexes]
        self.polarplot (name)
    # end def azimuth

    def elevation (self, name):
        """ Elevation is a little more complicated due to theta counting
            from zenith.
            OK for both 90° and 180° plots:
            self.angles = p2 - self.thetas
            self.polargains = gains1
            OK for both 90° and 180° plots:
            self.angles = p2 + self.thetas
            self.polargains = gains2
            But second half must (both) be flipped to avoid crossover
        """
        self.desc = self.data.elevation_text (self.scaler)
        self.lbl_deg  = 90 - self.data.thetas_d [self.theta_angle_idx]
        self.labels   = None
        p2            = np.pi / 2
        if self.mpl_plot_key is not None:
            self.polargains = []
            self.angles     = []
            for dat in self.mpl_by_f [self.mpl_plot_key]:
                pg, self.unscaled = dat.elevation_gains (self.scaler)
                indexes = np.logical_not (np.isnan (pg))
                self.polargains.append (pg [indexes])
                thetas = dat.thetas
                self.angles.append \
                    (np.append (p2 - thetas, np.flip (p2 + thetas)) [indexes])
        else:
            self.polargains, self.unscaled = self.data.elevation_gains \
                (self.scaler)
            indexes = np.logical_not (np.isnan (self.polargains))
            self.polargains = self.polargains [indexes]
            thetas = self.data.thetas
            self.angles = np.append \
                (p2 - thetas, np.flip (p2 + thetas)) [indexes]
        self.unscaled   = self.unscaled   [indexes]
        self.polarplot (name)
    # end def elevation

    def polarplot (self, name):
        self.angle_name  = name [0].upper () + name [1:]
        if  (  getattr (self.args, 'export_html', None)
            or getattr (self.args, 'show_in_browser', None)
            ):
            self.polarplot_plotly (name)
        else:
            self.polarplot_matplotlib (name)
    # end def polarplot

    plotly_polar_script = """
            var myPlot = document.getElementById('{plot_id}');
            Plotly.relayout (myPlot,
                {'modebar':
                    { 'add' :
                        [   { 'name'  : 'Reset'
                            , 'icon'  : Plotly.Icons.home
                            , 'click' : function (gd)
                              { Plotly.relayout
                                ( gd
                                , { 'polar.radialaxis.range': [0,1]
                                  , 'polar.radialaxis.angle': %(lbl_deg)s
                                  , 'polar.radialaxis.tickangle' : %(tickangle)s
                                  , 'polar.angularaxis.rotation' : 0
                                  }
                                );
                              }
                            }
                        ]
                    }
                });
            """

    def polarplot_plotly (self, name):
        fig  = self.plotly_fig
        nm   = self.angle_name
        tpl  = 'Gain: %%{text}<br>%s: %%{theta}<extra></extra>' % nm
        unit = self.args.dB_unit
        df = dict \
            ( r       = self.polargains
            , theta   = (self.angles / np.pi * 180) % 360
            , name    = self.legend_name
            , mode    = 'lines'
            , visible = True if self.plotly_firstfig else 'legendonly'
            , text    = ['%.2f %s (%.2f dB)' % (u, unit, u - self.maxgain)
                         for u in self.unscaled
                        ]
            , hovertemplate = tpl
            )
        fig.add_trace (go.Scatterpolar (**df))
        if self.plotly_lastfig:
            desc = self.desc
            if len (self.frq_keys) > 1 or len (self.pol_keys) <= 1:
                desc = [d for d in desc if not d.startswith ('Frequency')]
            desc = '<br>'.join (desc)
            # don't use fig.update_layout (title = desc) which will
            # delete title attributes
            fig.layout.title.text = desc
            if self.args.title_font_size:
                fig.layout.title.font.size = self.args.title_font_size
            lbl_deg = self.lbl_deg or 0
            tickangle = 90
            if lbl_deg > 180:
                tickangle = -90
            fig.layout.polar.radialaxis.tickangle = tickangle
            fig.layout.polar.radialaxis.angle = lbl_deg
            fig.layout.polar.radialaxis.range = [0,1]
# Trying to display 'X' and 'Y' on Azimuth plot
# Doesn't work: This doesn't correctly scale and it seems giving
# annotations in polar coordinates is still not possible
#            if self.labels:
#                fig.add_annotation \
#                    ( xref      = 'x domain'
#                    , yref      = 'y domain'
#                    , x         = 0.76
#                    , y         = 0.5
#                    , showarrow = False
#                    , align     = 'left'
#                    , text      = self.labels [0]
#                    , font      = dict (size = 18)
#                    )
#                fig.add_annotation \
#                    ( xref      = 'x domain'
#                    , yref      = 'y domain'
#                    , x         = 0.5
#                    , y         = 1.1
#                    , showarrow = False
#                    , align     = 'center'
#                    , text      = self.labels [1]
#                    , font      = dict (size = 18)
#                    )
            script = self.plotly_polar_script % locals ()
            self.show_plotly (fig, name, script = script)
    # end def polarplot_plotly

    def polarplot_matplotlib (self, name):
        if name not in self.gui_objects:
            self.gui_objects [name] = {}
        ax = self.axes [name]
        ax.set_rmax (1)
        ax.set_rlabel_position (self.lbl_deg  or 0)
        ax.set_thetagrids (range (0, 360, 15))
        if self.labels:
            d = dict (fontsize = 18, transform = ax.transAxes)
            plt.text (1.1, 0.5, self.labels [0], va = 'center', **d)
            plt.text (0.5, 1.1, self.labels [1], ha = 'center', **d)
        off = self.offset + np.array ([0.005, 0.01])
        off = [-.35, -.13]
        obj = plt.text (*off, '\n'.join (self.desc), transform = ax.transAxes)
        self.gui_objects [name]['text'] = obj
        args = dict (linestyle = 'solid', linewidth = 1.5)
        if self.mpl_plot_key is not None:
            l     = self.gui_objects [name]['data'] = []
            entry = self.mpl_by_f [self.mpl_plot_key]
            for gd, pg, angle in zip (entry, self.polargains, self.angles):
                label = gd.key [1]
                obj, = ax.plot (angle, pg, label = label, **args)
                l.append (obj)
            a   = 37.5 / 180 * np.pi
            pos = (0.5 + np.cos (a) * 0.6, 0.5 + np.sin (a) * 0.6)
            ax.legend (loc = 'lower left', bbox_to_anchor = pos)
        else:
            obj, = ax.plot (self.angles, self.polargains, **args)
            self.gui_objects [name]['data'] = obj
        #ax.grid (True)
        self.scaler.set_ticks (ax)
        # Might add color and size labelcolor='r' labelsize = 8
        ax.tick_params (axis = 'y', rotation = 'auto')
        an = self.angle_name
        def format_polar_coord (x, y):
            sc   = self.scaler.invscale (y)
            unit = self.args.dB_unit
            return '%s=%.2f°, Gain=%.2f %s (%.2f dB)' \
                % (an, x / np.pi * 180, sc + self.maxgain, unit, sc)
        ax.format_coord = format_polar_coord
    # end def polarplot_matplotlib

    def plot3d_matplotlib (self, name):
        if name in self.gui_objects and self.gui_objects [name]:
            self.gui_objects [name]['data'].remove ()
            self.gui_objects [name] = {}
        ax = self.axes [name]
        _, gains, X, Y, Z = self.data.plot3d_gains (self.scaler)
        xr, yr, zr = self.scene_ranges ((X, Y, Z))
        ax.set_title (self.title)
        ax.set_xlim (xr)
        ax.set_ylim (yr)
        ax.set_zlim (zr)

        ax.set_xlabel ('X')
        ax.set_ylabel ('Y')
        ax.set_zlabel ('Z')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_zticklabels([])

        ax.format_coord = lambda x, y: ''

        colors = cm.rainbow (gains)
        rc, cc = gains.shape

        surf = ax.plot_surface \
            (X, Y, Z, rcount=rc, ccount=cc, facecolors=colors, shade=False)
        if self.wireframe:
            surf.set_alpha (not self.wireframe)
        self.gui_objects [name] = {}
        self.gui_objects [name]['data'] = surf
    # end def plot3d_matplotlib

    # This is injected as javascript into the figure and hooks to the
    # (documented) legendclick. This is triggered *before* the click
    # action is performed and turn the visibility of all traces to
    # 'legendonly'. After that the button action is triggered and turns
    # makes *only* the clicked-on trace visible. So now the legend
    # buttons work like radio buttons.
    plotly_3d_script = """
            var myPlot = document.getElementById('{plot_id}')
            myPlot.on ( 'plotly_legendclick'
                      , function(clickData) {
                         var xlen = clickData.data.length;
                         //console.log (clickData);
                         for (var i = 0; i < xlen; i++) {
                            clickData.data [i].visible = 'legendonly';
                         }
                        }
                      );"""

    def plot3d_plotly (self, name):
        t, gains, X, Y, Z = self.data.plot3d_gains (self.scaler)
        xr, yr, zr = self.scene_ranges ()
        fig  = self.plotly_fig
        unit = self.args.dB_unit
        if self.args.decibel_style == 'both':
            ticktext = ['%.2f %s (%.2f dB)' % (u + self.maxg, unit, u)
                        for u in self.scaler.ticks
                       ]
        elif self.args.decibel_style == 'absolute':
            ticktext = ['%.2f %s' % (u + self.maxg, unit)
                        for u in self.scaler.ticks
                       ]
        else:
            ticktext = ['%.2f dB' % u for u in self.scaler.ticks]
        # Ensure that the uppermost (0dB) mark is printed
        # This may be slightly off when a pattern is very different for
        # different frequencies
        tickvals = self.scaler.tick_values
        tickvals [0] = gains.max ()
        lgroup  = 'l%d' % self.plotly_count
        visible = True if self.plotly_firstfig else 'legendonly'
        tpl = ('Gain: %%{customdata[0]:.2f} %s (%%{customdata[1]:.2f} dB)<br>'
               'Azimuth: %%{customdata[2]:.2f}° (X: 0°)<br>'
               'Elevation: %%{customdata[3]:.2f}°<extra></extra>'
              % self.args.dB_unit
              )

        colorbar_xpos = 1.02
        if self.legend_width:
            colorbar_xpos = 0.98 - self.legend_width
        key = self.legend_name
        fig.add_trace \
            ( go.Surface
                ( x = X, y = Y, z = Z
                , surfacecolor = gains
                , colorscale   = 'rainbow'
                , visible      = visible
                , legendgroup  = lgroup
                , name         = key
                , colorbar = dict
                    ( tickvals = tickvals
                    , ticktext = ticktext
                    , x = colorbar_xpos, y = 0.49
                    , xpad = 0
                    )
                , customdata    = t
                , hovertemplate = tpl
                )
            , row = 1, col = 1
            )
        if len (self.plot_keys) > 1:
            fig.add_trace \
                ( go.Scatter
                    ( dict (x = [1.], y = [1.], line = dict (color = 'white'))
                    , legendgroup = lgroup
                    , visible     = visible
                    , showlegend  = True
                    , name        = key
                    )
                , row = 1, col = 2
                )
        if self.plotly_lastfig:
            fig.layout.update \
                ( legend = dict
                    ( itemclick       = 'toggle'
                    , itemdoubleclick = 'toggle'
                    )
                , xaxis = dict
                    ( showticklabels  = False
                    )
                , yaxis = dict
                    ( showticklabels  = False
                    )
                ,  scene = dict
                    ( xaxis = dict (range = xr, showticklabels = False)
                    , yaxis = dict (range = yr, showticklabels = False)
                    , zaxis = dict (range = zr, showticklabels = False)
                    )
                )
            self.show_plotly (fig, name, script = self.plotly_3d_script)
    # end def plot3d_plotly

    def plot3d_stl (self, plotkey):
        if not plotkey:
            raise ValueError ('No gain data to plot')
        self.data = self.gdata [plotkey]
        t, gains, X, Y, Z = self.data.plot3d_gains (self.scaler)
        tri_e = []
        tri_a = []
        ele, azi = X.shape
        for e1, e2 in pairwise (range (ele)):
            for a1, a2 in pairwise (range (azi)):
                tri_e.append (np.array ([(e1, e1, e2)]))
                tri_a.append (np.array ([(a1, a2, a1)]))
                tri_e.append (np.array ([(e2, e1, e2)]))
                tri_a.append (np.array ([(a1, a2, a2)]))
        tri_e = np.array (tri_e)
        tri_a = np.array (tri_a)
        l = len (tri_a)

        data = np.zeros (l, dtype = stl.mesh.Mesh.dtype)
        mesh = stl.mesh.Mesh (data, remove_empty_areas = False)
        mesh.x [:] = np.reshape (X [tri_e, tri_a], (l, 3))
        mesh.y [:] = np.reshape (Y [tri_e, tri_a], (l, 3))
        mesh.z [:] = np.reshape (Z [tri_e, tri_a], (l, 3))

        fn = self.args.as_stl
        if '%' in self.args.as_stl:
            fn = self.args.as_stl % plotkey
        if not fn.endswith ('.stl'):
            fn = fn + '.stl'
        mesh.save (fn)
    # end def plot3d_stl

    def prepare_vswr (self):
        z0   = self.impedance
        X    = []
        Y    = []
        Z    = []
        imag = []
        real = []
        xabs = []
        xphi = []
        for key in self.idata:
            idt = self.idata [key]
            z   = idt.impedance
            rho = np.abs ((z - z0) / (z + z0))
            imag.append (z.imag)
            real.append (z.real)
            xabs.append (np.abs   (z))
            xphi.append (np.angle (z) * 180 / np.pi)
            X.append (idt.frequency)
            Y.append ((1 + rho) / (1 - rho))
            Z.append (z)
        min_idx = np.argmin (Y)
        self.min_x = X [min_idx]
        if self.args.target_swr_frequency:
            if not X [0] <= self.args.target_swr_frequency <= X [-1]:
                print \
                    ( "Warning: SWR target frequency %.2f not in range, ignored"
                    % self.args.target_swr_frequency
                    , file = sys.stderr
                    )
                self.args.target_swr_frequency = None
        self.min_f = min (X)
        self.max_f = max (X)
        self.band  = {}
        for n in self.args.band:
            fmin, fmax = self.args.band [n]
            in_band = self.min_f <= fmin <= self.max_f
            in_band = in_band or self.min_f <= fmax <= self.max_f
            in_band = in_band or fmin <= self.min_f and self.max_f <= fmax
            if in_band:
                self.band [n] = self.args.band [n]
        return [np.array (v) for v in (X, Y, real, imag, xabs, xphi, Z)]
    # end def prepare_vswr

    def plot_vswr_matplotlib (self, name):
        ax = self.axes [name]
        ax.set_title  (self.title)
        ax.set_xlabel ('Frequency (MHz)')
        ax.set_ylabel ('VSWR', color = self.c_vswr)
        X, Y, real, imag, xabs, xphi, Z = self.prepare_vswr ()
        strf  = ticker.FormatStrFormatter
        min_y = min (Y)
        max_y = max (Y)
        ax.plot (X, Y, linewidth = 2)
        ax.grid (color = blend (self.c_vswr), axis = 'y')
        ax.grid (color = '#B0B0B0', axis = 'x')
        ax.tick_params (axis = 'y', colors = self.c_vswr)
        pr = Plot_Range (Y, 1)
        max_y_r = pr.rng [1]
        ax.set (**pr.as_matplot ())
        ax.yaxis.set_major_formatter (pr.fmt ())
        #ax.xaxis.set_major_formatter (strf ('%.1f MHz'))
        tg = self.args.target_swr_frequency
        if tg is not None:
            c = self.args.swr_target_color
            ax.axvline (x = tg, color = c, linestyle = 'dashed')
        c = self.args.swr_min_color
        if c and c.lower () != 'none':
            ax.axvline (x = self.min_x, color = c, linestyle = 'dashed')
        if self.args.swr_show_impedance:
            self.fig.subplots_adjust (right=0.75)
            ax2 = ax.twinx ()
            ax3 = ax.twinx ()
            ax2.tick_params (axis = 'y', colors = self.c_real)
            ax3.tick_params (axis = 'y', colors = self.c_imag)
            ax3.spines ['right'].set_position (("axes", 1.2))
            if self.args.swr_plot_impedance_angle:
                ax2.set_ylabel ("|Z|", color = self.c_real)
                ax2.plot (X, xabs, color = self.c_real, linewidth = 0.9)
                pr = Plot_Range (xabs)
                ax2.set (**pr.as_matplot ())
                ax2.yaxis.set_major_formatter (pr.fmt (ohm))
                ax3.set_ylabel ("phi (Z)", color = self.c_imag)
                ax3.plot (X, xphi, color = self.c_imag, linewidth = 0.9)
                yt = np.arange (-180, 180 + 30, 30)
                ax3.set (ylim = (-180, 180), yticks = yt)
                ax3.yaxis.set_major_formatter (strf ('%.0f°'))
            else:
                ax2.set_ylabel ("Z (real)", color = self.c_real)
                ax2.plot (X, real, color = self.c_real, linewidth = 0.9)
                pr = Plot_Range (real)
                ax2.set (**pr.as_matplot ())
                ax2.yaxis.set_major_formatter (pr.fmt (ohm))
                ax3.set_ylabel ("Z (imag)", color = self.c_imag)
                ax3.plot (X, imag, color = self.c_imag, linewidth = 0.9)
                pr = Plot_Range (imag)
                ax3.set (**pr.as_matplot ())
                ax3.yaxis.set_major_formatter (pr.fmt (ohm))
        if self.args.swr_show_bands:
            y1, y2 = ax.get_ylim ()
            x1, x2 = ax.get_xlim ()
            for b in self.band:
                l, h = self.band [b]
                l = max (l, x1)
                h = min (h, x2)
                ax.fill_between ([l, h], y1, y2, color = '#CCFFCC')
                pos = ((l + h) / 2, 0.90 * max_y_r)
                ax.annotate \
                    ( '%s\nband' % b
                    , xytext = pos
                    , xy     = pos
                    , ha     = 'center'
                    )
    # end def plot_vswr_matplotlib

    def add_plotly_df (self, yname, color = None, axisname = None, **kw):
        """ Add yname in dataframe self.df to self.fig
        """
        d = dict (x = self.df ["Frequency"], y = self.df [yname], name = yname)
        d.update (line = dict (width = 1.5))
        d.update (kw)
        if color:
            if 'line' in d:
                d ['line']['color'] = color
            else:
                d.update (line = dict (color = color))
        if axisname:
            d.update (yaxis = axisname)
        self.fig.add_trace (go.Scatter (**d))
    # end def add_plotly_df

    def plot_vswr_plotly (self, name):
        X, Y, real, imag, xabs, xphi, Z = self.prepare_vswr ()
        df = pd.DataFrame ()
        df ['Frequency'] = X
        df ['VSWR']      = Y
        df ['Z (real)']  = real
        df ['Z (imag)']  = imag
        df ['|Z|']       = xabs
        df ['phi (Z)']   = xphi
        self.df = df
        self.fig = fig = go.Figure ()
        layout = self.plotly_line_default
        lstyle = dict (color = self.c_vswr, width = 3.5)
        self.add_plotly_df ("VSWR", line = lstyle)
        y = layout ['layout']['yaxis']
        y.update (**Plot_Range (Y, 1).as_plotly ())
        layout ['layout']['title']['text'] = self.title
        layout ['layout']['yaxis']['title'].update  (text = "VSWR")
        layout ['layout']['xaxis'].update \
            (title = dict (text = 'Frequency (MHz)'))
        if self.args.swr_show_impedance:
            y2 = layout ['layout']['yaxis2']
            y2 ['ticksuffix'] = ohm
            y3 = layout ['layout']['yaxis3']
            if self.args.swr_plot_impedance_angle:
                self.add_plotly_df ("|Z|", self.c_real, "y2")
                y2 ['title'].update (text = "|Z|")
                self.add_plotly_df ("phi (Z)", self.c_imag, "y3")
                y2.update (**Plot_Range (xabs).as_plotly ())
                y3 ['title'].update (text = "phi (Z)")
                y3.update (range = [-180, 180], dtick = 30)
                y3 ['ticksuffix'] = '°'
            else:
                self.add_plotly_df ("Z (real)", self.c_real, "y2")
                y2 ['title'].update (text = "Z (real)")
                y2.update (**Plot_Range (real).as_plotly ())
                self.add_plotly_df ("Z (imag)", self.c_imag, "y3")
                y3 ['title'].update (text = "Z (imag)")
                y3.update (**Plot_Range (imag).as_plotly ())
                y3 ['ticksuffix'] = ohm
        if self.args.swr_show_bands:
            shapes = layout ['layout']['shapes'] = []
            for b in self.band:
                l, h = self.band [b]
                d = dict \
                    ( type       = 'rect'
                    , yref       = 'paper'
                    , x0         = max (l, self.min_f)
                    , y0         = 0
                    , x1         = min (h, self.max_f)
                    , y1         = 1
                    , fillcolor  = '#CCFFCC'
                    , line_width = 0
                    , layer      = 'below'
                    )
                fig.add_annotation \
                    ( x         = (l + h) / 2
                    , y         = 0.98
                    , yref      = 'paper'
                    , text      = '<b>%s<br>band</b>' % escape (b)
                    , showarrow = False
                    )
                shapes.append (d)
        fig.update (layout)
        tg = self.args.target_swr_frequency
        if tg is not None:
            c = self.args.swr_target_color
            fig.add_vline (x = tg, line_dash = "dash", line_color = c)
        c = self.args.swr_min_color
        if c and c.lower () != 'none':
            fig.add_vline (x = self.min_x, line_dash = "dash", line_color = c)
        self.show_plotly (fig, name)
    # end def plot_vswr_plotly

    def scene_ranges (self, matrix = None, add_ground = False):
        """ Create cubic bounding box to force equal aspect ratio
            If matrix is not given, we concatenate *all* gains.
        """
        if matrix is None:
            matrix = self.all_gains ()
        x, y, z = matrix
        min_x = x.min ()
        max_x = x.max ()
        min_y = y.min ()
        max_y = y.max ()
        min_z = z.min ()
        max_z = z.max ()
        if add_ground and min_z > 0:
            min_z = 0
        max_range = np.array \
            ([ max_x - min_x, max_y - min_y, max_z - min_z ]).max() / 2.0
        mid_x = (max_x + min_x) / 2
        mid_y = (max_y + min_y) / 2
        mid_z = (max_z + min_z) / 2
        xr = np.array ([mid_x - max_range, mid_x + max_range])
        yr = np.array ([mid_y - max_range, mid_y + max_range])
        zr = np.array ([mid_z - max_range, mid_z + max_range])
        # Avoid that something isn't shown due to rounding errors
        if xr [0] > min_x:
            xr [0] = min_x
        if xr [1] < max_x:
            xr [1] = max_x
        if yr [0] > min_y:
            yr [0] = min_y
        if yr [1] < max_y:
            yr [1] = max_y
        if zr [0] > min_z:
            zr [0] = min_z
        if zr [1] < max_z:
            zr [1] = max_z
        if add_ground and min_z == 0:
            zr = np.array ([min_z, min_z + 2 * max_range])
        return np.array ([xr, yr, zr])
    # end def scene_ranges

    def plot_geo_plotly (self, name):
        gidx = min (self.geo)
        xr, yr, zr = self.scene_ranges \
            (np.concatenate (self.geo [gidx]).T, self.geo [gidx].has_ground)
        fig = px.line_3d ()
        fig.update (self.plotly_3d_default)
        fig.layout.title.text = self.title
        geo  = []
        for n, g in enumerate (self.geo [gidx]):
            if geo:
                geo.append ([np.nan, np.nan, np.nan])
            geo.extend (g)
        geo = np.array (geo)
        d = dict (mode = 'lines', connectgaps = False, name = 'Geometry')
        d.update (marker = dict (color = self.colormap [0]))
        d.update (line = dict (width = 5))
        d ['x'], d ['y'], d ['z'] = geo.T
        fig.add_trace (go.Scatter3d (**d))
        for i, name in enumerate (sorted (self.loaded_segs)):
            segs = self.loaded_segs [name]
            coord = []
            for s in segs:
                coord.append (s.coord)
            coord = np.array (coord, dtype = float)
            x, y, z = coord.T
            marker = dict (color = self.colormap [i + 1], size = 3)
            d = dict (marker = marker, name = name, mode = 'markers')
            fig.add_trace (go.Scatter3d (x = x, y = y, z = z, **d))
        fig.layout.scene.update \
            ( dict
                ( xaxis = dict (range = xr)
                , yaxis = dict (range = yr)
                , zaxis = dict (range = zr)
                )
            )
        if self.geo [gidx].has_ground:
            x, y = np.meshgrid (xr, yr)
            z = np.zeros (x.shape)
            d = dict (showscale = False, colorscale = ['#6cbe6c'] * 2)
            d.update (opacity = 0.9)
            fig.add_trace (go.Surface (x = x, y = y, z = z, **d))
        fig.layout.legend = dict (itemsizing = 'constant')
        self.show_plotly (fig, name)
    # end def plot_geo_plotly

    def plot_geo_matplotlib (self, name):
        ax = self.axes [name]
        # equal aspect ratio
        gidx = min (self.geo)
        xr, yr, zr = self.scene_ranges \
            (np.concatenate (self.geo [gidx]).T, self.geo [gidx].has_ground)
        ax.set_xlim (*xr)
        ax.set_ylim (*yr)
        ax.set_zlim (*zr)
        ax.set_xlabel ('X')
        ax.set_ylabel ('Y')
        ax.set_zlabel ('Z')
        ax.set_title  (self.title)
        for g in self.geo [gidx]:
            g = np.array (g)
            x, y, z = g.T
            d = dict (color = self.colormap [0], linewidth = 3)
            ax.plot (x, y, z, **d)
        for i, name in enumerate (sorted (self.loaded_segs)):
            segs = self.loaded_segs [name]
            coord = []
            for s in segs:
                coord.append (s.coord)
            coord = np.array (coord, dtype = float)
            x, y, z = coord.T
            d = dict (color = self.colormap [i + 1], marker = 'o')
            ax.scatter (x, y, z, **d)
        if self.geo [gidx].has_ground:
            x, y = np.meshgrid (xr, yr)
            z = np.zeros (x.shape)
            d = dict (color = '#6cbe6c', alpha = 0.9)
            ax.plot_surface (x, y, z, **d)
    # end def plot_geo_matplotlib

    def plot_smith_plotly (self, name):
        X, Y, real, imag, xabs, xphi, Z = self.prepare_vswr ()
        real_norm = real / self.args.system_impedance
        imag_norm = imag / self.args.system_impedance
        text = ['%.1f MHz' % x for x in X]
        data = np.stack ([real, imag], axis=-1)
        tpl = \
            ( '%%{text}<br>'
              'real: %%{real:.2f} (%%{customdata[0]:.1f} %s)<br>'
              'imag: %%{imag:.2f} (%%{customdata[1]:.1f} %s)'
              '<extra></extra>'
            ) % (Omega, Omega)
        self.fig = fig = go.Figure ()
        smith = go.Scattersmith \
            ( text          = text
            , imag          = imag_norm
            , real          = real_norm
            , hovertemplate = tpl
            , customdata    = data
            )
        fig.add_trace (smith)
        fig.update (self.plotly_smith_default)
        fmt = '$Z_0 = %.1f\,\Omega$'
        if self.args.system_impedance == int (self.args.system_impedance):
            fmt = '$Z_0 = %.0f\,\Omega$'
        fig.add_annotation \
            ( x         = 0.10
            , y         = 0.15
            , xref      = 'paper'
            , yref      = 'paper'
            , text      = fmt % self.args.system_impedance
            , showarrow = False
            )
        fig.layout.title.text = 'Smith chart for %s' % self.title
        self.show_plotly (fig, name)
    # end def plot_smith_plotly

    def plot_smith_matplotlib (self, name):
        X, Y, real, imag, xabs, xphi, Z = self.prepare_vswr ()
        ax = self.axes [name]
        d  = dict (markevery = 1, datatype  = 'Z', markersize = 2)
        ax.plot (Z, **d)
    # end def plot_smith_matplotlib

    def show_plotly (self, fig, name, script = None):
        """ We can pass a config option into fig.show and fig.write_html,
            allowing scroll seems to be the default for 3d view.
            At some point we may want to set different config options
            for different plots.
            Note that the script is passed as post_script to the html.
            It is triggered after loading the figure.
        """
        config = dict (displaylogo = False)
        d = {}
        if self.args.html_export_option and self.args.export_html:
            d.update (include_plotlyjs = self.args.html_export_option)
        if not self.args.show_plotly_logo:
            d.update (config = config)
        if script is not None:
            d.update (post_script = script)
        if self.args.output_file and self.save_format:
            fig.write_image (self.args.output_file, format = self.save_format)
        elif self.args.export_html:
            fn = self.args.export_html + '-' + name + '.html'
            fig.write_html (fn, **d)
        else:
            fig.show (**d)
    # end def show_plotly

    # For animation:

    def update_display (self):
        for name in self.gui_objects:
            if name not in self.update_names:
                continue
            gui = self.gui_objects [name]
            data_obj = gui ['data']
            if self.mpl_plot_key is not None:
                assert name != 'plot3d'
                entry = self.mpl_by_f [self.mpl_plot_key]
                for dat, dobj in zip (entry, data_obj):
                    gains, g = getattr (dat, name + '_gains')(self.scaler)
                    dobj.set_ydata (gains)
                    gdata = dat
            else:
                gdata = self.gdata [self.plot_key]
                if name == 'plot3d':
                    self.data = gdata
                    self.plot3d_matplotlib ('plot3d')
                else:
                    gains, g = getattr (gdata, name + '_gains')(self.scaler)
                    data_obj.set_ydata (gains)
            if name != 'plot3d':
                text_obj = gui ['text']
                text = getattr (gdata, name + '_text')(self.scaler)
                text_obj.set_text ('\n'.join (text))
                if self.cur_scaler != self.scaler:
                    self.scaler.set_ticks (self.axes [name])
        self.fig.canvas.draw ()
        self.cur_key    = self.plot_key
        self.cur_scaler = self.scaler
    # end def update_display

    def keypress (self, event):
        idx     = self.plot_keys.index (self.plot_key)
        if self.mpl_plot_key is not None:
            midx    = self.mpl_plot_keys.index (self.mpl_plot_key)
        changed = False
        if event.key == "+":
            if self.mpl_plot_key is not None:
                if midx < len (self.mpl_plot_keys) - 1:
                    self.mpl_plot_key = self.mpl_plot_keys [midx + 1]
                    changed = True
            else:
                if idx < len (self.plot_keys) - 1:
                    self.plot_key = self.plot_keys [idx + 1]
        elif event.key == "-":
            if self.mpl_plot_key is not None:
                if midx > 0:
                    self.mpl_plot_key = self.mpl_plot_keys [midx - 1]
                    changed = True
            else:
                if idx > 0:
                    self.plot_key = self.plot_keys [idx - 1]
        elif event.key == 'a':
            self.scaler = self.scalers ['arrl']
            self.update_display ()
        elif event.key == 'l':
            self.scaler = self.scalers ['linear']
            self.update_display ()
        elif event.key == 'd':
            self.scaler = self.scalers ['linear_db']
            self.update_display ()
        elif event.key == 'v':
            self.scaler = self.scalers ['linear_voltage']
            self.update_display ()
        elif event.key == 'w':
            self.wireframe = not self.wireframe
            if 'plot3d' in self.gui_objects:
                gui = self.gui_objects ['plot3d']['data']
                gui.set_alpha (not self.wireframe)
                self.fig.canvas.draw ()
        if self.cur_key != self.plot_key or changed:
            self.update_display ()
    # end def keypress

# end class Gain_Plot

class SortingHelpFormatter (HelpFormatter):

    def add_arguments (self, actions):
        actions = sorted (actions, key = self.argsort)
        super ().add_arguments (actions)
    # end def add_arguments

    @staticmethod
    def argsort (action):
        x = action.option_strings
        if not x:
            return ''
        for opt in tuple (x):
            if opt.startswith ('--'):
                return opt
    # end def argsort

# end class SortingHelpFormatter

class SortingArgumentParser (ArgumentParser):
    def __init__ (self, *args, **kw):
        super ().__init__ (*args, formatter_class = SortingHelpFormatter, **kw)
    # end def __init__
# end class SortingArgumentParser

ham_bands = dict \
   (( ('70cm', (430.0,  440.0))
    , ('2m',   (144.0,  146.0))
    , ('6m',   ( 50.0,   52.0))
    , ('10m',  ( 28.0,   29.7))
    , ('12m',  ( 24.89,  24.99))
    , ('15m',  ( 21.0,   21.45))
    , ('17m',  ( 18.068, 18.168))
    , ('20m',  ( 14.0,   14.35))
    , ('30m',  ( 10.1,   10.15))
    , ('40m',  (  7.0,    7.2))
    , ('60m',  (  5.3513, 5.3665))
    , ('80m',  (  3.5,    3.8))
    , ('160m', (  1.81,   1.95))
    , ('630m', (  0.472,  0.479))
   ))

def options_general (cmd = None):
    if cmd is None:
        cmd = SortingArgumentParser ()
    cmd.add_argument \
        ( '--dpi'
        , help    = 'Resolution for matplotlib, default = %(default)s'
        , type    = int
        , default = 80
        )
    cmd.add_argument \
        ( '--width'
        , help    = 'Width of the plot in pixels, default = 512 for'
                    ' matplotlib, 700 for plotly'
        , type    = int
        )
    cmd.add_argument \
        ( '--height'
        , help    = 'Height of the plot in pixels, default = 384 for'
                    ' matplotlib, 500 for plotly'
        , type    = int
        )
    cmd.add_argument \
        ( '--title'
        , help    = 'Title for plot, overrides filename or '
                    'information in parsed file'
        )
    cmd.add_argument \
        ( '--output-file'
        , help    = 'Output file, default is interactive'
        )
    cmd.add_argument \
        ( "--dB-unit"
        , help    = "Unit to print in diagrams, default=%(default)s,"
                    " for antenna simulation the default is usually"
                    " correct, for measurements of antennas the unit"
                    " might, e.g. be dBm of the receiver"
        , default = "dBi"
        )
    if px is not None:
        cmd.add_argument \
            ( "-H", "--export-html"
            , help    = "Filename-prefix to export graphics as html, "
                        "type of graphics (azimuth, elevation, ..) is appended"
            )
        cmd.add_argument \
            ( "--html-export-option"
            , help    = "Option passed to write_html include_plotlyjs option, "
                        "default is to include all javascript in generated "
                        "output file. To leave out the javascript, specify "
                        "'directory', this needs the plotly.min.js in the "
                        "same directory as the output. See plotly docs for "
                        "details."
            )
        cmd.add_argument \
            ( '--legend-x'
            , help    = 'Plotly x-position of legend, default=%(default)s'
            , type    = float
            , default = 1.02
            )
        cmd.add_argument \
            ( "--save-format"
            , help    = "Format of file with --output-file option, "
                        "default = %(default)s"
            , default = 'png'
            )
        cmd.add_argument \
            ( "-S", "--show-in-browser"
            , help    = "Produce a plot shown interactively in a running "
                        "browser"
            , action  = 'store_true'
            )
        cmd.add_argument \
            ( "--show-plotly-logo"
            , help    = "Show plotly logo in menu"
            , action  = 'store_true'
            )
    return cmd
# end def options_general

deci_styles = ('absolute', 'relative', 'both')

def options_gain (cmd = None):
    """ Options that have to do with displaying gains, i.e.
        plotting of azimuth/elevation or 3d
    """
    if cmd is None:
        cmd = SortingArgumentParser ()
    cmd.add_argument \
        ( '--azimuth'
        , help    = 'Do an azimuth plot'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--angle-azimuth'
        , help    = 'Azimuth angle to use for elevation plot, default is '
                    'maximum gain angle'
        , type    = float
        )
    cmd.add_argument \
        ( '--decibel-style'
        , help    = 'Decibel style for plotly 3D color bar,'
                    ' one of %s, the default prints the relative value'
                    ' in parentheses' % ', '.join (deci_styles)
        , default = 'both'
        )
    cmd.add_argument \
        ( '--default-frequency'
        , help    = 'Default frequency for input formats that do not '
                    'specify a frequency (e.g. the old MININEC gain '
                    '(.GNN) format), if no unit (e.g. GHz) is given '
                    'it defaults to MHz'
        , default = 0.0
        )
    cmd.add_argument \
        ( '--elevation'
        , help    = 'Do an elevation plot'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--angle-elevation'
        , help    = 'Elevation angle to use for azimuth plot, default is '
                    'maximum gain angle'
        , type    = float
        )
    cmd.add_argument \
        ( '--interpolate-azimuth-step'
        , help    = 'Interpolate azimuth angles from 0 to 360 with this'
                    ' stepsize, default is to not interpolate'
        , type    = float
        )
    cmd.add_argument \
        ( '--margin-3d'
        , help    = 'Margin around 3D plot in pixel for plotly backend'
        , type    = int
        , default = 20
        )
    cmd.add_argument \
        ( '--matplotlib-polarization-in-one'
        , dest    = 'mpl_pol_in_1'
        , help    = 'Plot polarizations for one frequency in one plot'
                    ' for matplotlib'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '-0', '--maxgain'
        , help    = 'Maximum gain at 0dB default is maxium from data'
        , type    = float
        )
    cmd.add_argument \
        ( '--polarization'
        , help    = 'Plot given polarization keys, can be specified'
                    ' multiple times, default is to plot only sum'
        , action  = 'append'
        , default = []
        )
    cmd.add_argument \
        ( '--plot3d', '--3d', '--plot-3d', '--3D'
        , help    = 'Do a 3D plot'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--scaling-method'
        , help    = 'Scaling method to use, default=%%(default)s'
        , default = 'arrl'
        , choices = ['arrl', 'linear', 'linear_db', 'linear_voltage']
        )
    cmd.add_argument \
        ( '--scaling-mindb'
        , help    = 'Minimum decibels linear dB scaling, default=%(default)s'
        , type    = float
        , default = -50
        )
    cmd.add_argument \
        ( '--title-font-size'
        , help    = 'Title/legend font size in pt '
                    '(currently only used in plotly)'
        , type    = int
        )
    cmd.add_argument \
        ( '--wireframe'
        , help    = 'Show 3D plot as a wireframe (not solid)'
        , action  = 'store_true'
        )
    return cmd
# end def options_gain

def options_geo (cmd = None):
    """ Options for displaying geometry
    """
    if cmd is None:
        cmd = SortingArgumentParser ()
    cmd.add_argument \
        ( '--plot-geo', '--geo'
        , help    = 'Plot Geometry'
        , action  = 'store_true'
        )
    return cmd
# end def options_geo

def options_stl (cmd = None):
    if cmd is None:
        cmd = SortingArgumentParser ()
    cmd.add_argument \
        ( '--as-stl'
        , help    = 'Output 3d geometry as STL'
        )
    return cmd
# end def options_stl

def options_swr (cmd = None):
    if cmd is None:
        cmd = SortingArgumentParser ()
    cmd.add_argument \
        ( '--axis-3-position'
        , help    = 'Plotly position of the 3rd y-axis relative to the plot'
        , type    = float
        , default = 0.98
        )
    cmd.add_argument \
        ( '--band'
        , help    = 'Band to highlight in VSWR plot, default are ham'
                    ' bands in Austria, Format: name:flow,fhi'
        , default = []
        , action  = 'append'
        )
    cmd.add_argument \
        ( '--plot-smith', '--smith'
        , help    = 'Plot impedances in Smith chart'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--system-impedance'
        , help    = 'System impedance Z0, default=%(default)s'
        , type    = float
        , default = 50
        )
    cmd.add_argument \
        ( '--plot-vswr', '--swr', '--vswr', '--plot-swr'
        , help    = 'Plot voltage standing wave ratio (VSWR)'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "--target-swr-frequency", "--target-vswr-frequency"
        , help    = "In SWR plot, draw a vertical line at this frequency"
        , type    = float
        )
    cmd.add_argument \
        ( "--swr-min-color", "--vswr-min-color"
        , help    = "Draw minimum SWR vertical line in this color, use "
                    "'none' to not draw the line"
        , default = 'green'
        )
    cmd.add_argument \
        ( "--swr-target-color", "--vswr-target-color"
        , help    = "If the --target-swr-frequency option is given, draw "
                    "vertical line in this color"
        , default = 'grey'
        )
    cmd.add_argument \
        ( "--swr-plot-impedance-angle"
        , help    = "In SWR plot impedance as abs/angle, default is real/imag"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "--swr-show-bands"
        , help    = "Show (ham-radio) bands in SWR plot"
        , action  = "store_true"
        )
    cmd.add_argument \
        ( "--swr-show-impedance"
        , help    = "Show impedance in SWR plot"
        , action  = "store_true"
        )
    return cmd
# end def options_swr

def process_args (cmd, argv = sys.argv [1:]):
    args = cmd.parse_args (argv)
    hb = dict (ham_bands)
    if getattr (args, 'band', None) is not None:
        for b in args.band:
            try:
                n, r = b.split (':')
            except ValueError as err:
                cmd.print_usage ()
                exit ('Error in band: %s' % err)
            n = n.strip ()
            try:
                l, h = (float (x) for x in r.split (','))
            except ValueError as err:
                cmd.print_usage ()
                exit ('Error in band: %s' % err)
            if h <= l:
                if n in hb:
                    del hb [n]
            else:
                hb [n] = (l, h)
        args.band = hb
    if getattr (args, 'default_frequency'):
        df = args.default_frequency.strip ()
        if df.endswith ('Hz'):
            if df [-3] == 'T':
                args.default_frequency = float (df [:-3]) * 1e6
            elif df [-3] == 'G':
                args.default_frequency = float (df [:-3]) * 1e3
            elif df [-3] == 'M':
                args.default_frequency = float (df [:-3])
            elif df [-3] == 'k':
                args.default_frequency = float (df [:-3]) / 1e3
            else:
                args.default_frequency = float (df [:-2]) / 1e6
        else:
            args.default_frequency = float (df)
    if getattr (args, 'decibel_style', None) is not None:
        if args.decibel_style not in deci_styles:
            cmd.print_usage ()
            exit ('Invalid decibel-style: "%s"' % args.decibel_style)
    if getattr (args, 'polarization', None) is not None:
        args.polarization = dict.fromkeys (args.polarization)
    return args
# end def process_args

def main (argv = sys.argv [1:], pic_io = None):
    """ The pic_io argument is for testing:
        We put the picture into that file-like object if the pic_io
        is not None.
    """
    cmd = options_general ()
    options_gain (cmd)
    options_geo  (cmd)
    if stl is not None:
        options_stl (cmd)
    options_swr  (cmd)
    cmd.add_argument \
        ( 'filename'
        , help    = 'File to parse and plot'
        )
    args = process_args (cmd, argv)
    # For regression testing:
    if pic_io is not None:
        args.output_file = pic_io
        args.save_format = 'png'
    gp = Gain_Plot.from_file (args)
    gp.compute ()

    all_plot_types = set \
        (( 'azimuth', 'elevation', 'plot3d', 'plot_vswr', 'plot_geo'
        ,  'plot_smith'
        ))
    set_types = sum (bool (getattr (args, p)) for p in all_plot_types)
    # Default is all
    if  not set_types:
        if getattr (args, 'as_stl', None):
            args.plot3d = True
        else:
            args.plot3d = args.elevation = args.azimuth = args.plot_vswr = True
    if getattr (args, 'as_stl', None):
        all_but_3d = all_plot_types - set (('plot3d',))
        all_but_3d = sum (bool (getattr (args, p)) for p in all_but_3d)
        if all_but_3d:
            print ('Warning: Output as-stl only supports 3D plot')
    gp.plot ()
# end def main

if __name__ == '__main__':
    main ()
