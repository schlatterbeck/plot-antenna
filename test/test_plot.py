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
from PIL import Image
from bisect import bisect_left
from plot_antenna.plot_antenna import main
from io import BytesIO
import matplotlib

# These are the generated pictures hashed by matplotlib version
# These were tested on:
# - Version 3.0.2 on python3.7.3  (debian buster)
# - Version 3.3.4 on python3.9.2  (debian bullseye)
# - Version 3.5.2 on python3.10.5 (own python build on debian bullseye)
# - Version 3.6.3 on python3.11.2 (debian bookworm)
# - Version 3.7.2 on python3.11.2 (debian bookwork in a venv)
# 
picture_hashes = dict \
    (( (( ( '3d', dict
            (( ('3.0.2', 'c76bc62f80106d79020af66d5ba30cbe32133255')
            ,  ('3.3.4', '5e21cd5e0bf83b94a606588c4e7a3f3e52d1d152')
            ,  ('3.5.2', '4e3be16ee73e143ab6d8e925d37fd54b9a3bb5a5')
            ,  ('3.6.3', '5e21cd5e0bf83b94a606588c4e7a3f3e52d1d152')
            ))
          )
       ,  ( 'azimuth', dict
            (( ('3.0.2', '81248b39e78fe707f59d732c8556a34e164add4f')
            ,  ('3.3.4', '55f83891c3c297962e24def9d5e5d565eee58a72')
            ,  ('3.5.2', '600221ff9765308069809711a779ea970de301b0')
            ,  ('3.6.3', '55f83891c3c297962e24def9d5e5d565eee58a72')
            ))
          )
       ,  ( 'azimuth_db', dict
            (( ('3.0.2', '91e3b791966caf17b1d5189d1ffe49d81fe753db')
            ,  ('3.3.4', '853f2e33d97921a1e29b168af6c72d9102857f0c')
            ,  ('3.5.2', 'e24bb294450bf3e666ab9e5d38fe659fa12bbd89')
            ,  ('3.6.3', '853f2e33d97921a1e29b168af6c72d9102857f0c')
            ))
          )
       ,  ( 'azimuth_linear', dict
            (( ('3.0.2', '660561393437790656f2be40f9959f6ee0040e18')
            ,  ('3.3.4', 'b294d474542522e2a598d37b8ce959faa253f164')
            ,  ('3.5.2', '283645c8cd248738afde0c512bbca6ddfe676118')
            ,  ('3.6.3', 'b294d474542522e2a598d37b8ce959faa253f164')
            ))
          )
       ,  ( 'azimuth_linear_voltage', dict
            (( ('3.0.2', 'ca0eb9b31d54d453dabc3be5594de15abd13881c')
            ,  ('3.3.4', '8852f490bb274471a1d4453ab0ddfe29a689ae9f')
            ,  ('3.5.2', '957e8bf68dc3155f9a98c3d7061049d797107f6f')
            ,  ('3.6.3', '8852f490bb274471a1d4453ab0ddfe29a689ae9f')
            ))
          )
       ,  ( 'basic_output', dict
            (( ('3.0.2', 'b9362d804d86a8be3870c460a162aae974a05955')
            ,  ('3.3.4', '931a908acb08eeebda27e680b12737cdbae95f1e')
            ,  ('3.5.2', '3ce7634a5bcff4d6a9591c68f4604325938bb5ed')
            ,  ('3.6.3', '931a908acb08eeebda27e680b12737cdbae95f1e')
            ))
          )
       ,  ( 'elevation', dict
            (( ('3.0.2', 'fd0b835fde4c976a88fd4c8419fc47ab3788f151')
            ,  ('3.3.4', '12a547c561497050af11bd72a1e55561b00a2f5b')
            ,  ('3.5.2', 'abcbfd16546a9aa4e02781955b3e2253cf01d0aa')
            ,  ('3.6.3', '12a547c561497050af11bd72a1e55561b00a2f5b')
            ))
          )
       ,  ( 'gainfile', dict
            (( ('3.0.2', 'a07f6166e68ee408a4131c866ebbe3f4bc94aa59')
            ,  ('3.3.4', 'e7a5888d1499494818eaf110f30cc7c06e7e3543')
            ,  ('3.5.2', '1ef7b62708590b2bcd6ed5afc23da63f111f9f84')
            ,  ('3.6.3', 'e7a5888d1499494818eaf110f30cc7c06e7e3543')
            ))
          )
       ,  ( 'necfile', dict
            (( ('3.0.2', '1d18ad114babc69bf459cabc0a46b7fa16aa8e74')
            ,  ('3.3.4', 'b2e735ae8f7fb2190c5c97fc44ead3299f8e86a4')
            ,  ('3.5.2', '493b0ec0cca1b872c426e6e06634593cbc81bfff')
            ,  ('3.6.3', 'b2e735ae8f7fb2190c5c97fc44ead3299f8e86a4')
            ))
          )
       ,  ( 'plotall', dict
            (( ('3.0.2', 'cf2d56853c9b9eba5b46188c96b4f990276d9f85')
            ,  ('3.3.4', '5a3267e9be54120d4871d724715e0c7fb1a39a25')
            ,  ('3.5.2', '568a0c3c7a2cc4ceb9c4d9a148420dc71e86dd1a')
            ,  ('3.6.3', '5a3267e9be54120d4871d724715e0c7fb1a39a25')
            ))
          )
       ,  ( 'vswr', dict
            (( ('3.0.2', '197c45672a1de86c6c6ca9cbfc2c899c28d0690e')
            ,  ('3.3.4', '6495b1f3e7c6c55ba06071dec4b24bc6bc9a3d59')
            ,  ('3.5.2', '71b310cf1c733d3f41272d27bde5a9cce69a8c9b')
            ,  ('3.6.3', '6495b1f3e7c6c55ba06071dec4b24bc6bc9a3d59')
            ))
          )
       ,  ( 'vswr_extended', dict
            (( ('3.0.2', 'fail')
            ,  ('3.3.4', 'fail')
            ,  ('3.5.2', '1bae165fbff4bce9597c629b89a858a6b207d72f')
            ,  ('3.6.3', 'fd6d0ff1b4be457d7a09f7e9743901c5e0356500')
            ))
          )
       ))
    ))

def get_picture_hash (function_name):
    """ Get picture hash from picture_hashes via the function name and
        the current matplotlib version.
    """
    assert function_name.startswith ('test_')
    key = function_name [5:]
    mpl_v = matplotlib.__version__
    if mpl_v not in picture_hashes [key]:
        versions = list (sorted (picture_hashes [key]))
        idx = bisect_left (versions, mpl_v)
        if idx == 0:
            return [picture_hashes [key][versions [idx]]]
        l = len (versions)
        if idx >= l - 1:
            # Return last *two*, seems sometimes it matches an earlier version
            return [picture_hashes [key][i] for i in versions [l - 2:]]
        return [picture_hashes [key][versions [i]] for i in (idx, idx + 1)]
    return [picture_hashes [key][mpl_v]]
# end def get_picture_hash

def check_status_matplotlib (v):
    hashes = get_picture_hash (v.__name__)
    if 'fail' in hashes:
        return pytest.mark.xfail (v)
    return v
# end def check_status_matplotlib

class Test_Plot (unittest.TestCase):

    @pytest.fixture (autouse=True)
    def cleanup (self):
        self.pic_io = BytesIO ()
        yield
    # end def cleanup

    def compare_cs (self):
        calling_fun = inspect.stack () [1].function
        img = Image.open (self.pic_io, formats = ['PNG', 'png'])
        io  = BytesIO ()
        img.save (io, format = 'ppm')
        cs = hashlib.sha1 (io.getvalue ()).hexdigest ()
        assert cs in get_picture_hash (calling_fun)
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

    @check_status_matplotlib
    def test_azimuth_linear (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "--scaling-method=linear", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_linear

    @check_status_matplotlib
    def test_azimuth_linear_voltage (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "--scaling-method=linear_voltage", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_linear_voltage

    @check_status_matplotlib
    def test_azimuth_db (self):
        infile = "test/12-el-5deg.pout"
        args = ["--azi", "--scaling-method=linear_db", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_azimuth_db

    @check_status_matplotlib
    def test_elevation (self):
        infile = "test/12-el-1deg.pout"
        args = ["--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_elevation

    @check_status_matplotlib
    def test_3d (self):
        infile = "test/12-el-5deg.pout"
        args = ["--plot3d", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    @check_status_matplotlib
    def test_plotall (self):
        infile = "test/inverted-v.pout"
        args = [infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    @check_status_matplotlib
    def test_vswr (self):
        infile = "test/inverted-v.pout"
        args = ["--vswr", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    @check_status_matplotlib
    def test_vswr_extended (self):
        infile = "test/u29gbuv0.nout"
        args = ["--vswr", "--swr-show-bands", "--swr-show-impedance"
               , "--system-impedance=4050", infile
               ]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    @check_status_matplotlib
    def test_basic_output (self):
        infile = "test/vdipole-01.bout"
        args = ["--ele", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    @check_status_matplotlib
    def test_gainfile (self):
        """ Original basic implementation can save gains to a file
        """
        infile = "test/DP001.GNN"
        args = ["--ele", "--angle-azi=60", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    @check_status_matplotlib
    def test_necfile (self):
        """ We also can parse nec2c output
        """
        infile = "test/12-el.nout"
        args = ["--azi", "--swr", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

# end class Test_Plot
