# Copyright (C) 2022 Ralf Schlatterbeck. All rights reserved
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
from plot_antenna.plot_antenna import main

class Test_Plot (unittest.TestCase):
    outfile = 'zoppel-test.png'

    @pytest.fixture (autouse=True)
    def cleanup (self):
        yield
        try:
            os.unlink (self.outfile)
        except FileNotFoundError:
            pass
    # end def cleanup

    def compare_cs (self, checksums):
        with open (self.outfile, 'rb') as f:
            contents = f.read ()
        cs = hashlib.sha1 (contents).hexdigest ()
        assert cs in checksums
    # end def compare_cs

    def test_cmdline_err (self):
        infile = "test/12-el-5deg.pout"
        args = ["--scaling-method=linear_db", "--scaling-mindb=7", infile]
        self.assertRaises (ValueError, main, args)
    # end def test_cmdline_err

    def test_azimuth (self):
        checksums = set \
            (( '4ba633ef2d286cbfd07bc0f845dbd92f6063bd72'
             , 'cae02fba0ce8d6c84397d70f8f267adfce2334b7'
             , '6f7e3004927ddf2623c87d5976ca19053b1b342d'
            ))
        infile = "test/12-el-1deg.pout"
        args = ["--azi", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_azimuth

    def test_azimuth_linear (self):
        checksums = set \
            (( '6edb2e10c24cd218ea6f7b544950b99cfc58bbd8'
             , 'bdb0566025474fdb3ff2bba6a3040a44b8ac0d43'
             , '74c1316ce650cd8554b58e6581a019c2e3223275'
            ))
        infile = "test/12-el-5deg.pout"
        args = [ "--azi", "--scaling-method=linear"
               , "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs (checksums)
    # end def test_azimuth_linear

    def test_azimuth_linear_voltage (self):
        checksums = set \
            (( 'a0c104f1e87b98bc4c5d716c65486ca1c37755aa'
             , '3102f95ceca5c3767f4b064def9ef1e701eb05db'
             , '269dfb8af39cd2e6bfde89868a0ef7ee83c76e9b'
            ))
        infile = "test/12-el-5deg.pout"
        args = [ "--azi", "--scaling-method=linear_voltage"
               , "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs (checksums)
    # end def test_azimuth_linear_voltage

    def test_azimuth_db (self):
        checksums = set \
            (( '650172f1ea286ed2eeeda9060c035ffc65f7a640'
             , '4737bd0c3e172014f7b13d3da3f4e165c223fb6a'
             , '046df401b907a6e7adf7cc84862de3a19a599981'
            ))
        infile = "test/12-el-5deg.pout"
        args = [ "--azi", "--scaling-method=linear_db"
               , "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs (checksums)
    # end def test_azimuth_db

    def test_elevation (self):
        checksums = set \
            (( 'cb7e1d536a4f25c686eed0ee2338ee171144afdd'
             , 'fd4ec4e93099432df09b7debe7663c9e9160c69a'
             , 'fec43025d6efe53d2a2dff877cec6aaafc6660c9'
            ))
        infile = "test/12-el-1deg.pout"
        args = ["--ele", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_elevation

    def test_3d (self):
        checksums = set \
            (( 'bf0053e8fafbf5b7a28fc1dd3f40a66a500fb797'
             , 'f106dccd3ccff1938d47664cba5f659b2560d27b'
             , '67d5f8a4cd30154754ececc0e8d22c6eba92a7c5'
            ))
        infile = "test/12-el-5deg.pout"
        args = ["--plot3d", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_plotall (self):
        checksums = set \
            (( 'b6954156e247485180c98f7c22489d4eb6d035d1'
             , '741be574591ae25d3277b23e4d63403ccc16ffab'
             , '6128cf125ae9b03837733117871601e4cebde090'
            ))
        infile = "test/inverted-v.pout"
        args = ["--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_vswr (self):
        checksums = set \
            (( '0199f336fd4c485068fc5871f0fbddc38c5dcf90'
             , '6ac6760bdbcf8252521b426ec4447df5cf9021a1'
             , '85ae44a0a42095548289b0bcc58f3be076c985a1'
            ))
        infile = "test/inverted-v.pout"
        args = ["--vswr", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_basic_output (self):
        checksums = set \
            (( 'a93fd750b4492788282d8edc6f2c6cae5cbcc972'
             , '30791dceac2bf8332b11d714989e777c63168a44'
             , 'eb638463bdab9c380b9c04242f3b230495ca3a12'
            ))
        infile = "test/vdipole-01.bout"
        args = ["--ele", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_gainfile (self):
        """ Original basic implementation can save gains to a file
        """
        checksums = set \
            (( '7e74e90107298586e93503b117cc59a6400d9232'
             , '0e1b066d1486e33b720728fc0c6ea2a1e1e2aa24'
             , '75e08e9c80b248abef3aa240c50898bb2db9a6db'
            ))
        infile = "test/DP001.GNN"
        args = ["--ele", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_necfile (self):
        """ We also can parse nec2c output
        """
        checksums = set \
            (( '914fe4fb6668f6fdd4f0ec2d8d16917dc2b0257f'
             , '7ac55ddedc11e35269488aa97058a68fa7a2df5f'
             , 'cfaee57e61f48c07320f4ce66720146df68d00c0'
            ))
        infile = "test/12-el.nout"
        args = ["--azi", "--swr", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

# end class Test_Plot
