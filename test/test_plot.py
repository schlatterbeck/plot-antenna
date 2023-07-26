# Copyright (C) 2022-23 Ralf Schlatterbeck. All rights reserved
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
import matplotlib

def min_matplotlib (v):
    min_v = tuple (v.split ('.'))
    mpl_v = tuple (matplotlib.__version__.split ('.'))
    return pytest.mark.skipif \
        ( mpl_v < min_v
        , reason="at least matplotlib %s required" % v
        )

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
             , 'a0aa181e7d42364a5f44d56dcccd26fa0b5a660c'
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
             , '460c7d594304af83bfe9bba1cb06817e87e4e34a'
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
             , '11fae3c94c61eef98117a3fc7ac40d42afed8b9c'
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
             , '213dcf0dcfc22ce680aab2018404f31596b589f4'
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
            (( 'f62eb7f542e5c06be02b8d87085ef6be9a131c1a'
             , '9c2c0dbee27318762c446622e80565523cc9f27e'
             , '7d484d3007d44ad3d5346cc5c2d99e78dbe8a8cd'
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
             , '32e55a243512a33dd7d8d4569666e3e9f27f9c25'
            ))
        infile = "test/12-el-5deg.pout"
        args = ["--plot3d", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_plotall (self):
        checksums = set \
            (( 'c6983522ea756b757ae6a4017f59b7bf73d8a444'
             , '199e352d9c78d1eff20ff58bc006af686f978660'
             , 'bee0a8e420912fefafe112cfbbbd1bb45a6430e1'
            ))
        infile = "test/inverted-v.pout"
        args = ["--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_vswr (self):
        checksums = set \
            (( 'e0bc3945aeb821cdf03ee47d26d9d225752f046c'
             , 'c7d51ae7e9b99db01efca23883b0082f9a2e5cea'
             , '0249df3ae9c7f526e1701b8d1bc94841718c4c6c'
            ))
        infile = "test/inverted-v.pout"
        args = ["--vswr", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    @min_matplotlib ('3.1.0')
    def test_vswr_extended (self):
        checksums = set \
            (( 'db4eb15db1b4534bd8d7bfbc29b9d63262e5a673'
             , '7fbe093c9a406f7c25ec2e14ce0f5e157e5532aa'
             , ''
            ))
        infile = "test/u29gbuv0.nout"
        args = ["--vswr", "--swr-show-bands", "--swr-show-impedance"
               , "--system-impedance=4050", "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_basic_output (self):
        checksums = set \
            (( '45d9090245f3addcc7eba873863a595513b5ffd9'
             , '3b34a4da877eb65ec27d6245e70108f7f6847343'
             , '0ca9dfa12999c91a86ad5c623bc81eb90ef26fdc'
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
            (( 'e355a35ce2a6c23b0ba1ea3e59eb9363f764acff'
             , '5e205938df4dae1b731eff91f9bd1d0ab0c56f8d'
             , '2815d3fa423e30484cabc8c2e982d32c5bbcb891'
            ))
        infile = "test/DP001.GNN"
        args = ["--ele", "--angle-azi=60", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

    def test_necfile (self):
        """ We also can parse nec2c output
        """
        checksums = set \
            (( '3271f513a3cae9c3733c773d94e3fde65d988a39'
             , '4fbbdd11deb57eef1364b8cbd5fdefe2775ad8d5'
             , 'c8e63a94f1c73f6649c612187bfd047e38137945'
            ))
        infile = "test/12-el.nout"
        args = ["--azi", "--swr", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs (checksums)
    # end def test_3d

# end class Test_Plot
