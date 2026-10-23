#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Comparison script — load saved simulations and plot comparison graphs.
#
# Workflow
# --------
# 1. Run example_tracking_hugo.py (or any simulation script) for each scenario.
#    Each script must call save_simulation() at the end to persist its results.
# 2. Run THIS file to load all saved results and produce the comparison plots.
#
# No simulation is re-run here — only results already on disk are used.

from pase.DATA_MANAGEMENT.simulation_results import load_all_simulations
from pase.DATA_MANAGEMENT.plots.plot_comparison_graphs import (
    plot_comparison_overlay,
    plot_comparison_grid,
    plot_comparison_bars,
    plot_comparison_combined,
)

# ── Load all saved simulations ────────────────────────────────────────────────
# Each .pkl in OUTPUTS/simulations/ is one scenario.
# They are loaded in alphabetical order — rename files to control sort order.

simulations = load_all_simulations('OUTPUTS/simulations/SIMU_pilotage_1')

# ── Crop variable to compare ──────────────────────────────────────────────────
# Options : 'Biomass', 'Fresh_yield', 'Dry_yield', 'LAI', 'Height'

VARIABLE = 'Biomass'
UNIT     = 'g/m²'

# ── Plots ─────────────────────────────────────────────────────────────────────

# Option 1 — Curves superimposed
plot_comparison_overlay(simulations, variable=VARIABLE, unit=UNIT,
                        save_path='OUTPUTS/GRAPHS/COMPARISON_TEST_2/comparison_overlay.png')

# Option 2 — Grid (one column per simulation)
plot_comparison_grid(simulations, variable=VARIABLE, unit=UNIT,
                     save_path='OUTPUTS/GRAPHS/COMPARISON_TEST_2/comparison_grid.png')

# Option 3 — Bar chart of annual totals
plot_comparison_bars(simulations, variable=VARIABLE, unit=UNIT,
                     save_path='OUTPUTS/GRAPHS/COMPARISON_TEST_2/comparison_bars.png')

# Option 1 + 3 combined
plot_comparison_combined(simulations, variable=VARIABLE, unit=UNIT,
                         save_path='OUTPUTS/GRAPHS/COMPARISON_TEST_2/comparison_combined.png')
