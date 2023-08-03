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
            (( ('3.0.2', '137e9550138ae29517a656785916e9e53659c535')
            ,  ('3.3.4', 'f9234e4868fbd0104cdb10c8cad7e5a490f33dcc')
            ,  ('3.5.2', '7eb9eda74a98a3086be5077fbe8999b3601f7582')
            ,  ('3.6.3', 'f9234e4868fbd0104cdb10c8cad7e5a490f33dcc')
            ))
          )
       ,  ( 'gainfile_plotly', dict
            (( ('5.4.0',  '1b208de1caf499c08414ae7787fa93002159b898')
            ,  ('5.10.0', '1b208de1caf499c08414ae7787fa93002159b898')
            ,  ('5.15.0', [ '7e4f7e2fa1fb5f9603c3e7f3730ca4d20b94c7cb'
                          , '1b208de1caf499c08414ae7787fa93002159b898'
                          ]
               )
            ))
          )
       ,  ( 'geo', dict
            (( ('3.0.2', '22baea55587016bb29bdcd3b56a1dc8a87100f3d')
            ,  ('3.3.4', '5a21d4501625eeccd70bdda13e9d197a6c00a82b')
            ,  ('3.5.2', '2e2c52a558339b4aa4bf2f67394a09edbc0abc50')
            ,  ('3.6.3', '7c085ddc21d488930b4287f01db31b431800dc9f')
            ))
          )
       ,  ( 'geo_plotly', dict
            (( ('5.4.0',  '802fd1bfc29d50468c33096bee4b5458c30f1d0c')
            ,  ('5.10.0', '802fd1bfc29d50468c33096bee4b5458c30f1d0c')
            ,  ('5.15.0', [ '802fd1bfc29d50468c33096bee4b5458c30f1d0c'
                          , '3065cb6d938fa3ce7d015c45c23887f5c4ce5a91'
                          ]
               )
            ))
          )
       ,  ( 'necfile', dict
            (( ('3.0.2', 'c6f672d460e81f5f14cf69d0d9d793b41ac8a7f3')
            ,  ('3.3.4', '36e0de54ff41c41f88530572fdcf712c77596cda')
            ,  ('3.5.2', '68fcdc634ae889d9edea1fdcbff196e16ccd8ca9')
            ,  ('3.6.3', '36e0de54ff41c41f88530572fdcf712c77596cda')
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
            (( ('5.4.0',  'f0f7f70e23cd49717fefde84fc4edacaa9765f31')
            ,  ('5.10.0', 'f0f7f70e23cd49717fefde84fc4edacaa9765f31')
            ,  ('5.15.0', 'a5bc67eb15c221d173b7c71487927cb6d177c7f0')
            ))
          )
       ,  ( 'plotall', dict
            (( ('3.0.2', '5a0418e4b0a5c6c09a0765b102edb6ea7b49082b')
            ,  ('3.3.4', '894b813078420b04011dcc5f273385b00dc68d46')
            ,  ('3.5.2', '1c858d93cb69d95e3fe608148016f084bbc046fd')
            ,  ('3.6.3', '894b813078420b04011dcc5f273385b00dc68d46')
            ))
          )
       ,  ( 'smith', dict
            (( ('3.0.2', 'dfa7f621afc3037fbdbc9c795e6452672b1dd3c7')
            ,  ('3.5.2', 'ebe551b3aa8ccb2ba20b90e50338efb66af3e24b')
            ,  ('3.6.3', '0c7cfae41d1002c5e75f31df6180f3c8e5d15581')
            ))
          )
       ,  ( 'smith_plotly', dict
            (( ('5.4.0',  '92118fc5f98e118ff29cab3ed947c701eed92a6d')
            ,  ('5.9.0',  '82e6bf2da6b8031af7cb19f38d5417bc39997b25')
            ,  ('5.10.0', '92118fc5f98e118ff29cab3ed947c701eed92a6d')
            ,  ('5.15.0', [ '92118fc5f98e118ff29cab3ed947c701eed92a6d'
                          , '82e6bf2da6b8031af7cb19f38d5417bc39997b25'
                          ]
               )
            ))
          )
       ,  ( 'vswr', dict
            (( ('3.0.2', '4bdae4121b47e9787bcf15136f22cc9aaf418a04')
            ,  ('3.3.4', '2b01bbdd71c162ace5c5ef0683a8ef8c1703ee2c')
            ,  ('3.5.2', '544bed7b90f16fa725bc998658de751e3b4bbc84')
            ,  ('3.6.3', '2b01bbdd71c162ace5c5ef0683a8ef8c1703ee2c')
            ))
          )
       ,  ( 'vswr_plotly', dict
            (( ('5.4.0',  '112b70a58dccd9cefa13f33bf0e6b0184da16c35')
            ,  ('5.10.0', '112b70a58dccd9cefa13f33bf0e6b0184da16c35')
            ,  ('5.15.0', '0c7fad833b107b4a83b3530473e570b601af2381')
            ))
          )
       ,  ( 'vswr_extended', dict
            (( ('3.0.2', '3ea33e12ae46ca889c0b68f80046e7dbba89d0fa')
            ,  ('3.3.4', 'abccaab32ed29b4bc91a991a3affd2a59ee312e4')
            ,  ('3.5.2', '8f2dffe04393666fb71bc29837f9d2e7c554b9b9')
            ,  ('3.6.3', 'abccaab32ed29b4bc91a991a3affd2a59ee312e4')
            ))
          )
       ,  ( 'vswr_extended_plotly', dict
            (( ('5.4.0',  'acdd60ed0d960f329f4699fc49db5655cd7e8d47')
            ,  ('5.10.0', 'acdd60ed0d960f329f4699fc49db5655cd7e8d47')
            ,  ('5.15.0', '460d57001482e2d35b477582544630c4a7272757')
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
            with open (calling_fun + '.ppm', 'wb') as f:
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

    def test_geo (self):
        infile = "test/inve802B.pout"
        args = ["--geo", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo

    def test_geo_plotly (self):
        infile = "test/inve802B.pout"
        args = ["--geo", "-S", infile]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_geo

# end class Test_Plot
