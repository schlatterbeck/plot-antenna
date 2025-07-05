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
# We might want to ship result to running browser with plotly
# args.show_in_browser = True
# If we want to do a 3d-plot we set args.plot3d, we could also set
# args.azimuth to get an azimuth plot. Both variables can be set and we
# get both plots (one after the other with matplotlib, both in different
# browser windows with plotly)
args.azimuth = False
args.plot3d  = True

frequency = 430.0
polarization = 'sum'
key = (frequency, polarization)
# First variant: Use dictionary
gdict = {key: plot_antenna.Gain_Data (key)}
data = gdict [key].pattern
for theta in np.arange (0, 181, 10):
    for phi in np.arange (0, 361, 10):
        data [(theta, phi)] = 0.0
gp = plot_antenna.Gain_Plot (args, gdict)
gp.compute ()
gp.plot ()
# Second variant: Use a two-dimensional gains array and theta and phi
# angles in degrees, the shape of the gains array must match the lengths
# of the thetas and phis arrays.
thetas = np.arange (0, 181, 10)
phis   = np.arange (0, 361, 10)
gains  = np.zeros ((19, 37))
gdict  = {key: plot_antenna.Gain_Data.from_gains (key, gains, thetas, phis)}
gp = plot_antenna.Gain_Plot (args, gdict)
gp.compute ()
gp.plot ()
