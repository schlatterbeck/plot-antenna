# Copyright (C) 2022-25 Ralf Schlatterbeck. All rights reserved
# Reichergasse 131, A-3411 Weidling
# ****************************************************************************
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software. 
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ****************************************************************************

import os
import unittest
import pytest
import filecmp
import hashlib
from PIL import Image
from bisect import bisect_left
from plot_antenna.plot_antenna import main
from plot_antenna.contrib import main_csv_measurement_data
from plot_antenna.eznec import main_eznec
from io import BytesIO
from glob import glob
import matplotlib
import plotly
try:    
    from smithplot.smithaxes import SmithAxes
except ImportError:
    SmithAxes = None

# These are the generated pictures hashed by matplotlib version
# These were tested on:
# - Version 3.5.2 on python3.10.5 (debian bookworm in a venv)
# - Version 3.6.3 on python3.11.2 (debian bookworm)
# - Version 3.7.2 on python3.11.2 (debian bookworm in a venv)
# For plotly these are tested on
# - Version 5.4.0  on python3.11.2 (plotly + python debian bookworm)
# - Version 5.10.0 on python3.10.5 (own python build)
# - Version 5.15.0 on python3.11.2 (debian bookworm in a venv)
# Note that different outcome for the same version can depend on the
# fonts installed in the system. So I'm quite sure this doesn't cover
# all possible configurations.
# Debian stable aka bookworm has matplotlib version 3.6.3 and plotly
# version 5.4.0. The other versions are tested in venvs.
#
# If a version is not available as a picture we do a binary search and take
# the next and the prior version
#

def pic_filename_and_glob (function_name):
    """ Return picture file name and glob pattern
        The glob pattern is without version number
    """
    assert function_name.startswith ('test_')
    key = function_name [5:]
    if key.endswith ('_plotly'):
        version = plotly.__version__
        pfx = 'P'
    else:
        version = matplotlib.__version__
        pfx = 'M'
    fn = 'test/pics/%(pfx)s.%(version)s.%(key)s.png' % locals ()
    pattern  = 'test/pics/%(pfx)s.*.%(key)s.png' % locals ()
    return fn, pattern
# end def pic_filename_and_glob

def hash_from_pic_obj (obj):
    """ Compute hash from picture
        Image.open can read from a file (given by name) or from a
        file-like object
        We need to convert to ppm, the png format stores too much info
        that is different for the same picture
    """
    img = Image.open (obj, formats = ['PNG', 'png'])
    io  = BytesIO ()
    img.save (io, format = 'ppm')
    return hashlib.sha1 (io.getvalue ()).hexdigest ()
# end def hash_from_pic_obj

def get_picture_hash (function_name):
    """ Get picture hash from picture file via the function name and
        the current matplotlib version.
    """
    cs = []
    fn, pattern = pic_filename_and_glob (function_name)
    try:
        cs.append (hash_from_pic_obj (fn))
    except FileNotFoundError:
        pass
    if not cs:
        versions = list (sorted (glob (pattern)))
        idx = bisect_left (versions, fn)
        l   = len (versions)
        if not l:
            globfn = []
        elif idx >= l - 1:
            globfn = versions [l-2:]
        else:
            globfn = versions [idx:idx+2]
        for name in globfn:
            cs.append (hash_from_pic_obj (name))
    return cs
# end def get_picture_hash

def check_status_matplotlib (v):
    # Currently there are no instances of test failures
    return v
# end def check_status_matplotlib

def check_smith_available (v):
    if SmithAxes is None:
        return pytest.mark.xfail (v)
    return check_status_matplotlib (v)
# end def check_smith_available

class Test_Plot (unittest.TestCase):
    debug = False

    @pytest.fixture (autouse=True)
    def cleanup (self, request):
        self.test_name = request.node.name
        self.pic_io = BytesIO ()
        yield
        rep_call = getattr (request.node, 'rep_call', None)
        rep_fail = \
            rep_call and not rep_call.passed and rep_call.outcome != 'skipped'
        if rep_fail or self.debug:
            fn, _ = pic_filename_and_glob (self.test_name)
            with open (fn + '.debug', 'wb') as f:
                f.write (self.pic_io.getvalue ())
    # end def cleanup

    def compare_cs (self):
        cs = hash_from_pic_obj (self.pic_io)
        assert cs in get_picture_hash (self.test_name)
    # end def compare_cs

    def test_cmdline_err (self):
        infile = "test/12-el-5deg.pout"
        args = ["--scaling-method=linear_db", "--scaling-mindb=7", infile]
        self.assertRaises (ValueError, main, args)
    # end def test_cmdline_err

    @check_status_matplotlib
    def test_azimuth (self):
        infile = "test/12-el-1deg.pout"
        args = ["--azi", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth

    def test_azimuth_plotly (self):
        infile = "test/12-el-1deg.pout"
        args = ["--azi", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_plotly

    @check_status_matplotlib
    def test_azimuth_linear (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "--scaling-method=linear", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_linear

    def test_azimuth_linear_plotly (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "-S", "--scaling-method=linear", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_linear_plotly

    @check_status_matplotlib
    def test_azimuth_linear_voltage (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "--scaling-method=linear_voltage", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_linear_voltage

    def test_azimuth_linear_voltage_plotly (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "-S", "--scaling-method=linear_voltage", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_linear_voltage_plotly

    @check_status_matplotlib
    def test_azimuth_db (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "--scaling-method=linear_db", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_db

    def test_azimuth_db_plotly (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "-S", "--scaling-method=linear_db", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_db_plotly

    @check_status_matplotlib
    def test_elevation (self):
        infile = "test/12-el-1deg.pout"
        args = ["--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_elevation

    def test_elevation_plotly (self):
        infile = "test/12-el-1deg.pout"
        args = ["--ele", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_elevation_plotly

    @check_status_matplotlib
    def test_3d (self):
        infile = "test/12-el-5deg.pout"
        args = ["--title=", "--plot3d", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    def test_3d_plotly (self):
        infile = "test/12-el-5deg.pout"
        args = ["--title=", "--plot3d", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d_plotly

    @check_status_matplotlib
    def test_plotall (self):
        infile = "test/inverted-v.pout"
        args = [infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_plotall

    @check_status_matplotlib
    def test_vswr (self):
        infile = "test/inverted-v.pout"
        args = ["--title=", "--vswr", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr

    def test_vswr_plotly (self):
        infile = "test/inverted-v.pout"
        args = ["--title=", "--vswr", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr_plotly

    @check_status_matplotlib
    def test_vswr_extended (self):
        infile = "test/u29gbuv0.nout"
        args = '''--title= --vswr --swr-show-bands --swr-show-imp
                  --system-impedance=4050 --width=700 --height=400'''
        args = args.split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr_extended

    def test_vswr_extended_plotly (self):
        infile = "test/u29gbuv0.nout"
        args = '''-S --title= --vswr --swr-show-bands --swr-show-imp
                  --system-impedance=4050 --width=1000
                  --axis-3-pos=1 --legend-x=1.07'''
        args = args.split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr_extended_plotly

    @check_status_matplotlib
    def test_basic_output (self):
        infile = "test/vdipole-01.bout"
        args = ["--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_basic_output

    def test_basic_output_plotly (self):
        infile = "test/vdipole-01.bout"
        args = ["--ele", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_basic_output_plotly

    @check_status_matplotlib
    def test_gainfile (self):
        """ Original basic implementation can save gains to a file
        """
        infile = "test/DP001.GNN"
        args = ["--ele", "--angle-azi=60", "--default-f=14MHz", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_gainfile

    def test_gainfile_plotly (self):
        """ Original basic implementation can save gains to a file
        """
        infile = "test/DP001.GNN"
        args = ["--ele", "-S", "--angle-azi=60", "--default-f=14MHz", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_gainfile_plotly

    @check_status_matplotlib
    def test_necfile (self):
        """ We also can parse nec2c output
        """
        infile = "test/12-el.nout"
        args = ["--azi", "--swr", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_necfile

    def test_necfile_azi_plotly (self):
        """ We also can parse nec2c output
        """
        infile = "test/12-el.nout"
        args = ["--azi", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_necfile_azi_plotly

    def test_necfile_swr_plotly (self):
        """ We also can parse nec2c output
        """
        infile = "test/12-el.nout"
        args = ["--title=", "--swr", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_necfile_swr_plotly

    @check_smith_available
    def test_smith (self):
        infile = "test/u29gbuv0.nout"
        args = ["--smith", "--system-impedance=4050", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_smith

    def test_smith_plotly (self):
        """ We also can parse nec2c output
        """
        infile = "test/u29gbuv0.nout"
        args = ["--smith", "--system-impedance=4050", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_smith_plotly

    def test_geo (self):
        infile = "test/inve802B.pout"
        args = ["--title=", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo

    def test_geo_plotly (self):
        infile = "test/inve802B.pout"
        args = ["--title=", "--geo", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_plotly

    def test_geo_s_para (self):
        infile = "test/inve802B_S.pout"
        args = ["--title=", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_s_para

    def test_geo_s_para_plotly (self):
        infile = "test/inve802B_S.pout"
        args = ["--title=", "--geo", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_s_para_plotly

    def test_measurement (self):
        infile = "test/Messdaten.csv"
        args = ["--ele", "--polari=H", infile]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement

    def test_measurement_plotly (self):
        infile = "test/Messdaten.csv"
        args = ["--ele", "--polari=H", "-S", infile]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement_plotly

    def test_measurement_full (self):
        infile = "test/Messdaten.csv"
        args = [ "--azi", "--polari=H", "--polari=V", "--polari=sum"
               , "--matp", "--angle-ele=-27", "--round-ele=2", infile
               ]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement_full

    def test_measurement_full_plotly (self):
        infile = "test/Messdaten.csv"
        args = [ "--azi", "--polari=H", "--polari=V", "--polari=sum"
               , "--matp", "--angle-ele=-27", "--round-ele=2", "-S", infile
               ]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement_full_plotly

    def test_geo_bug_plotly (self):
        infile = "test/geo-bug.nout"
        args = ["--title=", "--geo", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_bug_plotly

    def test_monopole (self):
        infile = "test/diphalf.nout"
        args = ["--title=", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_monopole

    def test_monopole_plotly (self):
        infile = "test/diphalf.nout"
        args = ["--title=", "--geo", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_monopole_plotly

    def test_old_mininec_ele (self):
        infile = "test/mininec-1.bout"
        args = ["--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_old_mininec_ele

    def test_old_mininec_ele_plotly (self):
        infile = "test/mininec-1.bout"
        args = ["-S", "--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_old_mininec_ele_plotly

    def test_old_mininec_geo (self):
        infile = "test/mininec-1.bout"
        args = ["--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_old_mininec_geo

    def test_old_mininec_geo_plotly (self):
        infile = "test/mininec-1.bout"
        args = ["-S", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_old_mininec_geo_plotly

    def test_mininec_3_ele (self):
        infile = "test/mininec-3.bout"
        args = ["--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_mininec_3_ele

    def test_mininec_3_ele_plotly (self):
        infile = "test/mininec-3.bout"
        args = ["-S", "--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_mininec_3_ele_plotly

    def test_mininec_3_geo (self):
        infile = "test/mininec-3.bout"
        args = ["--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_mininec_3_geo

    def test_mininec_3_geo_plotly (self):
        infile = "test/mininec-3.bout"
        args = ["-S", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_mininec_3_geo_plotly

    def test_swr_tickmarks (self):
        infile = "test/inverted-v.pout"
        args = '--vswr --swr-show-impedance'.split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_swr_tickmarks

    def test_swr_tickmarks_plotly (self):
        infile = "test/inverted-v.pout"
        args = '-S --vswr --swr-show-impedance --width=1000 --height=500'
        args = args.split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_swr_tickmarks_plotly

    def test_swr_band_range (self):
        """ Test limit the colored area of the band to the X plot range
        """
        infile = "test/inverted-v.pout"
        args = '--vswr --swr-show-bands --swr-show-impedance'.split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_swr_band_range

    def test_asap_geo (self):
        infile = "test/3-ele-10deg.aout"
        args = ['--geo', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_geo

    def test_asap_geo_plotly (self):
        infile = "test/3-ele-10deg.aout"
        args = ['-S', '--geo', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_geo_plotly

    def test_asap_azi (self):
        infile = "test/3-ele-10deg.aout"
        args = ['--azi', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_azi

    def test_asap_azi_plotly (self):
        infile = "test/3-ele-10deg.aout"
        args = ['-S', '--azi', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_azi_plotly

    def test_asap_ele (self):
        infile = "test/3-ele-10deg.aout"
        args = ['--ele', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_ele

    def test_asap_ele_plotly (self):
        infile = "test/3-ele-10deg.aout"
        args = ['-S', '--ele', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_ele_plotly

    def test_asap_3d (self):
        infile = "test/3-ele-10deg.aout"
        args = ['--ele', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_3d

    def test_asap_3d_plotly (self):
        infile = "test/3-ele-10deg.aout"
        args = ['-S', '--3d', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_3d_plotly

    def test_asap_swr (self):
        infile = "test/3-ele-10deg.aout"
        args = ['--swr', '--swr-show-impedance', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_swr

    def test_asap_swr_plotly (self):
        infile = "test/3-ele-10deg.aout"
        args = '-S --swr --swr-show-imp --width=1000 --legend-x=1.04'.split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_asap_swr_plotly

    def test_eznec_azi (self):
        infile = "test/tapered.eout"
        args = ['--azi', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_azi

    def test_eznec_azi_plotly (self):
        infile = "test/tapered.eout"
        args = ['-S', '--azi', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_azi_plotly

    def test_eznec_ele (self):
        infile = "test/tapered.eout"
        args = ['--ele', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_ele

    def test_eznec_ele_plotly (self):
        infile = "test/tapered.eout"
        args = ['-S', '--ele', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_ele_plotly

    def test_eznec_3d (self):
        infile = "test/tapered.eout"
        args = ['--ele', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_3d

    def test_eznec_3d_plotly (self):
        infile = "test/tapered.eout"
        args = ['-S', '--3d', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_3d_plotly

    def test_eznec_swr (self):
        infile = "test/lastz.eout"
        args = ['--vswr', '--swr-show-imp', infile]
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_swr

    def test_eznec_swr_plotly (self):
        infile = "test/lastz.eout"
        args = '''-S --vswr --swr-show-imp --width=1000 --height=500
                  --legend-x=1.04 --axis-3-pos=.99'''.split ()
        args.append (infile)
        main_eznec (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_eznec_swr_plotly

    def test_nec_geo_inv_v (self):
        """ This tests a case where we had a parsing error in geo
        """
        infile = "test/inverted-v-thin.nout"
        args = ['--ele', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_nec_geo_inv_v

    def test_4nec2_azi (self):
        infile = 'test/dip-4n.4out'
        args = ['--azi', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_azi

    def test_4nec2_azi_plotly (self):
        infile = 'test/dip-4n.4out'
        args = ['-S', '--azi', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_azi_plotly

    def test_4nec2_ele (self):
        infile = 'test/dip-4n.4out'
        args = ['--ele', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_ele

    def test_4nec2_ele_plotly (self):
        infile = 'test/dip-4n.4out'
        args = ['-S', '--ele', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_ele_plotly

    def test_4nec2_3d (self):
        infile = 'test/dip-4n.4out'
        args = ['--3d', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_3d

    def test_4nec2_3d_plotly (self):
        infile = 'test/dip-4n.4out'
        args = ['-S', '--3d', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_3d_plotly

    def test_4nec2_geo (self):
        infile = 'test/dip-4n.4out'
        args = ['--geo', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_geo

    def test_4nec2_geo_plotly (self):
        infile = 'test/dip-4n.4out'
        args = ['-S', '--geo', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_geo_plotly

    def test_4nec2_swr (self):
        infile = 'test/dip-4n.4out'
        args = ['--swr', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_4nec2_swr

    def test_fortran_swr (self):
        infile = 'test/dip-som.out'
        args = ['--swr', infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_fortran_swr

    def test_geo_gridhelix (self):
        infile = "test/helix-small.nout"
        args = ["--title=", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_gridhelix

    def test_geo_gridhelix_plotly (self):
        infile = "test/helix-small.nout"
        args = ["--title=", "--geo", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_gridhelix_plotly

    def test_geo_simple (self):
        infile = "test/t2.nout"
        args = ["--title=", "--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo_simple

    def test_scale_by_angle (self):
        infile = "test/inve802B.pout"
        args = "--title= --azi --angle-ele=35 --scale-by-angle".split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_scale_by_angle

    def test_scale_by_angle_plotly (self):
        infile = "test/inve802B.pout"
        args = "-S --title= --azi --angle-ele=35 --scale-by-angle".split ()
        args.append (infile)
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_scale_by_angle_plotly

# end class Test_Plot
