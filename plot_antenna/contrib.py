#!/usr/bin/python3

# Parsers for contributed data structures

import sys
from csv import DictReader
from . import plot_antenna as aplot

def parse_csv_measurement_data (args):
    """ Parses measurement data from CSV file
        This has the columns:
        - Messwert: The measurement
        - Einheit Messwert: Unit of the measurement (e.g. dBm)
        - Position Drehscheibe: Azimuth angle
        - Position Positionierer: Elevation angle
        - Polarisation: 'PH' for horizontal, 'PV' for vertical polarization
        - Messfrequenz: frequency
        - Einheit Messfrequenz: unit of frequency
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
        - Some angles are greater than 360°/180°.
    """
    gdata_dict = {}
    with open (args.filename, 'r') as f:
        dr = DictReader (f, delimiter = ';')
        for rec in dr:
            args.dB_unit = rec ['Einheit Messwert']
            f = float (rec ['Messfrequenz']) * 1e3 # MHz
            if f not in gdata_dict:
                p = rec ['Polarisation'][1:]
                k = (f, p)
                if k not in gdata_dict:
                    gdata_dict [k] = aplot.Gain_Data (k)
                gdata = gdata_dict [k]
            azi = float (rec ['Position Drehscheibe']) % 360
            # Need to round elevation values: these sometimes differ
            # during a scan
            ele = round (float (rec ['Position Positionierer']), 0) % 180
            # Don't allow values outside angle range
            if azi < 0 or azi > 360 or ele < 0 or ele > 360:
                continue
            # We treat the value as 'dBi' although this is dBm
            # Probably needs conversion but we may get away with
            # allowing a unit to be specified for the plot, it must be a
            # dezibel value, though (not linear gain or so)
            gain = float (rec ['Messwert'])
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
    args = aplot.process_args (cmd, argv)
    if pic_io is not None:
        args.output_file = pic_io
        args.save_format = 'png'
    gdata = parse_csv_measurement_data (args)
    gp = aplot.Gain_Plot (args, gdata)
    gp.compute ()
    gp.plot ()
# end def main_csv_measurement_data

if __name__ == '__main__':
    main_csv_measurement_data ()
