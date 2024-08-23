#!/usr/bin/env python3
# Copyright (C) 2022-24 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
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
import sys
from setuptools import setup

if os.path.exists ("VERSION"):
    with open ("VERSION", 'r', encoding="utf8") as f:
        __version__ = f.read ().strip ()
else:
    __version__ = '0+unknown'

with open ('README.rst') as f:
    description = f.read ()

license     = 'MIT License'
rq          = '>=3.7'
setup \
    ( name             = "plot-antenna"
    , version          = __version__
    , description      =
        "Antenna plotting program for plotting antenna simulation results"
    , long_description = ''.join (description)
    , long_description_content_type='text/x-rst'
    , license          = license
    , author           = "Ralf Schlatterbeck"
    , author_email     = "rsc@runtux.com"
    , install_requires = \
        [ 'matplotlib', 'numpy', 'pandas', 'plotly' ]
    , packages         = ['plot_antenna']
    , platforms        = 'Any'
    , url              = "https://github.com/schlatterbeck/plot-antenna"
    , python_requires  = rq
    , entry_points     = dict
        ( console_scripts =
            [ 'plot-antenna=plot_antenna.plot_antenna:main'
            , 'plot-measurements-from-file=plot_antenna.contrib'
              ':main_csv_measurement_data'
            , 'plot-eznec=plot_antenna.eznec:main_eznec'
            ]
        )
    , classifiers      = \
        [ 'Development Status :: 4 - Beta'
        , 'License :: OSI Approved :: ' + license
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Intended Audience :: Science/Research'
        , 'Intended Audience :: Other Audience'
        ]
    )
