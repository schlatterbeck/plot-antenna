#!/usr/bin/python3

# Parsers for contributed data structures

import sys
import numpy as np
from csv import DictReader
from . import plot_antenna as aplot

def coordinate_transform (gd):
    """ Coordinate transformation on gain data: The measurement
        describes a great circle for each elevation, so the 'poles' are
        on the axis of the positioner. The positioner axis becomes the
        new Z axis and new elevations are the azimuth values. The new
        azimuths are computed from the elevations.
    """
    t = gd.phis_d [gd.phis_d <= 180]
    p = sorted (list (set (gd.thetas_d).union (gd.thetas_d + 180)))
    if p [-1] != 360.:
        p.append (360.)
    otl = gd.thetas_d.shape [0]
    if gd.thetas_d [otl - 1] != 180:
        otl += 1
    p   = np.array (p)
    ng  = np.zeros ((len (t), len (p)))
    opl = gd.phis_d.shape [0]
    for nth, theta in enumerate (t):
        for nph, phi in enumerate (p):
            if phi <= 180:
                oth = nph
                oph = nth
            else:
                oth = nph - (p.shape [0] // 2)
                oph = opl - nth - 1
            if oth == gd.gains.shape [0]:
                # This happens only when 180° is missing for positioner
                ng [nth, nph] = gd.gains [0, opl - oph - 1]
            else:
                ng [nth, nph] = gd.gains [oth, oph]
    gd.gains    = ng
    gd.phis_d   = p
    gd.thetas_d = t
    gd.phis     = p * np.pi / 180
    gd.thetas   = t * np.pi / 180
# end def coordinate_transform

def parse_csv_measurement_data (args):
    """ Parses measurement data from CSV file
        This has the columns:
        - Messwert: The measurement
          May also be called 'eirp' or 'eirp (dBm)'
        - Einheit Messwert: Unit of the measurement (e.g. dBm)
          This can also be called "Einheit eirp"
          Or we have a column 'eirp (dBm)' above and the column with the
          unit is missing
        - Position Drehscheibe: Azimuth angle
          also called Position Drehscheibe (deg)
        - Position Positionierer: Elevation angle
          also seen as Position Positioner
          or Position Positioner (deg)
        - Polarisation: 'PH' for horizontal, 'PV' for vertical polarization
        - Messfrequenz: frequency
        For an example see test/Messdaten.csv
        The format has the following peculiarities:
        - The elevation angles slightly vary for a single azimuth scan.
          This means we may have 10° and some values at 10.1°. Since the
          elevation angle steps are 10° we round to the nearest integer.
        - Azimuth is scanned continuously, so azimuth angles do not
          match at all for two different elevation angles. This still
          means we can plot an azimuth polarization diagram. But for
          elevation or 3d plots we need to interpolate the azimuth
          angles. For this the --interpolate-azimuth-step option was
          added. Typically we interpolate the azimuth values to e.g. a
          2° grid.
        - Some azimuth angles are greater than 360°.
    """
    # We always need to interpolate to do the coordinate transformation
    # And we fix this to 1° for ease of coordinate transform
    if args.interpolate_azimuth_step is None:
        args.interpolate_azimuth_step = 1
    gdata_dict = {}
    with open (args.filename, 'r') as f:
        dr = DictReader (f, delimiter = ';')
        for rec in dr:
            for m in ('Einheit Messwert', 'Einheit eirp'):
                try:
                    args.dB_unit = rec [m]
                    break
                except KeyError:
                    pass
            else:
                if 'eirp (dBm)' in rec:
                    args.dB_unit = 'dBm'
            # Frequency: The internal representation is in MHz, so we
            # multiply by 1e3 because the values are in GHz.
            try:
                f = float (rec ['Messfrequenz']) * 1e3
            except KeyError:
                f = float (rec ['Messfrequenz (GHz)']) * 1e3
            if f not in gdata_dict:
                p = rec ['Polarisation'][1:]
                k = (f, p)
                if k not in gdata_dict:
                    gdata_dict [k] = aplot.Gain_Data \
                        (k, transform = coordinate_transform)
                gdata = gdata_dict [k]
            for ds in ('Position Drehscheibe', 'Position Drehscheibe (deg)'):
                try:
                    azi = float (rec [ds])
                    if args.invert_turntable:
                        azi = -azi
                    azi = (azi + args.turntable_offset) % 360
                    break
                except KeyError:
                    pass
            else:
                raise ValueError ('No column "Position Drehscheibe"')
            # Need to round elevation values: these sometimes differ
            # during a scan
            p = ( 'Position Positionierer', 'Position Positioner'
                , 'Position Positioner (deg)'
                )
            for k in p:
                try:
                    ele = float (rec [k])
                    if args.invert_positioner:
                        ele = -ele
                    ele %= 360
                    break
                except KeyError:
                    pass
            else:
                raise ValueError ('No column "Position Positioner"')
            if args.round_positioner:
                rel = args.round_positioner
                ele = round (ele / rel, 0) * rel
            # Don't allow values outside angle range
            if azi < 0 or azi > 360 or ele < 0 or ele > 360:
                continue
            # We treat the value as 'dBi' although this is dBm
            # Probably needs conversion but we may get away with
            # allowing a unit to be specified for the plot, it must be a
            # dezibel value, though (not linear gain or so)
            for k in ('Messwert', 'eirp', 'eirp (dBm)'):
                try:
                    gain = float (rec [k])
                    break
                except KeyError:
                    pass
            else:
                raise ValueError ('No column "eirp" or similar')
            gdata.pattern [(ele, azi)] = gain
    return gdata_dict
# end def parse_csv_measurement_data

def main_csv_measurement_data (argv = sys.argv [1:], pic_io = None):
    """ Parse a contributed measurement format, see docstring of
        parse_csv_measurement_data.
        The pic_io argument is for testing.
    """
    cmd = aplot.options_general ()
    aplot.options_gain (cmd)
    cmd.add_argument ('filename', help = 'CSV File to parse and plot')
    cmd.add_argument \
        ( '--round-positioner'
        , help    = "Round positioner angle to this many degrees"
        , type    = int
        )
    cmd.add_argument \
        ( '--turntable-offset'
        , help    = "Offset in degrees of the turntable, default=%(default)s"
        , type    = float
        , default = 0.0
        )
    cmd.add_argument \
        ( '--invert-turntable'
        , help    = "Invert turntable angles, default False"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( '--invert-positioner'
        , help    = "Invert positioner angles, default False"
        , action  = 'store_true'
        )
    args = aplot.process_args (cmd, argv)
    # Set default polarization, we need this otherwise the sum isn't computed
    if not args.polarization:
        args.polarization ['sum'] = True
    if pic_io is not None:
        args.output_file = pic_io
        args.save_format = 'png'
    gdata = parse_csv_measurement_data (args)
    gp = aplot.Gain_Plot (args, gdata)
    gp.compute ()
    if 0:
        # Try find (old) azimuth where only the polarization changes
        # This assumes that the phi angles are the same for H and V
        keys = list (gp.gdata)
        key  = None
        for k in keys:
            if len (k) == 2 and k [1] == 'sum':
                key = k
                break
        if key is not None:
            stat = {}
            for oph, phi in enumerate (gp.gdata [key].phis_d):
                gbp = []
                for oth, theta in enumerate (gp.gdata [key].thetas_d):
                    gbp.append (gp.gdata [key].gains [oth, oph])
                gbp = np.array (gbp)
                stat [phi] = (np.average (gbp), np.std (gbp))
            for k in stat:
                print ("%3g: avg: %g std: %g cv: %g" % (k, stat [k][0],
                    stat [k][1], stat [k][1] / abs (stat [k][0])))

    gp.plot ()
# end def main_csv_measurement_data

if __name__ == '__main__':
    main_csv_measurement_data ()
