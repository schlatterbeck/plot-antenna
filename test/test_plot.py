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
import inspect
from plot_antenna.plot_antenna import main
import matplotlib

# These are the generated pictures hashed by matplotlib version
# These were tested on:
# - Version 3.0.2 on python3.7.3  (debian buster)
# - Version 3.3.4 on python3.9.2  (debian bullseye)
# - Version 3.5.2 on python3.10.5 (own python build on debian bullseye)
# - Version 3.6.3 on python3.11.2 (debian bookworm)
# 
checksums = set \
            (( '4ba633ef2d286cbfd07bc0f845dbd92f6063bd72'
            ))
picture_hashes = dict \
    (( (( ( '3d', dict
            (( ('3.0.2', '67d5f8a4cd30154754ececc0e8d22c6eba92a7c5')
            ,  ('3.3.4', '')
            ,  ('3.5.2', 'f106dccd3ccff1938d47664cba5f659b2560d27b')
            ,  ('3.6.3', '32e55a243512a33dd7d8d4569666e3e9f27f9c25')
            ))
          )
       ,  ( 'azimuth', dict
            (( ('3.0.2', '6f7e3004927ddf2623c87d5976ca19053b1b342d')
            ,  ('3.3.4', '')
            ,  ('3.5.2', 'cae02fba0ce8d6c84397d70f8f267adfce2334b7')
            ,  ('3.6.3', 'a0aa181e7d42364a5f44d56dcccd26fa0b5a660c')
            ))
          )
       ,  ( 'azimuth_db', dict
            (( ('3.0.2', '046df401b907a6e7adf7cc84862de3a19a599981')
            ,  ('3.3.4', '')
            ,  ('3.5.2', '4737bd0c3e172014f7b13d3da3f4e165c223fb6a')
            ,  ('3.6.3', '213dcf0dcfc22ce680aab2018404f31596b589f4')
            ))
          )
       ,  ( 'azimuth_linear', dict
            (( ('3.0.2', '74c1316ce650cd8554b58e6581a019c2e3223275')
            ,  ('3.3.4', '')
            ,  ('3.5.2', 'bdb0566025474fdb3ff2bba6a3040a44b8ac0d43')
            ,  ('3.6.3', '460c7d594304af83bfe9bba1cb06817e87e4e34a')
            ))
          )
       ,  ( 'azimuth_linear_voltage', dict
            (( ('3.0.2', '269dfb8af39cd2e6bfde89868a0ef7ee83c76e9b')
            ,  ('3.3.4', '')
            ,  ('3.5.2', '3102f95ceca5c3767f4b064def9ef1e701eb05db')
            ,  ('3.6.3', '11fae3c94c61eef98117a3fc7ac40d42afed8b9c')
            ))
          )
       ,  ( 'basic_output', dict
            (( ('3.0.2', '45d9090245f3addcc7eba873863a595513b5ffd9')
            ,  ('3.3.4', '')
            ,  ('3.5.2', '0ca9dfa12999c91a86ad5c623bc81eb90ef26fdc')
            ,  ('3.6.3', '3b34a4da877eb65ec27d6245e70108f7f6847343')
            ))
          )
       ,  ( 'elevation', dict
            (( ('3.0.2', 'f62eb7f542e5c06be02b8d87085ef6be9a131c1a')
            ,  ('3.3.4', '')
            ,  ('3.5.2', '7d484d3007d44ad3d5346cc5c2d99e78dbe8a8cd')
            ,  ('3.6.3', '9c2c0dbee27318762c446622e80565523cc9f27e')
            ))
          )
       ,  ( 'gainfile', dict
            (( ('3.0.2', 'e355a35ce2a6c23b0ba1ea3e59eb9363f764acff')
            ,  ('3.3.4', '')
            ,  ('3.5.2', '2815d3fa423e30484cabc8c2e982d32c5bbcb891')
            ,  ('3.6.3', '5e205938df4dae1b731eff91f9bd1d0ab0c56f8d')
            ))
          )
       ,  ( 'necfile', dict
            (( ('3.0.2', '3271f513a3cae9c3733c773d94e3fde65d988a39')
            ,  ('3.3.4', '')
            ,  ('3.5.2', 'c8e63a94f1c73f6649c612187bfd047e38137945')
            ,  ('3.6.3', '4fbbdd11deb57eef1364b8cbd5fdefe2775ad8d5')
            ))
          )
       ,  ( 'plotall', dict
            (( ('3.0.2', 'c6983522ea756b757ae6a4017f59b7bf73d8a444')
            ,  ('3.3.4', '')
            ,  ('3.5.2', 'bee0a8e420912fefafe112cfbbbd1bb45a6430e1')
            ,  ('3.6.3', '199e352d9c78d1eff20ff58bc006af686f978660')
            ))
          )
       ,  ( 'vswr', dict
            (( ('3.0.2', 'e0bc3945aeb821cdf03ee47d26d9d225752f046c')
            ,  ('3.3.4', '')
            ,  ('3.5.2', '0249df3ae9c7f526e1701b8d1bc94841718c4c6c')
            ,  ('3.6.3', 'c7d51ae7e9b99db01efca23883b0082f9a2e5cea')
            ))
          )
       ,  ( 'vswr_extended', dict
            (( ('3.0.2', 'fail')
            ,  ('3.3.4', 'fail')
            ,  ('3.5.2', '7fbe093c9a406f7c25ec2e14ce0f5e157e5532aa')
            ,  ('3.6.3', 'db4eb15db1b4534bd8d7bfbc29b9d63262e5a673')
            ))
          )
       ))
    ))

def check_status (v):
    mpl_v = matplotlib.__version__
    fun = v.__name__
    assert fun.startswith ('test_')
    key = fun [5:]
    if picture_hashes [key][mpl_v] == 'fail':
        return pytest.mark.xfail (v)
    return v

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

    def compare_cs (self):
        calling_fun = inspect.stack () [1].function
        assert calling_fun.startswith ('test_')
        key = calling_fun [5:]
        with open (self.outfile, 'rb') as f:
            contents = f.read ()
        cs = hashlib.sha1 (contents).hexdigest ()
        assert cs == picture_hashes [key][matplotlib.__version__]
    # end def compare_cs

    def test_cmdline_err (self):
        infile = "test/12-el-5deg.pout"
        args = ["--scaling-method=linear_db", "--scaling-mindb=7", infile]
        self.assertRaises (ValueError, main, args)
    # end def test_cmdline_err

    @check_status
    def test_azimuth (self):
        infile = "test/12-el-1deg.pout"
        args = ["--azi", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_azimuth

    @check_status
    def test_azimuth_linear (self):
        checksums = set \
            (( '6edb2e10c24cd218ea6f7b544950b99cfc58bbd8'
            ))
        infile = "test/12-el-5deg.pout"
        args = [ "--azi", "--scaling-method=linear"
               , "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs ()
    # end def test_azimuth_linear

    @check_status
    def test_azimuth_linear_voltage (self):
        checksums = set \
            (( 'a0c104f1e87b98bc4c5d716c65486ca1c37755aa'
            ))
        infile = "test/12-el-5deg.pout"
        args = [ "--azi", "--scaling-method=linear_voltage"
               , "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs ()
    # end def test_azimuth_linear_voltage

    @check_status
    def test_azimuth_db (self):
        checksums = set \
            (( '650172f1ea286ed2eeeda9060c035ffc65f7a640'
            ))
        infile = "test/12-el-5deg.pout"
        args = [ "--azi", "--scaling-method=linear_db"
               , "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs ()
    # end def test_azimuth_db

    @check_status
    def test_elevation (self):
        checksums = set \
            ((
              '3f12165407b4676ba6e8706a50b7d9b3e31a7cc7'
            ))
        infile = "test/12-el-1deg.pout"
        args = ["--ele", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_elevation

    @check_status
    def test_3d (self):
        checksums = set \
            (( 'bf0053e8fafbf5b7a28fc1dd3f40a66a500fb797'
            ))
        infile = "test/12-el-5deg.pout"
        args = ["--plot3d", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_3d

    @check_status
    def test_plotall (self):
        checksums = set \
            (( 
              '939a52f8a1fa0e96579edccac772ea231c964175'
            ))
        infile = "test/inverted-v.pout"
        args = ["--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_3d

    @check_status
    def test_vswr (self):
        checksums = set \
            ((
              '8cb9304e4eee21c6144ed40de34daf56395a035c'
            ))
        infile = "test/inverted-v.pout"
        args = ["--vswr", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_3d

    @check_status
    def test_vswr_extended (self):
        infile = "test/u29gbuv0.nout"
        args = ["--vswr", "--swr-show-bands", "--swr-show-impedance"
               , "--system-impedance=4050", "--out=%s" % self.outfile, infile
               ]
        main (args)
        self.compare_cs ()
    # end def test_3d

    @check_status
    def test_basic_output (self):
        checksums = set \
            ((
              '21c6b094b727213378859e8ff78816de50bb7801'
            ))
        infile = "test/vdipole-01.bout"
        args = ["--ele", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_3d

    @check_status
    def test_gainfile (self):
        """ Original basic implementation can save gains to a file
        """
        checksums = set \
            ((
              '81f427701288da7988b26e67d78ee968a88fbc58'
            ))
        infile = "test/DP001.GNN"
        args = ["--ele", "--angle-azi=60", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_3d

    @check_status
    def test_necfile (self):
        """ We also can parse nec2c output
        """
        checksums = set \
            ((
              'bcebf95b5635edbf4104cc6d4c332544df854382'
            ))
        infile = "test/12-el.nout"
        args = ["--azi", "--swr", "--out=%s" % self.outfile, infile]
        main (args)
        self.compare_cs ()
    # end def test_3d

# end class Test_Plot
