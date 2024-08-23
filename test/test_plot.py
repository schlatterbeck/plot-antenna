# Copyright (C) 2022-24 Ralf Schlatterbeck. All rights reserved
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
from plot_antenna.contrib import main_csv_measurement_data
from plot_antenna.eznec import main_eznec
from io import BytesIO
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
# If a version is not in the picture hash we do a binary search and take
# the next and the prior version
#
picture_hashes = dict \
    (( (( ( '3d', dict
            (( ('3.5.2', '4e3be16ee73e143ab6d8e925d37fd54b9a3bb5a5')
            ,  ('3.6.3', '5e21cd5e0bf83b94a606588c4e7a3f3e52d1d152')
            ))
          )
       ,  ( '3d_plotly', dict
            (( ('5.4.0',  '87cc3e896eb1ab65ec84212bc057a68898e046d6')
            ,  ('5.10.0', '87cc3e896eb1ab65ec84212bc057a68898e046d6')
            ,  ('5.15.0', '87cc3e896eb1ab65ec84212bc057a68898e046d6')
            ))
          )
       ,  ( 'asap_3d', dict
            (( ('3.5.2', '1acd523a256c6a8e534150f4099c6def386e2f1e')
            ,  ('3.6.3', '5ce38429edf8a0acec45e2fb08412ad875609120')
            ))
          )
       ,  ( 'asap_azi', dict
            (( ('3.5.2', 'cafe43d1ad73bef2d137e98bc86fda855de60fa6')
            ,  ('3.6.3', '8a10b180a43da1faeb33b0491f8778d5b803fbef')
            ))
          )
       ,  ( 'asap_ele', dict
            (( ('3.5.2', '1acd523a256c6a8e534150f4099c6def386e2f1e')
            ,  ('3.6.3', '5ce38429edf8a0acec45e2fb08412ad875609120')
            ))
          )
       ,  ( 'asap_geo', dict
            (( ('3.5.2', '8274017b943c0f6258bb392a7168ef2b7f061ebe')
            ,  ('3.6.3', '5bc030ddf6607d54cbcf3d169a9973974bc5f1d7')
            ))
          )
       ,  ( 'asap_swr', dict
            (( ('3.5.2', 'd231a47380b4848f9cb87e410660440413990cf5')
            ,  ('3.6.3', '3d4d55c23bfcc3c246cc7f97724ad154b447839f')
            ))
          )
       ,  ( 'asap_3d_plotly', dict
            (( ('5.4.0',  '92bd1d733e2a6c36e9afafa495d9838409e55383')
            ,  ('5.10.0', '92bd1d733e2a6c36e9afafa495d9838409e55383')
            ,  ('5.15.0', '92bd1d733e2a6c36e9afafa495d9838409e55383')
            ))
          )
       ,  ( 'asap_azi_plotly', dict
            (( ('5.4.0',  '2a1cf9d0cf3c5d5ddfab3cf4cf47dd342a00b31e')
            ,  ('5.10.0', '2a1cf9d0cf3c5d5ddfab3cf4cf47dd342a00b31e')
            ,  ('5.15.0', '2a1cf9d0cf3c5d5ddfab3cf4cf47dd342a00b31e')
            ))
          )
       ,  ( 'asap_ele_plotly', dict
            (( ('5.4.0',  'f5de68c359171a3988f24dc69fff3cd39e5f050a')
            ,  ('5.10.0', 'f5de68c359171a3988f24dc69fff3cd39e5f050a')
            ,  ('5.15.0', 'f5de68c359171a3988f24dc69fff3cd39e5f050a')
            ))
          )
       ,  ( 'asap_geo_plotly', dict
            (( ('5.4.0',  'c49fbaafcb7b77a6330d500d68cda8329f9afd03')
            ,  ('5.10.0', 'c49fbaafcb7b77a6330d500d68cda8329f9afd03')
            ,  ('5.15.0', 'c49fbaafcb7b77a6330d500d68cda8329f9afd03')
            ))
          )
       ,  ( 'asap_swr_plotly', dict
            (( ('5.4.0',  'b252845d3224a94cdd9a875b7fcb0dba1ec141d8')
            ,  ('5.10.0', 'b252845d3224a94cdd9a875b7fcb0dba1ec141d8')
            ,  ('5.15.0', 'd84a4d58d2444bb7429a570918c446ddce69c253')
            ))
          )
       ,  ( 'azimuth', dict
            (( ('3.5.2', '600221ff9765308069809711a779ea970de301b0')
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
            (( ('3.5.2', 'e24bb294450bf3e666ab9e5d38fe659fa12bbd89')
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
            (( ('3.5.2', '283645c8cd248738afde0c512bbca6ddfe676118')
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
            (( ('3.5.2', '957e8bf68dc3155f9a98c3d7061049d797107f6f')
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
            (( ('3.5.2', '3ce7634a5bcff4d6a9591c68f4604325938bb5ed')
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
            (( ('3.5.2', 'abcbfd16546a9aa4e02781955b3e2253cf01d0aa')
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
       ,  ( 'eznec_3d', dict
            (( ('3.5.2', '6c903634b1d27f7029e56bf48eac7c7935b1725f')
            ,  ('3.6.3', '4d8a9bfe6a7d2697c3ec6b1aa1690f00f0cf60ad')
            ))
          )
       ,  ( 'eznec_3d_plotly', dict
            (( ('5.4.0',  '8a09e54324ca4016d7f69b2cd7d5d1f277241a08')
            ,  ('5.10.0', '8a09e54324ca4016d7f69b2cd7d5d1f277241a08')
            ,  ('5.15.0', '8a09e54324ca4016d7f69b2cd7d5d1f277241a08')
            ))
          )
       ,  ( 'eznec_azi', dict
            (( ('3.5.2', 'b24a1168399b7db3be11e5890eec88b067ce1796')
            ,  ('3.6.3', '09b70587499c5c43528653275eeb10b3ac9dc7a9')
            ))
          )
       ,  ( 'eznec_azi_plotly', dict
            (( ('5.4.0',  'cb888b791bca39bf191ed7fdae57ed010c0d35da')
            ,  ('5.10.0', 'cb888b791bca39bf191ed7fdae57ed010c0d35da')
            ,  ('5.15.0', 'cb888b791bca39bf191ed7fdae57ed010c0d35da')
            ))
          )
       ,  ( 'eznec_ele', dict
            (( ('3.5.2', '6c903634b1d27f7029e56bf48eac7c7935b1725f')
            ,  ('3.6.3', '4d8a9bfe6a7d2697c3ec6b1aa1690f00f0cf60ad')
            ))
          )
       ,  ( 'eznec_ele_plotly', dict
            (( ('5.4.0',  'ac7733a8dd42593def54f7b2d2689215e969e9d9')
            ,  ('5.10.0', 'ac7733a8dd42593def54f7b2d2689215e969e9d9')
            ,  ('5.15.0', 'ac7733a8dd42593def54f7b2d2689215e969e9d9')
            ))
          )
       ,  ( 'gainfile', dict
            (( ('3.5.2', '7eb9eda74a98a3086be5077fbe8999b3601f7582')
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
            (( ('3.5.2', '2e2c52a558339b4aa4bf2f67394a09edbc0abc50')
            ,  ('3.6.3', '7c085ddc21d488930b4287f01db31b431800dc9f')
            ))
          )
       ,  ( 'geo_bug_plotly', dict
            (( ('5.4.0',  '64287b7648b82a5525c6aa3e3501a927bc66ddc8')
            ,  ('5.10.0', '64287b7648b82a5525c6aa3e3501a927bc66ddc8')
            ,  ('5.15.0', '64287b7648b82a5525c6aa3e3501a927bc66ddc8')
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
       ,  ( 'measurement', dict
            (( ('3.5.2', '65fead7d01e63d34c62d09daccd47147c859a7f5')
            ,  ('3.6.3', 'fb5c176c854f739adac27a4e070963b8b3ae371b')
            ))
          )
       ,  ( 'measurement_plotly', dict
            (( ('5.4.0',  'e8a382b7b7fc40b103cf67d3f058ba8eec1a19ae')
            ,  ('5.10.0', 'e8a382b7b7fc40b103cf67d3f058ba8eec1a19ae')
            ,  ('5.15.0', [ 'e8a382b7b7fc40b103cf67d3f058ba8eec1a19ae'
                          , '3df9716996f3f65960c5182eede8f601834d6b66'
                          ]
               )
            ))
          )
       ,  ( 'measurement_full', dict
            (( ('3.5.2', '723ac9f815723bbcd1cfbc06ab1871f29026ca92')
            ,  ('3.6.3', '8afa5c3e5c3dcdc7448d8162b70cba8c99b868c4')
            ))
          )
       ,  ( 'measurement_full_plotly', dict
            (( ('5.4.0',  'c869f79a74b778199ec5319a9ce34509d6d8b9b8')
            ,  ('5.10.0', 'c869f79a74b778199ec5319a9ce34509d6d8b9b8')
            ,  ('5.15.0', [ 'c869f79a74b778199ec5319a9ce34509d6d8b9b8'
                          , '06bd7bf093d206f20888df7425725405fc557098'
                          ]
               )
            ))
          )
       ,  ( 'mininec_3_ele', dict
            (( ('3.5.2', '8b233f643d5d7df61888d615be2b3911753ed61c')
            ,  ('3.6.3', '7dcaa697b1df4ba81ac3e17910e712f5e79072d2')
            ))
          )
       ,  ( 'mininec_3_geo', dict
            (( ('3.5.2', '6064f56e7b6b7eb2be3fb60262e90e28c9bb2f90')
            ,  ('3.6.3', 'eceaff14bd647727b616eb65c28cfff07b6f0dec')
            ))
          )
       ,  ( 'mininec_3_ele_plotly', dict
            (( ('5.4.0',  'a8402e6c835babeee44045804ca3b52922db28b1')
            ,  ('5.10.0', 'a8402e6c835babeee44045804ca3b52922db28b1')
            ,  ('5.15.0', 'a8402e6c835babeee44045804ca3b52922db28b1')
            ))
          )
       ,  ( 'mininec_3_geo_plotly', dict
            (( ('5.4.0',  '97897b4d1ae3d848ec327a6e34bb27357a67ed51')
            ,  ('5.10.0', '97897b4d1ae3d848ec327a6e34bb27357a67ed51')
            ,  ('5.15.0', '97897b4d1ae3d848ec327a6e34bb27357a67ed51')
            ))
          )
       ,  ( 'monopole', dict
            (( ('3.5.2', 'faf003cb6a8c659b94a9c074428d7daa8bdd6f7f')
            ,  ('3.6.3', 'e263df49ec466597eccf32337923f3a7dbd9337b')
            ))
          )
       ,  ( 'monopole_plotly', dict
            (( ('5.4.0',  '6744ee0e3c4a7f53db772dba633c71e4c91a298b')
             ,
            ))
          )
       ,  ( 'necfile', dict
            (( ('3.5.2', '7e55528275f1d39992dafa84bf7d17ffb231c292')
            ,  ('3.6.3', '52b2031fc239871a0d38edcdb3028bb0bdc2fc2c')
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
            (( ('3.5.2', '6c9bdebd77a6e045a01a7b52424c3b69b6c08b44')
            ,  ('3.6.3', '0344e593e0878f76d99a5dd9ec3c45f44757654a')
            ))
          )
       ,  ( 'old_mininec_ele', dict
            (( ('3.5.2', 'bc4f6891a6554f796726721c82bfac6a618d2918')
            ,  ('3.6.3', '6e2008b990de7d338a5682fc7f016150eca6d4e1')
            ))
          )
       ,  ( 'old_mininec_geo', dict
            (( ('3.5.2', '78fc22b82c1744964928a498599e1a2e590c009e')
            ,  ('3.6.3', 'dc197cd8784b412bd1b52b5dcf5efed800a7aa13')
            ))
          )
       ,  ( 'old_mininec_ele_plotly', dict
            (( ('5.4.0',  'c0493d0054674c4722df9a77a14072e9cc8f3b3d')
            ,  ('5.10.0', 'c0493d0054674c4722df9a77a14072e9cc8f3b3d')
            ,  ('5.15.0', 'c0493d0054674c4722df9a77a14072e9cc8f3b3d')
            ))
          )
       ,  ( 'old_mininec_geo_plotly', dict
            (( ('5.4.0',  'd530dc770807d6f3bf15492a0e5659e896eff91d')
            ,  ('5.10.0', 'd530dc770807d6f3bf15492a0e5659e896eff91d')
            ,  ('5.15.0', 'd530dc770807d6f3bf15492a0e5659e896eff91d')
            ))
          )
       ,  ( 'smith', dict
            (( ('3.5.2', 'ebe551b3aa8ccb2ba20b90e50338efb66af3e24b')
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
       ,  ( 'swr_band_range', dict
            (( ('3.5.2', 'c2ead006f88ba0b80e3d6db0cedb76722c784d41')
            ,  ('3.6.3', '3015bb1ec5feb0c7ea5667c73e707b0bbcf4fdea')
            ))
          )
       ,  ( 'swr_tickmarks', dict
            (( ('3.5.2', '3c8026d526cb759571fdfbcbc2f548b9b94c6f48')
            ,  ('3.6.3', '9c368599c81b9231bbb41af40bb6b2b874fbafa1')
            ))
          )
       ,  ( 'swr_tickmarks_plotly', dict
            (( ('5.4.0',  'c787ce20e2876f9477863c089c18e5e56a810a17')
            ,  ('5.10.0', 'c787ce20e2876f9477863c089c18e5e56a810a17')
            ,  ('5.15.0', '254c6d573d7c3551f9a5ddcac7b91b0b6f696c3e')
            ))
          )
       ,  ( 'vswr', dict
            (( ('3.5.2', '544bed7b90f16fa725bc998658de751e3b4bbc84')
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
            (( ('3.5.2', '8f2dffe04393666fb71bc29837f9d2e7c554b9b9')
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

def check_smith_available (v):
    if SmithAxes is None:
        return pytest.mark.xfail (v)
    return check_status_matplotlib (v)
# end def check_smith_available

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
        args = ["--title=", "--vswr", "--swr-show-bands", "--swr-show-impedance"
               , "--system-impedance=4050", infile
               ]
        main (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_vswr_extended

    def test_vswr_extended_plotly (self):
        infile = "test/u29gbuv0.nout"
        args = ["--title=", "--vswr", "--swr-show-bands", "--swr-show-impedance"
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

    def test_measurement (self):
        infile = "test/Messdaten.csv"
        args = ["--azi", "--polari=H", infile]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement

    def test_measurement_plotly (self):
        infile = "test/Messdaten.csv"
        args = ["--azi", "--polari=H", "-S", infile]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement_plotly

    def test_measurement_full (self):
        infile = "test/Messdaten.csv"
        args = [ "--ele", "--polari=H", "--polari=V", "--polari=sum"
               , "--matp", "--angle-ele=10.3", "--interpol=2", infile
               ]
        main_csv_measurement_data (args, pic_io = self.pic_io)
        self.compare_cs ()
    # end def test_measurement_full

    def test_measurement_full_plotly (self):
        infile = "test/Messdaten.csv"
        args = [ "--ele", "--polari=H", "--polari=V", "--polari=sum"
               , "--matp", "--angle-ele=10.3", "--interpol=2", "-S", infile
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
        args = '-S --vswr --swr-show-impedance'.split ()
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
        args = ['-S', '--swr', '--swr-show-impedance', infile]
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

# end class Test_Plot
