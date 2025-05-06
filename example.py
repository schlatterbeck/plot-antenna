#!/usr/bin/python3

# Simple example of using the API to plot a simple pattern
# See README.rst section API

import numpy as np
from plot_antenna import plot_antenna

# Initialize command options with general options
cmd = plot_antenna.options_general ()
# Add gain options
plot_antenna.options_gain (cmd)
# Parse empty arguments resulting in default args
args = plot_antenna.process_args (cmd, [])
# The filename is needed internally for computing default title
args.filename = ''
# Title
args.title = 'My Title'
# We want an azimuth plot
args.azimuth = True
# We might want to ship result to running browser with plotly
# args.show_in_browser = True

frequency = 430.0
polarization = 'sum'
key = (frequency, polarization)
gdict = {key: plot_antenna.Gain_Data ([frequency])}
data = gdict [key].pattern
for azi in np.arange (0, 361, 10):
    data [(90.0, azi)] = 0.0
gp = plot_antenna.Gain_Plot (args, gdict)
gp.compute ()
gp.plot ()
