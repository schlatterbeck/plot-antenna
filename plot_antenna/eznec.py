#!/usr/bin/python3

import sys
from csv import DictReader
from . import plot_antenna as aplot

def parse_eznec_data (args):
    """ Parses eznec date exported with 'FF Tab'
        This is either organized in Azimuth- or Elevation slices.
        We determine the format during parsing.
        It looks like the format supports only a single frequency.
    """
    gdata_dict = {}
    state_seen = None
    state      = 'start'
    head_seen  = False
    gdata_dict = {}
    with open (args.filename, 'r') as rfile:
        for line in rfile:
            line = line.strip ()
            if state == 'start':
                if line.startswith ('Frequency'):
                    if not line.endswith ('MHz'):
                        raise ValueError \
                            ('Unsupported frequency format: %s' % line)
                    frq = float (line.rsplit () [-2])
                    continue
                if 'Pattern' in line:
                    if line.startswith ('Azimuth'):
                        state = 'azi'
                    elif line.startswith ('Elevation'):
                        state = 'ele'
                    else:
                        raise ValueError ('Unsupported slice format %s' % line)
                    if state_seen and state_seen != state:
                        raise ValueError ('Mid-file change of slice format')
                    state_seen = state
                    r = line.split ('=', 1) [1]
                    r = r.split () [0]
                    angle     = int (r)
                    if state == 'azi':
                        angle += 90
                    head_seen = False
                    continue
            if state in ('azi', 'ele'):
                if not head_seen:
                    l = ' '.join (line.split ())
                    if l != 'Deg V dB H dB Tot dB V Pha H Pha':
                        raise ValueError ('Expect Degree line, got %s' % line)
                    head_seen = True
                    continue
                if not line:
                    state = 'start'
                    continue
                values = line.split ()
                deg = int (values [0])
                if state == 'ele':
                    if 90 < deg < 270:
                        continue
                    if deg <= 90:
                        deg += 90
                    elif deg >= 270:
                        deg -= 270
                vert, hori, tot = (float (x) for x in values [1:4])
                gd = {}
                for pol, gain in zip (('H', 'V', 'sum'), (hori, vert, tot)):
                    k = (frq, pol)
                    if k not in gdata_dict:
                        gdata_dict [k] = aplot.Gain_Data (k)
                    gdata = gdata_dict [k]
                    if state == 'azi':
                        ele = angle
                        azi = deg
                    else:
                        ele = deg
                        azi = angle
                    #print (ele, azi, pol, gain)
                    gdata.pattern [(ele, azi)] = gain
    return gdata_dict
# end def parse_csv_measurement_data

def main_eznec (argv = sys.argv [1:], pic_io = None):
    """ Parse eznec far field data.
    """
    cmd = aplot.options_general ()
    aplot.options_gain (cmd)
    cmd.add_argument ('filename', help = 'EZNEC far field data to plot')
    args = aplot.process_args (cmd, argv)
    if pic_io is not None:
        args.output_file = pic_io
        args.save_format = 'png'
    gdata = parse_eznec_data (args)
    gp = aplot.Gain_Plot (args, gdata)
    gp.compute ()
    gp.plot ()
# end def main_eznec

if __name__ == '__main__':
    main_eznec ()
