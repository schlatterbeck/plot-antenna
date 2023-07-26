#!/usr/bin/python3

import sys
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from html import escape
from bisect import bisect
from mpl_toolkits.mplot3d import Axes3D
from argparse import ArgumentParser, HelpFormatter
from matplotlib import cm, __version__ as matplotlib_version, rcParams, ticker
from matplotlib.widgets import Slider
from matplotlib.patches import Rectangle
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import pandas         as pd
except ImportError:
    px = None

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

class Gain_Data:

    def __init__ (self, parent, f):
        self.parent   = parent
        self.f        = f
        self.pattern  = {}
    # end def __init__

    def compute (self):
        thetas = set ()
        phis   = set ()
        gains  = []
        for theta, phi in sorted (self.pattern):
            gains.append (self.pattern [(theta, phi)])
            thetas.add (theta)
            phis.add   (phi)
        self.thetas_d = np.array (list (sorted (thetas)))
        self.phis_d   = np.array (list (sorted (phis)))
        self.thetas   = self.thetas_d * np.pi / 180
        self.phis     = self.phis_d   * np.pi / 180
        self.maxg     = max (gains)
        self.gains    = np.reshape \
            (np.array (gains), (self.thetas.shape [0], -1))
        idx = np.unravel_index (self.gains.argmax (), self.gains.shape)
        self.theta_maxidx, self.phi_maxidx = idx
        # Special case: If theta is 0° or 180° recompute phi_maxidx
        # since in that case all values are the same at that theta angle
        if self.thetas_d [self.theta_maxidx] == 0:
            self.phi_maxidx = self.gains [1].argmax ()
        elif self.thetas_d [self.theta_maxidx] == 180:
            self.phi_maxidx = self.gains [-1].argmax ()
        self.theta_max = self.thetas_d [self.theta_maxidx]
        self.phi_max   = self.phis_d   [self.phi_maxidx]
        self.desc      = ['Title: %s' % self.parent.title]
        self.desc.append ('Frequency: %.2f MHz' % self.f)
        self.lbl_deg   = 0
        self.labels    = None
    # end def compute

    def azimuth_gains (self, scaler):
        g = self.gains [self.parent.theta_angle_idx]
        gains = scaler.scale (self.parent.maxg, g)
        return gains, g
    # end def azimuth_gains

    def azimuth_text (self, scaler):
        desc = self.desc.copy ()
        desc.insert (0, 'Azimuth Pattern')
        desc.append ('Outer ring: %.2f dBi' % self.parent.maxg)
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
        eps = 1e-9
        phis = self.phis
        assert abs (phis [idx] - phis [self.parent.phi_angle_idx]) - np.pi < eps
        gains2 = self.gains.T [idx].T
        g = np.append (gains1, np.flip (gains2))
        gains = scaler.scale (self.parent.maxg, g)
        return gains, g
    # end def elevation_gains

    def elevation_text (self, scaler):
        desc = self.desc.copy ()
        desc.insert (0, 'Elevation Pattern')
        desc.append ('Outer ring: %.2f dBi' % self.parent.maxg)
        desc.append ('Scaling: %s' % scaler.title)
        desc.append \
            ( 'Azimuth: %.2f° (X=0°)'
            % self.phis_d [self.parent.phi_angle_idx]
            )
        return desc
    # end def elevation_text

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

class Gain_Plot:
    fig_x = 512
    fig_y = 384
    plot_names   = ('azimuth', 'elevation', 'plot_vswr', 'plot3d', 'plot_geo')
    update_names = set (('azimuth', 'elevation', 'plot3d'))
    font_sans    = \
        "Helvetica, Nimbus Sans, Liberation Sans, Open Sans, arial, sans-serif"
    # Default colors for swr plot
    c_real = '#AE4141'
    c_imag = '#FFB329'

    def __init__ (self, args):
        self.args        = args
        self.dpi         = args.dpi
        self.filename    = args.filename
        self.outfile     = args.output_file
        self.f           = None
        self.with_slider = args.with_slider
        self.wireframe   = args.wireframe
        self.scalers     = dict \
            ( linear_db      = Linear_dB_Scaler (args.scaling_mindb)
            , linear_voltage = scale_linear_voltage
            , linear         = scale_linear
            , arrl           = scale_arrl
            )
        self.scaler = self.scalers [args.scaling_method]
        self.cur_scaler = self.scaler

        # Discrete values for slider are available only in later
        # matplotlib versions
        if matplotlib_version_float < 3.5:
            self.with_slider = False
        # Default title from filename
        self.title       = os.path.splitext \
            (os.path.basename (args.filename)) [0]
        # This might override title
        self.gdata = {}
        self.geo = []
        # This populates gdata:
        self.read_file ()
        self.frequencies = []
        self.maxg = None
        theta_idx = {}
        phi_idx   = {}
        for f in sorted (self.gdata):
            gdata = self.gdata [f]
            gdata.compute ()
            if gdata.theta_maxidx not in theta_idx:
                theta_idx [gdata.theta_maxidx] = 0
            theta_idx [gdata.theta_maxidx] += 1
            if gdata.phi_maxidx not in phi_idx:
                phi_idx [gdata.phi_maxidx] = 0
            phi_idx [gdata.phi_maxidx] += 1
            if self.maxg is None or self.maxg < gdata.maxg:
                self.maxg = gdata.maxg
            self.frequencies.append (f)
        # Compute the theta index that occurs most often over all
        # frequencies
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
        if self.outfile or len (self.gdata) == 1 or not self.with_slider:
            self.with_slider = False
        # Borrow colormap from matplotlib to use in plotly
        self.colormap = []
        for cn in mcolors.TABLEAU_COLORS:
            self.colormap.append (mcolors.TABLEAU_COLORS [cn])
        self.c_vswr = self.colormap [0]
    # end def __init__

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
                )
            )
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
                    , ticksuffix  = ' MHz'
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
                    , hoverformat = '.2f'
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
		    , position    = 0.96
		    , anchor      = "free"
                    , hoverformat = '.1f'
                    , zeroline    = False
                    )
                , paper_bgcolor = 'white'
                , plot_bgcolor  = 'white'
                , hovermode     = 'x unified'
                )
            )
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
                        )
                    , yaxis = dict
                        ( linecolor      = "#B0B0B0"
                        , gridcolor      = "#B0B0B0"
                        , showbackground = False
                        )
                    , zaxis = dict
                        ( linecolor      = "#B0B0B0"
                        , gridcolor      = "#B0B0B0"
                        , showbackground = False
                        )
                    )
                )
            )
        return d
    # end def plotly_3d_default

    def all_gains (self):
        xyz = None
        for f in self.frequencies:
            g = self.gdata [f]
            _, _, X, Y, Z = g.plot3d_gains (self.scaler)
            if xyz is None:
                xyz = np.array ([X, Y, Z]).T
            else:
                xyz = np.concatenate ((xyz, np.array ([X, Y, Z]).T))
        return xyz.T
    # end def all_gains

    def read_file (self):
        guard     = 'not set'
        delimiter = guard
        gdata     = None
        status    = 'start'
        wires     = []
        with open (self.filename, 'r') as f:
            for line in f:
                line = line.strip ()
                if  (   line.startswith ('X             Y             Z')
                    and line.endswith ('END1 END2  NO.')
                    ):
                    status = 'geo'
                    self.geo.append ([])
                    continue
                if  (   line.startswith ('X             Y             Z')
                    and line.endswith ('SEGMENTS')
                    ):
                    status = 'wire'
                    wires.append ([])
                    continue
                if  (   line.startswith ('No:       X         Y         Z')
                    and line.endswith ('I-     I    I+   No:')
                    ):
                    status = 'necgeo'
                    necidx = {}
                    continue
                if status != 'start' and not line:
                    status  = 'start'
                    continue
                if status == 'geo':
                    x, y, z, r, e1, e2, n = line.split ()
                    self.geo [-1].append ([float (a) for a in (x, y, z)])
                    continue
                if status == 'wire':
                    l = line.split ()
                    wires [-1].append ([float (a) for a in l [:3]])
                    continue
                if status == 'necgeo':
                    # Fixme: This should really be lambda-dependent
                    eps = 1e-3
                    started = False
                    ll = line.split ()
                    idx = int (ll [0])
                    x, y, z, l, alpha, beta = (float (a) for a in ll [1:7])
                    mid = np.array ([x, y, z])
                    prev, cur, next = (int (a) for a in ll [8:11])
                    if prev == 0 or abs (prev) > idx:
                        self.geo.append ([])
                        started = True
                    elif abs (prev) != idx - 1:
                        self.geo.append ([])
                        a, b = necidx [abs (prev)]
                        if prev > 0:
                            b += 1
                        self.geo [-1].append (self.geo [a][b])
                        started = True
                    necidx [idx] = (len (self.geo) - 1, len (self.geo [-1]) - 1)
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
                        self.geo [-1].append (st)
                        self.geo [-1].append (en)
                    else:
                        assert np.linalg.norm (self.geo [-1][-1] - st) < eps
                        self.geo [-1].append (en)
                if line.startswith ('FREQUENCY'):
                    f = float (line.split (':') [1].split () [0])
                    if f in self.gdata:
                        print \
                            ( "Warning: Frequency %2.2f already present, "
                              "using last occurrence"
                            , file = sys.stderr
                            )
                    gdata = self.gdata [f] = Gain_Data (self, f)
                    delimiter = guard
                    continue
                if line.startswith ('IMPEDANCE ='):
                    m = line.split ('(', 1)[1].split (')')[0].rstrip ('J')
                    a, b = (float (x) for x in m.split (','))
                    gdata.impedance = a + 1j * b
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
                    gdata.impedance = a + 1j * b
                    status = 'start'
                    continue
                # File might end with Ctrl-Z (DOS EOF)
                if line.startswith ('\x1a'):
                    break
                if status == 'antenna-input':
                    continue
                if delimiter == guard:
                    # Original Basic implementation gain output
                    if line.endswith (',D'):
                        delimiter = ','
                        f = 0.0
                        gdata = self.gdata [f] = Gain_Data (self, f)
                        continue
                    if line.startswith ('ANGLE') and line.endswith ('(DB)'):
                        delimiter = None
                        continue
                    # NEC file
                    if  (   line.startswith ('DEGREES   DEGREES        DB')
                        and line.endswith ('VOLTS/M   DEGREES')
                        ):
                        delimiter = None
                        continue
                else:
                    if not line:
                        delimiter = guard
                        gdata = None
                        continue
                    fields = line.split (delimiter)
                    if len (fields) < 5 or not fields [0][0].isnumeric ():
                        delimiter = guard
                        gdata = None
                        continue
                    zen, azi, vp, hp, tot = (float (x) for x in fields [:5])
                    gdata.pattern [(zen, azi)] = tot
        for w, g in zip (wires, self.geo):
            if w [0] != g [0]:
                g.insert (0, w [0])
            if w [-1] != g [-1]:
                g.append (w [-1])
    # end def read_file

    def plot (self, f = None):
        if f is None:
            f = next (iter (self.gdata))
        self.frequency = f
        self.cur_freq  = f
        self.impedance = self.args.system_impedance
        if  (  getattr (self.args, 'export_html', None)
            or getattr (self.args, 'show_in_browser', None)
            ):
            self.plot_plotly (f)
        else:
            self.plot_matplotlib (f)
    # end def plot

    def plot_plotly (self, f):
        m = {}
        self.data = self.gdata [f]
        for name in self.plot_names:
            if getattr (self.args, name):
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
                        self.plotly_lastfig  = False
                        self.plotly_firstfig = True
                        if name == 'plot3d':
                            if len (self.frequencies) > 1:
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
                        else:
                            self.plotly_fig = go.Figure \
                                (** self.plotly_polar_default)
                        for n, f in enumerate (self.frequencies):
                            self.plotly_count = n
                            self.frequency = f
                            self.cur_freq  = f
                            self.data = self.gdata [f]
                            if f == self.frequencies [-1]:
                                self.plotly_lastfig = True
                            method (name)
                            self.plotly_firstfig = False
                    else:
                        method (name)
    # end def plot_plotly

    def plot_matplotlib (self, f):
        dpi  = self.dpi
        x, y = np.array ([self.fig_x, self.fig_y]) / 80 * dpi

        d = {}
        a = {}
        count = 0
        for name in self.plot_names:
            if getattr (self.args, name):
                p = dict (projection = 'polar')
                if name == 'plot_vswr':
                    p = {}
                elif name == 'plot3d' or name == 'plot_geo':
                    p = dict (projection = '3d')
                d [name] = p
                a [name] = dict (arg = count + 1)
                count += 1
        if len (d) > 2:
            args       = [2, 2]
            figsize    = [x * 2 / dpi, y * 2 / dpi]
        elif len (d) == 2:
            args       = [1, 2]
            figsize    = [x * 2 / dpi, y / dpi]
        else:
            args       = [1, 1]
            figsize    = [x / dpi, y / dpi]
        if self.with_slider:
            fig_inc = .8
            slider_perc = fig_inc / (fig_inc + figsize [1])
            figsize [1] += fig_inc
        self.fig = fig = plt.figure (dpi = dpi, figsize = figsize)
        fig.canvas.manager.set_window_title (self.title)
        if self.with_slider:
            sc = 1 + slider_perc
            hs = fig.subplotpars.hspace / sc
            bt = fig.subplotpars.bottom / sc
            sp = slider_perc            / sc
            tp = 1 - ((1 - fig.subplotpars.top) / sc)
            plt.subplots_adjust \
                (hspace = hs, top = tp, bottom = sp + bt)
        self.axes = {}
        self.data = self.gdata [f]
        self.gui_objects = {}
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
        self.freq_slider = None
        # Make a horizontal slider to control the frequency.
        if not self.outfile:
            if self.with_slider:
                axfreq = fig.add_axes ([0.15, 0.01, 0.65, 0.03])
                #axfreq = fig.add_axes ([0.15, 0.01, 0.65, sh])
                minf   = min (self.gdata)
                freq_slider = Slider \
                    ( ax      = axfreq
                    , label   = 'Frequency'
                    , valinit = minf
                    , valmin  = minf
                    , valmax  = max (self.gdata)
                    , valstep = np.array (list (self.gdata))
                    , valfmt  = '%.2f MHz'
                    )
                self.freq_slider = freq_slider
                freq_slider.on_changed (self.update_from_slider)
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
            fig.savefig (self.outfile)
        else:
            plt.show ()
    # end def plot_matplotlib

    def azimuth (self, name):
        self.desc = self.data.azimuth_text (self.scaler)
        self.lbl_deg = self.data.phis_d [self.phi_angle_idx]
        self.labels  = 'XY'
        self.polargains, self.unscaled = self.data.azimuth_gains (self.scaler)
        self.angles = self.data.phis
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
        self.polargains, self.unscaled = self.data.elevation_gains (self.scaler)
        thetas = self.data.thetas
        p2 = np.pi / 2
        self.angles = np.append (p2 - thetas, np.flip (p2 + thetas))
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
        fig = self.plotly_fig
        nm  = self.angle_name
        tpl = 'Gain: %%{text}<br>%s: %%{theta}<extra></extra>' % nm
        df = dict \
            ( r       = self.polargains
            , theta   = (self.angles / np.pi * 180) % 360
            , name    = "f=%.3f MHz" % self.frequency
            , mode    = 'lines'
            , visible = True if self.plotly_firstfig else 'legendonly'
            , text    = ['%.2f dBi (%.2f dB)' % (u, u - self.maxg)
                         for u in self.unscaled
                        ]
            , hovertemplate = tpl
            )
        fig.add_trace (go.Scatterpolar (**df))
        if self.plotly_lastfig:
            desc = '<br>'.join (self.desc [0:2] + self.desc [3:])
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
        obj, = ax.plot (self.angles, self.polargains, **args)
        self.gui_objects [name]['data'] = obj
        #ax.grid (True)
        self.scaler.set_ticks (ax)
        # Might add color and size labelcolor='r' labelsize = 8
        ax.tick_params (axis = 'y', rotation = 'auto')
        an = self.angle_name
        def format_polar_coord (x, y):
            sc = self.scaler.invscale (y)
            return '%s=%.2f°, Gain=%.2f dBi (%.2f dB)' \
                % (an, x / np.pi * 180, sc + self.maxg, sc)
        ax.format_coord = format_polar_coord
    # end def polarplot_matplotlib

    def plot3d_matplotlib (self, name):
        if name in self.gui_objects and self.gui_objects [name]:
            self.gui_objects [name]['data'].remove ()
            self.gui_objects [name] = {}
        ax = self.axes [name]
        _, gains, X, Y, Z = self.data.plot3d_gains (self.scaler)
        xr, yr, zr = self.scene_ranges ((X, Y, Z))
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
        fig = self.plotly_fig
        if self.args.decibel_style == 'both':
            ticktext = ['%.2f dBi (%.2f dB)' % (u + self.maxg, u)
                        for u in self.scaler.ticks
                       ]
        elif self.args.decibel_style == 'absolute':
            ticktext = ['%.2f dBi' % (u + self.maxg) for u in self.scaler.ticks]
        else:
            ticktext = ['%.2f dB' % u for u in self.scaler.ticks]
        # Ensure that the uppermost (0dB) mark is printed
        # This may be slightly off when a pattern is very different for
        # different frequencies
        tickvals = self.scaler.tick_values
        tickvals [0] = gains.max ()
        lgroup  = 'l%d' % self.plotly_count
        visible = True if self.plotly_firstfig else 'legendonly'
        tpl = ('Gain: %{customdata[0]:.2f} dBi (%{customdata[1]:.2f} dB)<br>'
               'Azimuth: %{customdata[2]:.2f}° (X: 0°)<br>'
               'Elevation: %{customdata[3]:.2f}°<extra></extra>'
              )

        colorbar_xpos = 1.02
        if self.legend_width:
            colorbar_xpos = 0.98 - self.legend_width
        fig.add_trace \
            ( go.Surface
                ( x = X, y = Y, z = Z
                , surfacecolor = gains
                , colorscale   = 'rainbow'
                , visible      = visible
                , legendgroup  = lgroup
                , name         = "f=%.3f MHz" % self.frequency
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
        if len (self.frequencies) > 1:
            fig.add_trace \
                ( go.Scatter
                    ( dict (x = [1.], y = [1.], line = dict (color = 'white'))
                    , legendgroup = lgroup
                    , visible     = visible
                    , showlegend  = True
                    , name        = "f=%.3f MHz" % self.frequency
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
                    , aspectratio = dict (x=1, y=1, z=1)
                    )
                )
            self.show_plotly (fig, name, script = self.plotly_3d_script)
    # end def plot3d_plotly

    def prepare_vswr (self):
        z0   = self.impedance
        X    = []
        Y    = []
        imag = []
        real = []
        xabs = []
        xphi = []
        for f in self.gdata:
            gd  = self.gdata [f]
            z   = gd.impedance
            rho = np.abs ((z - z0) / (z + z0))
            imag.append (z.imag)
            real.append (z.real)
            xabs.append (np.abs   (z))
            xphi.append (np.angle (z) * 180 / np.pi)
            X.append (f)
            Y.append ((1 + rho) / (1 - rho))
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
        return [np.array (v) for v in (X, Y, real, imag, xabs, xphi)]
    # end def prepare_vswr

    def range_y (self, y, min_y = None, as_plotly = False):
        """ Sensible Y range so that all different Y coordinates can
            share a grid.
        """
        mx = max (y)
        mn = min_y
        if min_y is None:
            mn = min (y)
        exp = int (np.log (max (abs (mx), abs (mn))) / np.log (10))
        mx /= 10 ** exp
        mn /= 10 ** exp
        assert mx < 10 and abs (mn) < 10
        # round mn to lower int
        mn = np.floor (mn)
        # round mx to higher int
        mx = np.ceil (mx)
        for k in 1, 2, 4, 8, 10:
            if mx - mn <= k:
                rng = np.array ([mn, mn + k]) * 10 ** exp
                tck = (k / 4) * 10 ** exp
                if as_plotly:
                    return dict (range = rng, dtick = tck)
                return rng [0], rng [1], tck
        rng = np.array ([mn, mn + 12]) * 10 ** exp
        tck = 3 * 10 ** exp
        if as_plotly:
            return dict (range = rng, dtick = tck)
        return rng [0], rng [1], tck
    # end def range_y

    def plot_vswr_matplotlib (self, name):
        ax = self.axes [name]
        ax.set_xlabel ('Frequency (MHz)')
        ax.set_ylabel ('VSWR', color = self.c_vswr)
        X, Y, real, imag, xabs, xphi = self.prepare_vswr ()
        strf  = ticker.FormatStrFormatter
        min_y = min (Y)
        max_y = max (Y)
        ax.plot (X, Y)
        ax.grid (color = blend (self.c_vswr), axis = 'y')
        ax.grid (color = '#B0B0B0', axis = 'x')
        ax.tick_params (axis = 'y', colors = self.c_vswr)
        r1, r2, t = self.range_y (Y, 1)
        yt = np.arange (r1, r2 + t, t)
        ax.set (ylim = (r1, r2), yticks = yt)
        fmt = '%.1f'
        if t == int (t):
            fmt = '%.0f'
        ax.yaxis.set_major_formatter (strf (fmt))
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
            ax3.spines.right.set_position (("axes", 1.2))
            if self.args.swr_plot_impedance_angle:
                ax2.set_ylabel ("|Z|", color = self.c_real)
                ax2.plot (X, xabs, color = self.c_real)
                r1, r2, t = self.range_y (xabs)
                yt = np.arange (r1, r2 + t, t)
                ax2.set (ylim = (r1, r2), yticks = yt)
                fmt = '%.1f '
                if t == int (t):
                    fmt = '%.0f '
                ax2.yaxis.set_major_formatter (strf (fmt + ohm))
                ax3.set_ylabel ("phi (Z)", color = self.c_imag)
                ax3.plot (X, xphi, color = self.c_imag)
                yt = np.arange (-180, 180 + 30, 30)
                ax3.set (ylim = (-180, 180), yticks = yt)
                ax3.yaxis.set_major_formatter (strf ('%.0f°'))
            else:
                ax2.set_ylabel ("real", color = self.c_real)
                ax2.plot (X, real, color = self.c_real)
                r1, r2, t = self.range_y (real)
                yt = np.arange (r1, r2 + t, t)
                ax2.set (ylim = (r1, r2), yticks = yt)
                fmt = '%.1f '
                if t == int (t):
                    fmt = '%.0f '
                ax2.yaxis.set_major_formatter (strf (fmt + ohm))
                ax3.set_ylabel ("imag", color = self.c_imag)
                ax3.plot (X, imag, color = self.c_imag)
                r1, r2, t = self.range_y (imag)
                yt = np.arange (r1, r2 + t, t)
                ax3.set (ylim = (r1, r2), yticks = yt)
                fmt = '%.1f '
                if t == int (t):
                    fmt = '%.0f '
                ax3.yaxis.set_major_formatter (strf (fmt + ohm))
        if self.args.swr_show_bands:
            y1, y2 = np.array (list (ax.get_ylim ()))
            for b in self.band:
                l, h = self.band [b]
                ax.fill_between ([l, h], y1, y2, color = '#CCFFCC')
    # end def plot_vswr_matplotlib

    def add_plotly_df (self, yname, color = None, axisname = None):
        """ Add yname in dataframe self.df to self.fig
        """
        d  = dict (x = self.df ["Frequency"], y = self.df [yname], name = yname)
        if color:
            d.update (line = dict (color = color))
        if axisname:
            d.update (yaxis = axisname)
        self.fig.add_trace (go.Scatter (**d))
    # end def add_plotly_df

    def plot_vswr_plotly (self, name):
        X, Y, real, imag, xabs, xphi = self.prepare_vswr ()
        df = pd.DataFrame ()
        df ['Frequency'] = X
        df ['VSWR']      = Y
        df ['real']      = real
        df ['imag']      = imag
        df ['|Z|']       = xabs
        df ['phi (Z)']   = xphi
        self.df = df
        self.fig = fig = go.Figure()
        layout = self.plotly_line_default
        self.add_plotly_df ("VSWR", self.c_vswr)
        y = layout ['layout']['yaxis']
        y.update (**self.range_y (Y, 1, as_plotly = True))
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
                y2.update (** self.range_y (xabs, as_plotly = True))
                y3 ['title'].update (text = "phi (Z)")
                y3.update (range = [-180, 180], dtick = 30)
                y3 ['ticksuffix'] = '°'
            else:
                self.add_plotly_df ("real", self.c_real, "y2")
                y2 ['title'].update (text = "real")
                y2.update (** self.range_y (real, as_plotly = True))
                self.add_plotly_df ("imag", self.c_imag, "y3")
                y3 ['title'].update (text = "imag")
                y3.update (** self.range_y (imag, as_plotly = True))
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
                    , text      = '<b>%s</b>' % escape (b)
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

    def scene_ranges (self, matrix = None):
        """ Create cubic bounding box to force equal aspect ratio
            If matrix is not given, we concatenate *all* gains.
        """
        if matrix is None:
            matrix = self.all_gains ()
        x, y, z = matrix
        max_range = np.array \
            ( [ x.max () - x.min ()
              , y.max () - y.min ()
              , z.max () - z.min ()
              ]
            ).max() / 2.0
        mid_x = (x.max () + x.min ()) / 2
        mid_y = (y.max () + y.min ()) / 2
        mid_z = (z.max () + z.min ()) / 2
        xr = np.array ([mid_x - max_range, mid_x + max_range])
        yr = np.array ([mid_y - max_range, mid_y + max_range])
        zr = np.array ([mid_z - max_range, mid_z + max_range])
        return np.array ([xr, yr, zr])
    # end def scene_ranges

    def plot_geo_plotly (self, name):
        xr, yr, zr = self.scene_ranges (np.concatenate (self.geo).T)
        fig = px.line_3d ()
        fig.update (self.plotly_3d_default)
        # We may want to draw everything in the same color and
        # remove the individual scatter3d from the legend
        # but then, maybe not
        for n, g in enumerate (self.geo):
            g = np.array (g)
            d = dict (mode = 'lines', connectgaps = False)
            d ['x'], d ['y'], d ['z'] = g.T
            fig.add_scatter3d (**d)
        fig.layout.scene.update \
            ( dict
                ( xaxis = dict (range = xr)
                , yaxis = dict (range = yr)
                , zaxis = dict (range = zr)
                #, domain = dict (x = [0.0, 0.5], y = [0.0, 0.5]) ??
                , camera = dict
                    ( up     = dict (x = 0,    y = 0,    z = 1)
                    , center = dict (x = 0,    y = 0,    z = 0)
                    , eye    = dict (x = 0.01, y = 0.01, z = 1)
                    )
                )
            )
        self.show_plotly (fig, name)
    # end def plot_geo_plotly

    def plot_geo_matplotlib (self, name):
        ax = self.axes [name]
        # equal aspect ratio
        xr, yr, zr = self.scene_ranges (np.concatenate (self.geo).T)
        ax.set_xlim (*xr)
        ax.set_ylim (*yr)
        ax.set_zlim (*zr)
        for g in self.geo:
            g = np.array (g)
            x, y, z = g.T
            ax.plot (x, y, z)
    # end def plot_geo_matplotlib

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
        if self.args.export_html:
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
            gdata = self.gdata [self.frequency]
            if name == 'plot3d':
                self.data = gdata
                self.plot3d_matplotlib ('plot3d')
            else:
                gains, g = getattr (gdata, name + '_gains')(self.scaler)
                data_obj.set_ydata (gains)
                text_obj = gui ['text']
                text = getattr (gdata, name + '_text')(self.scaler)
                text_obj.set_text ('\n'.join (text))
                if self.cur_scaler != self.scaler:
                    self.scaler.set_ticks (self.axes [name])
        self.fig.canvas.draw ()
        self.cur_freq   = self.frequency
        self.cur_scaler = self.scaler
    # end def update_display

    def keypress (self, event):
        idx = self.frequencies.index (self.frequency)
        if event.key == "+":
            if idx < len (self.frequencies) - 1:
                self.frequency = self.frequencies [idx + 1]
        elif event.key == "-":
            if idx > 0:
                self.frequency = self.frequencies [idx - 1]
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
        if self.cur_freq != self.frequency:
            # Do not call update_display when slider has changed, this
            # is done by slider
            if self.freq_slider:
                self.freq_slider.set_val (self.frequency)
            else:
                self.update_display ()
    # end def keypress

    def update_from_slider (self, val):
        self.frequency = self.freq_slider.val
        self.update_display ()
    # end def update_from_slider

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

def main (argv = sys.argv [1:]):
    cmd = SortingArgumentParser ()
    scaling = ['arrl', 'linear', 'linear_db', 'linear_voltage']
    cmd.add_argument \
        ( 'filename'
        , help    = 'File to parse and plot'
        )
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
    deci_styles = ('absolute', 'relative', 'both')
    cmd.add_argument \
        ( '--decibel-style'
        , help    = 'Decibel style for plotly 3D color bar,'
                    ' one of %s, the default prints the relative value'
                    ' in parentheses' % ', '.join (deci_styles)
        , default = 'both'
        )
    cmd.add_argument \
        ( '--dpi'
        , help    = 'Resolution for matplotlib, default = %(default)s'
        , type    = int
        , default = 80
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
    # For versions below 3.5 slider will be always off
    if matplotlib_version_float >= 3.5:
        cmd.add_argument \
            ( '--with-frequency-slider', '--with-slider'
            , dest    = 'with_slider'
            , help    = 'Turn on frequency slider, frequency can be stepped'
                        ' with +/- keys and slider is very slow.'
            , action  = 'store_true'
            )
    cmd.add_argument \
        ( '--margin-3d'
        , help    = 'Margin around 3D plot in pixel for plotly backend'
        , type    = int
        , default = 20
        )
    cmd.add_argument \
        ( '--band'
        , help    = 'Band to highlight in VSWR plot, default are ham'
                    ' bands in Austria, Format: name:flow,fhi'
        , default = []
        , action  = 'append'
        )
    cmd.add_argument \
        ( '--plot-geo', '--geo'
        , help    = 'Plot Geometry'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--output-file'
        , help    = 'Output file, default is interactive'
        )
    cmd.add_argument \
        ( '--plot3d', '--3d', '--plot-3d', '--3D'
        , help    = 'Do a 3D plot'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--scaling-method'
        , help    = 'Scaling method to use, default=%%(default)s, one of %s'
                  % (', '.join (scaling))
        , default = 'arrl'
        )
    cmd.add_argument \
        ( '--scaling-mindb'
        , help    = 'Minimum decibels linear dB scaling, default=%(default)s'
        , type    = float
        , default = -50
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
    args = cmd.parse_args (argv)
    hb = dict (ham_bands)
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
    if args.decibel_style not in deci_styles:
        cmd.print_usage ()
        exit ('Invalid decibel-style: "%s"' % args.decibel_style)
    if not hasattr (args, 'with_slider'):
        args.with_slider = False
    gp   = Gain_Plot (args)

    # Default is all
    if  (   not args.azimuth and not args.elevation
        and not args.plot3d  and not args.plot_vswr and not args.plot_geo
        ):
        args.plot3d = args.elevation = args.azimuth = args.plot_vswr = True
    gp.plot ()
# end def main

if __name__ == '__main__':
    main ()
