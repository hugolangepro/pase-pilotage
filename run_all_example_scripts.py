#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
Author : Arnaud Bouvry (<abouvry@uliege.be>)
This file is part of the PASE software, and is distributed under the MIT license.

Run all example scripts to make sure they all run smooth.

Source: https://tutorialreference.com/python/examples/faq/python-how-to-run-multiple
-python-files-concurrently-or-sequentially
"""

import subprocess
import sys

python_executable = sys.executable
scripts = ['example.py',
           'example_albedo.py',
           'example_diffusers.py',
           'example_HSATS.py',
           'example_mesh.py',
           'example_multiblock.py',
           'example_NoPanels.py',
           'example_profiling.py',
           'example_PVTable.py']#,
           # 'example_tracking.py']

print("Running processes sequentially...")
for script in scripts:
    print(f"--- Running {script} ---")
    # run() executes the command and WAITS for it to complete
    result = subprocess.run([python_executable, script], capture_output=True,
                            text=True, check=False)
    print(f"--- Finished {script} ---")
    print(f"  Return Code: {result.returncode}")
    print(f"  Stdout:{result.stdout}")
    if result.stderr:
         print(f"  Stderr:{result.stderr}")

    # Optional: Stop if a script fails (non-zero return code)
    if result.returncode != 0:
        print(f"Error: {script} failed with code {result.returncode}. Stopping.")
        sys.exit(1)

print("All sequential processes finished.")
print("Don't forget to manually run example_tracking.py (because it needs user input, it is excluded from the automated"
      " script.")
