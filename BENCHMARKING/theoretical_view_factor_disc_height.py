import numpy as np
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
import pandas as pd

def compute_analytical_f(disc_radius, heights):
    theta_0 = np.arctan(disc_radius / heights)
    analytical_f = 1 - (np.sin(theta_0)) ** 2

    return analytical_f

# Build the same dataframe as in SYMBIOSYST report
step1 = 0.1
heights = np.arange(0.1, 1, step=step1)

step2 = 0.25
heights = np.concatenate([heights, np.arange(1, 2, step=step2)])

step3 = 1
heights = np.concatenate([heights, np.arange(2, 6, step=step3)])

disc_radius = np.sqrt(1/np.pi)
analytical_f = compute_analytical_f(disc_radius, heights)

df = pd.DataFrame([heights, analytical_f]).T

# Draw a plot
step=0.01
heights = np.arange(step, 10, step=step)
analytical_f = compute_analytical_f(disc_radius, heights)

plt.figure()

plt.plot(heights, analytical_f, 'k-')

plt.xlabel('Disc height [m]')
plt.ylabel('View factor [-]')

plt.show()
