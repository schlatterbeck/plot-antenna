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
import plotly

# These are the generated pictures hashed by matplotlib version
# These were tested on:
# - Version 3.0.2 on python3.7.3  (debian buster)
# - Version 3.3.4 on python3.9.2  (debian bullseye)
# - Version 3.5.2 on python3.10.5 (own python build on debian bullseye)
# - Version 3.6.3 on python3.11.2 (debian bookworm)
# - Version 3.7.2 on python3.11.2 (debian bookworm in a venv)
# For plotly these are tested on
# - Version 5.4.0  on python3.11.2 (plotly + python debian bookworm)
# - Version 5.10.0 on python3.10.5 (own python build)
# - Version 5.15.0 on python3.11.2 (debian bookworm in a venv)
# Note that different outcome for the same version can depend on the
# fonts installed in the system. So I'm quite sure this doesn't cover
# all possible configurations.
#
picture_hashes = dict \
    (( (( ( '3d', dict
            (( ('3.0.2', 'c76bc62f80106d79020af66d5ba30cbe32133255')
            ,  ('3.3.4', '5e21cd5e0bf83b94a606588c4e7a3f3e52d1d152')
            ,  ('3.5.2', '4e3be16ee73e143ab6d8e925d37fd54b9a3bb5a5')
            ,  ('3.6.3', '5e21cd5e0bf83b94a606588c4e7a3f3e52d1d152')
            ))
          )
       ,  ( '3d_plotly', dict
            (( ('5.4.0',  '87cc3e896eb1ab65ec84212bc057a68898e046d6')
            ,  ('5.10.0', '87cc3e896eb1ab65ec84212bc057a68898e046d6')
            ,  ('5.15.0', '87cc3e896eb1ab65ec84212bc057a68898e046d6')
            ))
          )
       ,  ( 'azimuth', dict
            (( ('3.0.2', '81248b39e78fe707f59d732c8556a34e164add4f')
            ,  ('3.3.4', '55f83891c3c297962e24def9d5e5d565eee58a72')
            ,  ('3.5.2', '600221ff9765308069809711a779ea970de301b0')
            ,  ('3.6.3', '55f83891c3c297962e24def9d5e5d565eee58a72')
            ))
          )
       ,  ( 'azimuth_plotly', dict
            (( ('5.4.0',  '0d77bf5fab130b50b52f6e08b294fb44319b002c')
            ,  ('5.10.0', '0d77bf5fab130b50b52f6e08b294fb44319b002c')
            ,  ('5.15.0', [ '0d77bf5fab130b50b52f6e08b294fb44319b002c'
                          , '1575c461d8b743be1cd51d4c69dac1e54f616174'
                          ]
               )
            ))
          )
       ,  ( 'azimuth_db', dict
            (( ('3.0.2', '91e3b791966caf17b1d5189d1ffe49d81fe753db')
            ,  ('3.3.4', '853f2e33d97921a1e29b168af6c72d9102857f0c')
            ,  ('3.5.2', 'e24bb294450bf3e666ab9e5d38fe659fa12bbd89')
            ,  ('3.6.3', '853f2e33d97921a1e29b168af6c72d9102857f0c')
            ))
          )
       ,  ( 'azimuth_db_plotly', dict
            (( ('5.4.0',  '15fc048f952e2f1e1e3068b258617ca1706cb2d3')
            ,  ('5.10.0', '15fc048f952e2f1e1e3068b258617ca1706cb2d3')
            ,  ('5.15.0', [ '15fc048f952e2f1e1e3068b258617ca1706cb2d3'
                          , '2a688bec782165d8c8aafaf581dd00ff73b606fd'
                          ]
               )
            ))
          )
       ,  ( 'azimuth_linear', dict
            (( ('3.0.2', '660561393437790656f2be40f9959f6ee0040e18')
            ,  ('3.3.4', 'b294d474542522e2a598d37b8ce959faa253f164')
            ,  ('3.5.2', '283645c8cd248738afde0c512bbca6ddfe676118')
            ,  ('3.6.3', 'b294d474542522e2a598d37b8ce959faa253f164')
            ))
          )
       ,  ( 'azimuth_linear_plotly', dict
            (( ('5.4.0',  '0f2e4e8873ae0f7f1323f8b7f581f9affd8209aa')
            ,  ('5.10.0', '0f2e4e8873ae0f7f1323f8b7f581f9affd8209aa')
            ,  ('5.15.0', [ '0f2e4e8873ae0f7f1323f8b7f581f9affd8209aa'
                          , 'e8109449a4020c0040d44dbdb32a46235e470df9'
                          ]
               )
            ))
          )
       ,  ( 'azimuth_linear_voltage', dict
            (( ('3.0.2', 'ca0eb9b31d54d453dabc3be5594de15abd13881c')
            ,  ('3.3.4', '8852f490bb274471a1d4453ab0ddfe29a689ae9f')
            ,  ('3.5.2', '957e8bf68dc3155f9a98c3d7061049d797107f6f')
            ,  ('3.6.3', '8852f490bb274471a1d4453ab0ddfe29a689ae9f')
            ))
          )
       ,  ( 'azimuth_linear_voltage_plotly', dict
            (( ('5.4.0',  '06f2207b0eed942368bc5f2f5f88cb418da0b151')
            ,  ('5.10.0', '06f2207b0eed942368bc5f2f5f88cb418da0b151')
            ,  ('5.15.0', [ '06f2207b0eed942368bc5f2f5f88cb418da0b151'
                          , '4e11035ea7f9d46636a5e6192e293bf6eed1b659'
                          ]
               )
            ))
          )
       ,  ( 'basic_output', dict
            (( ('3.0.2', 'b9362d804d86a8be3870c460a162aae974a05955')
            ,  ('3.3.4', '931a908acb08eeebda27e680b12737cdbae95f1e')
            ,  ('3.5.2', '3ce7634a5bcff4d6a9591c68f4604325938bb5ed')
            ,  ('3.6.3', '931a908acb08eeebda27e680b12737cdbae95f1e')
            ))
          )
       ,  ( 'basic_output_plotly', dict
            (( ('5.4.0',  'f28fff3f214477c51c136afaf04b027cc0082bdc')
            ,  ('5.10.0', 'f28fff3f214477c51c136afaf04b027cc0082bdc')
            ,  ('5.15.0', [ 'f28fff3f214477c51c136afaf04b027cc0082bdc'
                          , '8c0364c6d9fbc0209988c8de66234c66b337c9eb'
                          ]
               )
            ))
          )
       ,  ( 'elevation', dict
            (( ('3.0.2', 'fd0b835fde4c976a88fd4c8419fc47ab3788f151')
            ,  ('3.3.4', '12a547c561497050af11bd72a1e55561b00a2f5b')
            ,  ('3.5.2', 'abcbfd16546a9aa4e02781955b3e2253cf01d0aa')
            ,  ('3.6.3', '12a547c561497050af11bd72a1e55561b00a2f5b')
            ))
          )
       ,  ( 'elevation_plotly', dict
            (( ('5.4.0',  '6940e7e0b6c5424c72a9f5253c67482803dbae77')
            ,  ('5.10.0', '6940e7e0b6c5424c72a9f5253c67482803dbae77')
            ,  ('5.15.0', [ '6940e7e0b6c5424c72a9f5253c67482803dbae77'
                          , 'b516fa1c7e20e91c75494c1c88c5ba08e92ed15e'
                          ]
               )
            ))
          )
       ,  ( 'gainfile', dict
            (( ('3.0.2', 'a07f6166e68ee408a4131c866ebbe3f4bc94aa59')
            ,  ('3.3.4', 'e7a5888d1499494818eaf110f30cc7c06e7e3543')
            ,  ('3.5.2', '1ef7b62708590b2bcd6ed5afc23da63f111f9f84')
            ,  ('3.6.3', 'e7a5888d1499494818eaf110f30cc7c06e7e3543')
            ))
          )
       ,  ( 'gainfile_plotly', dict
            (( ('5.4.0',  '3f84d929ef5a3f5b7b7122543502099e31b07d7a')
            ,  ('5.10.0', '3f84d929ef5a3f5b7b7122543502099e31b07d7a')
            ,  ('5.15.0', [ '3f84d929ef5a3f5b7b7122543502099e31b07d7a'
                          , 'ce14166b62f11eba795294a38bbfe0d262a91151'
                          ]
               )
            ))
          )
       ,  ( 'necfile', dict
            (( ('3.0.2', '1d18ad114babc69bf459cabc0a46b7fa16aa8e74')
            ,  ('3.3.4', 'b2e735ae8f7fb2190c5c97fc44ead3299f8e86a4')
            ,  ('3.5.2', '493b0ec0cca1b872c426e6e06634593cbc81bfff')
            ,  ('3.6.3', 'b2e735ae8f7fb2190c5c97fc44ead3299f8e86a4')
            ))
          )
       ,  ( 'necfile_azi_plotly', dict
            (( ('5.4.0',  '045e123ee4209a4fff66a885d10b067614cb7f2e')
            ,  ('5.10.0', '045e123ee4209a4fff66a885d10b067614cb7f2e')
            ,  ('5.15.0', [ '045e123ee4209a4fff66a885d10b067614cb7f2e'
                          , '4bf705d840c97c4f2c48ae8746225a9432b1f1cd'
                          ]
               )
            ))
          )
       ,  ( 'necfile_swr_plotly', dict
            (( ('5.4.0',  '2ef58822b0e45b77adb57ada9e5a5f8072956bb8')
            ,  ('5.10.0', '2ef58822b0e45b77adb57ada9e5a5f8072956bb8')
            ,  ('5.15.0', 'c070cb1d3c91e31b6d2cf19d96328c388e9678f9')
            ))
          )
       ,  ( 'plotall', dict
            (( ('3.0.2', 'cf2d56853c9b9eba5b46188c96b4f990276d9f85')
            ,  ('3.3.4', '5a3267e9be54120d4871d724715e0c7fb1a39a25')
            ,  ('3.5.2', '568a0c3c7a2cc4ceb9c4d9a148420dc71e86dd1a')
            ,  ('3.6.3', '5a3267e9be54120d4871d724715e0c7fb1a39a25')
            ))
          )
       ,  ( 'smith', dict
            (( ('3.0.2', 'dfa7f621afc3037fbdbc9c795e6452672b1dd3c7')
            ,  ('3.5.2', 'ebe551b3aa8ccb2ba20b90e50338efb66af3e24b')
            ,  ('3.6.3', '0c7cfae41d1002c5e75f31df6180f3c8e5d15581')
            ))
          )
       ,  ( 'smith_plotly', dict
            (( ('5.4.0',  '7f74b48395846dc1a3db412bdc62f1d6a36c856f')
            ,  ('5.10.0', '7f74b48395846dc1a3db412bdc62f1d6a36c856f')
            ,  ('5.15.0', '7f74b48395846dc1a3db412bdc62f1d6a36c856f')
            ))
          )
       ,  ( 'vswr', dict
            (( ('3.0.2', '197c45672a1de86c6c6ca9cbfc2c899c28d0690e')
            ,  ('3.3.4', '6495b1f3e7c6c55ba06071dec4b24bc6bc9a3d59')
            ,  ('3.5.2', '71b310cf1c733d3f41272d27bde5a9cce69a8c9b')
            ,  ('3.6.3', '6495b1f3e7c6c55ba06071dec4b24bc6bc9a3d59')
            ))
          )
       ,  ( 'vswr_plotly', dict
            (( ('5.4.0',  'de29597890a6dbfda68a0d5e031c54ab15a7a91f')
            ,  ('5.10.0', 'de29597890a6dbfda68a0d5e031c54ab15a7a91f')
            ,  ('5.15.0', 'f4b7036d8cd27c40a99455d90949365c70801f56')
            ))
          )
       ,  ( 'vswr_extended', dict
            (( ('3.0.2', 'fail')
            ,  ('3.3.4', 'fail')
            ,  ('3.5.2', '1bae165fbff4bce9597c629b89a858a6b207d72f')
            ,  ('3.6.3', 'fd6d0ff1b4be457d7a09f7e9743901c5e0356500')
            ))
          )
       ,  ( 'vswr_extended_plotly', dict
            (( ('5.4.0',  'f4f8cfa5614733800fdb0a8cecc578fb9ed3c6bc')
            ,  ('5.10.0', 'f4f8cfa5614733800fdb0a8cecc578fb9ed3c6bc')
            ,  ('5.15.0', 'e5b52e2efc0e01154583e9dfbda20f891ec31bf0')
            ))
          )
       ))
    ))

def flatten (l):
    if not isinstance (l, list):
        return [l]
    r = []
    for item in l:
        if not isinstance (l, list):
            r.append (item)
        r.extend (flatten (item))
    return r
# end def flatten

def get_picture_hash (function_name):
    """ Get picture hash from picture_hashes via the function name and
        the current matplotlib version.
    """
    assert function_name.startswith ('test_')
    key = function_name [5:]
    if key.endswith ('_plotly'):
        version = plotly.__version__
    else:
        version = matplotlib.__version__
    if version not in picture_hashes [key]:
        versions = list (sorted (picture_hashes [key]))
        idx = bisect_left (versions, version)
        if idx == 0:
            return flatten ([picture_hashes [key][versions [idx]]])
        l = len (versions)
        if idx >= l - 1:
            # Return last *two*, seems sometimes it matches an earlier version
            lst = [picture_hashes [key][i] for i in versions [l - 2:]]
            return flatten (lst)
        lst = [picture_hashes [key][versions [i]] for i in (idx, idx + 1)]
        return flatten (lst)
    return flatten ([picture_hashes [key][version]])
# end def get_picture_hash

def check_status_matplotlib (v):
    hashes = get_picture_hash (v.__name__)
    if 'fail' in hashes:
        return pytest.mark.xfail (v)
    return v
# end def check_status_matplotlib

class Test_Plot (unittest.TestCase):
    debug = False

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
        if self.debug:
            with open ('zoppel', 'wb') as f:
                f.write (io.getvalue ())
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
        args = ["--plot3d", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_3d

    def test_3d_plotly (self):
        infile = "test/12-el-5deg.pout"
        args = ["--plot3d", "-S", infile]
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
        args = ["--vswr", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr

    def test_vswr_plotly (self):
        infile = "test/inverted-v.pout"
        args = ["--vswr", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr_plotly

    @check_status_matplotlib
    def test_vswr_extended (self):
        infile = "test/u29gbuv0.nout"
        args = ["--vswr", "--swr-show-bands", "--swr-show-impedance"
               , "--system-impedance=4050", infile
               ]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr_extended

    def test_vswr_extended_plotly (self):
        infile = "test/u29gbuv0.nout"
        args = ["--vswr", "--swr-show-bands", "--swr-show-impedance"
               , "-S", "--system-impedance=4050", infile
               ]
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
        args = ["--ele", "--angle-azi=60", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_gainfile

    def test_gainfile_plotly (self):
        """ Original basic implementation can save gains to a file
        """
        infile = "test/DP001.GNN"
        args = ["--ele", "-S", "--angle-azi=60", infile]
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
        args = ["--swr", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_necfile_swr_plotly

    @check_status_matplotlib
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

# end class Test_Plot
