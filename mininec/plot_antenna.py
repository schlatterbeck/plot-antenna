#!/usr/bin/python3

import sys
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from argparse import ArgumentParser
from matplotlib import cm, __version__ as matplotlib_version, rcParams
from matplotlib.widgets import Slider
try:
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas         as pd
except ImportError:
    px = None

matplotlib_version_float = float ('.'.join (matplotlib_version.split ('.')[:2]))

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

# end class Linear_Scaler

scale_linear = Linear_Scaler ()

class Linear_Voltage_Scaler (Scaler):
    ticks = np.array ([0, -3, -6, -10, -20])
    title = 'Linear voltage'

    def scale (self, max_gain, gains):
        return 10 ** ((gains - max_gain) / 20)
    # end def scale

# end class Linear_Voltage_Scaler

scale_linear_voltage = Linear_Voltage_Scaler ()

class ARRL_Scaler (Scaler):
    ticks = np.array ([0, -3, -6, -10, -20, -30])
    title = 'ARRL'

    def scale (self, max_gain, gains):
        return (1 / 0.89) ** ((gains - max_gain) / 2)
    # end def scale

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
        self.theta_max = self.thetas_d [self.theta_maxidx]
        self.phi_max   = self.phis_d   [self.phi_maxidx]
        self.desc      = ['Title: %s' % self.parent.title]
        self.desc.append ('Frequency: %.2f MHz' % self.f)
        self.desc.append ('Outer ring: %.2f dBi' % self.maxg)
        self.lbl_deg   = 0
        self.labels    = None
    # end def compute

    def azimuth_gains (self, scaler):
        g = self.gains [self.parent.theta_maxidx]
        gains = scaler.scale (self.parent.maxg, g)
        return gains, g
    # end def azimuth_gains

    def azimuth_text (self, scaler):
        desc = self.desc.copy ()
        desc.insert (0, 'Azimuth Pattern')
        desc.append ('Scaling: %s' % scaler.title)
        desc.append \
            ( 'Elevation: %.2f°'
            % (90 - self.thetas_d [self.parent.theta_maxidx])
            )
        return desc
    # end def azimuth_text

    def elevation_gains (self, scaler):
        gains1 = self.gains.T [self.parent.phi_maxidx].T
        # Find index of the other side of the azimuth
        pmx = self.phis.shape [0] - self.phis.shape [0] % 2
        idx = (self.parent.phi_maxidx + pmx // 2) % pmx
        assert idx != self.parent.phi_maxidx
        eps = 1e-9
        phis = self.phis
        assert abs (phis [idx] - phis [self.parent.phi_maxidx]) - np.pi < eps
        gains2 = self.gains.T [idx].T
        g = np.append (gains1, np.flip (gains2))
        gains = scaler.scale (self.parent.maxg, g)
        return gains, g
    # end def elevation_gains

    def elevation_text (self, scaler):
        desc = self.desc.copy ()
        desc.insert (0, 'Elevation Pattern')
        desc.append ('Scaling: %s' % scaler.title)
        desc.append \
            ( 'Azimuth: %.2f°'
            % ((self.phis_d [self.parent.phi_maxidx] - 90) % 360)
            )
        return desc
    # end def elevation_text

    def plot3d_gains (self, scaler):
        gains  = scaler.scale (self.parent.maxg, self.gains)
        P, T   = np.meshgrid (self.phis, self.thetas)
        X = np.cos (P) * np.sin (T) * gains
        Y = np.sin (P) * np.sin (T) * gains
        Z = np.cos (T) * gains
        return [gains, X, Y, Z]
    # end def plot3d_gains

# end class Gain_Data

class Gain_Plot:
    fig_x = 512
    fig_y = 384
    plot_names   = ('azimuth', 'elevation', 'plot_vswr', 'plot3d', 'plot_geo')
    update_names = set (('azimuth', 'elevation', 'plot3d'))


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
        if self.outfile or len (self.gdata) == 1 or not self.with_slider:
            self.with_slider = False
        # Borrow colormap from matplotlib to use in plotly
        self.colormap = []
        for cn in mcolors.TABLEAU_COLORS:
            self.colormap.append (mcolors.TABLEAU_COLORS [cn])
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
                        ( family = "Helvetica"
                        , color  = "#010101"
                        )
                    )
                )
            )
        return d
    # end def plotly_polar_default

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
        if self.args.export_html or self.args.show_in_browser:
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
                    method = getattr (self, name + '_plotly')
                if method is None:
                    print \
                        ( 'Warning: No method for "%(name)s for plotly'
                        % locals ()
                        )
                else:
                    if name in ('azimuth', 'elevation'):
                        self.plotly_lastfig  = False
                        self.plotly_firstfig = True
                        self.plotly_polarfig = go.Figure \
                            (** self.plotly_polar_default)
                        for f in self.frequencies:
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
        pm = self.data.phis_d [self.phi_maxidx]
        self.lbl_deg = (pm - 90) % 360
        self.labels  = 'XY'
        self.polargains, self.unscaled = self.data.azimuth_gains (self.scaler)
        self.angles = (self.data.phis - np.pi / 2)
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
        self.lbl_deg  = 90 - self.data.thetas_d [self.theta_maxidx]
        self.labels   = None
        self.polargains, self.unscaled = self.data.elevation_gains (self.scaler)
        thetas = self.data.thetas
        p2 = np.pi / 2
        self.angles = np.append (p2 - thetas, np.flip (p2 + thetas))
        self.polarplot (name)
    # end def elevation

    def format_polar_coord (self, x, y):
        return '\u03B8=%.2f°, r=%.3f' % (x / np.pi * 180, y)
    # end def format_polar_coord

    def polarplot (self, name):
        if self.args.export_html or self.args.show_in_browser:
            self.polarplot_plotly (name)
        else:
            self.polarplot_matplotlib (name)
    # end def polarplot

    def polarplot_plotly (self, name):
        fig = self.plotly_polarfig
        df = dict \
            ( r       = self.polargains
            , theta   = self.angles / np.pi * 180
            , name    = "f=%.3f MHz" % self.frequency
            , mode    = 'lines'
            , visible = True if self.plotly_firstfig else 'legendonly'
            , text    = ['%.2f dBi (%.2f dB)' % (u, u - self.maxg)
                         for u in self.unscaled
                        ]
            , hovertemplate = 'gain: %{text}<br>\u03b8: %{theta}'
            )
        fig.add_trace (go.Scatterpolar (**df))
        if self.plotly_lastfig:
            desc = '<br>'.join (self.desc [0:2] + self.desc [3:])
            # don't use fig.update_layout (title = desc) which will
            # delete title attributes
            fig.layout.title.text = desc
            lbl_deg = self.lbl_deg or 0
            tickangle = 90
            if lbl_deg > 180:
                tickangle = -90
            fig.layout.polar.radialaxis.tickangle = tickangle
            fig.layout.polar.radialaxis.angle = lbl_deg
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
            self.show_plotly (fig, name)
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
        ax.format_coord = self.format_polar_coord
    # end def polarplot_matplotlib

    def plot3d_matplotlib (self, name):
        if name in self.gui_objects and self.gui_objects [name]:
            self.gui_objects [name]['data'].remove ()
            self.gui_objects [name] = {}
        ax = self.axes [name]
        gains, X, Y, Z = self.data.plot3d_gains (self.scaler)
        # Create cubic bounding box to simulate equal aspect ratio
        max_range = np.array \
            ( [ X.max () - X.min ()
              , Y.max () - Y.min ()
              , Z.max () - Z.min ()
              ]
            ).max() / 2.0
        mid_x = (X.max () + X.min ()) * 0.5
        mid_y = (Y.max () + Y.min ()) * 0.5
        mid_z = (Z.max () + Z.min ()) * 0.5
        ax.set_xlim (mid_x - max_range, mid_x + max_range)
        ax.set_ylim (mid_y - max_range, mid_y + max_range)
        ax.set_zlim (mid_z - max_range, mid_z + max_range)

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
    # end def plot3d_gains

    def prepare_vswr (self):
        z0 = self.impedance
        X  = []
        Y  = []
        for f in self.gdata:
            gd  = self.gdata [f]
            z   = gd.impedance
            rho = np.abs ((z - z0) / (z + z0))
            X.append (f)
            Y.append ((1 + rho) / (1 - rho))
        return X, Y
    # end def prepare_vswr

    def plot_vswr_matplotlib (self, name):
        ax = self.axes [name]
        ax.set_xlabel ('Frequency')
        ax.set_ylabel ('VSWR')
        X, Y = self.prepare_vswr ()
        ax.plot (X, Y)
    # end def plot_vswr_matplotlib

    def plot_vswr_plotly (self, name):
        X, Y = self.prepare_vswr ()
        df = pd.DataFrame ()
        df ['Frequency'] = X
        df ['VSWR'] = Y
        fig = px.line (df, x="Frequency", y="VSWR")
        self.show_plotly (fig, name)
    # end def plot_vswr_plotly

    def plot_geo_prepare_maxima (self):
        x, y, z = np.concatenate (self.geo).T
        mr = [x.max () - x.min (), y.max () - y.min (), z.max () - z.min ()]
        mr = np.array (mr) / 2
        mid_x = (x.max () + x.min ()) / 2
        mid_y = (y.max () + y.min ()) / 2
        mid_z = (z.max () + z.min ()) / 2
        max_range = max (mr)
        xl, xu = (mid_x - max_range, mid_x + max_range)
        yl, yu = (mid_y - max_range, mid_y + max_range)
        zl, zu = (mid_z - max_range, mid_z + max_range)
        return (xl, xu), (yl, yu), (zl, zu)
    # end def plot_geo_prepare_maxima

    def plot_geo_plotly (self, name):
        xr, yr, zr = self.plot_geo_prepare_maxima ()
        fig = px.line_3d ()
        # We may want to draw everything in the same color and
        # remove the individual scatter3d from the legend
        # but then, maybe not
        for n, g in enumerate (self.geo):
            g = np.array (g)
            d = dict (mode = 'lines', connectgaps = False)
            d ['x'], d ['y'], d ['z'] = g.T
            fig.add_scatter3d (**d)
        # Hmm: How to set scaleanchor? Used to couple ratio of axes
        # constrain and constraintoward  need also to be set
        # Hmm, rangemode (one of nonnegative, tozero, normal) does nothing
        # Ah: This applies only if we do not specify an explicit range
        fig.update_layout \
            ( scene = dict
                ( xaxis = dict (range = xr)
                , yaxis = dict (range = yr)
                , zaxis = dict (range = zr)
                )
            )
        self.show_plotly (fig, name)
    # end def plot_geo_plotly

    def plot_geo_matplotlib (self, name):
        ax = self.axes [name]
        # equal aspect ratio
        xr, yr, zr = self.plot_geo_prepare_maxima ()
        ax.set_xlim (*xr)
        ax.set_ylim (*yr)
        ax.set_zlim (*zr)
        for g in self.geo:
            g = np.array (g)
            x, y, z = g.T
            ax.plot (x, y, z)
    # end def plot_geo_matplotlib

    def show_plotly (self, fig, name):
        """ We can pass a config option into fig.show and fig.write_html,
            allowing scroll seems to be the default for 3d view.
            At some point we may want to set different config options
            for different plots.
        """
        config = dict (displaylogo = False)

        if self.args.export_html:
            fn = self.args.export_html + '-' + name
            fig.write_html (fn, config = config)
        else:
            fig.show (config = config)
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
                gains = getattr (gdata, name + '_gains')(self.scaler)
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

def main (argv = sys.argv [1:]):
    cmd = ArgumentParser ()
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
        ( '--plot-geo', '--geo'
        , help    = 'Plot Geometry'
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--output-file'
        , help    = 'Output file, default is interactive'
        )
    cmd.add_argument \
        ( '--plot3d'
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
        ( '--wireframe'
        , help    = 'Show 3d plot as a wireframe (not solid)'
        , action  = 'store_true'
        )
    if px is not None:
        cmd.add_argument \
            ( "-H", "--export-html"
            , help    = "Filename-prefix to export graphics as html, "
                        "type of graphics (azimuth, elevation, ..) is appended"
            )
        cmd.add_argument \
            ( "-S", "--show-in-browser"
            , help    = "Produce a plot shown interactively in a running "
                        "browser"
            , action  = 'store_true'
            )
    args = cmd.parse_args (argv)
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
