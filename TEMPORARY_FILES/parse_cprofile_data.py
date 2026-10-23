import os
import pstats
from pstats import SortKey

from MODULES.ENVIRONMENT.sky_model import ReinhartSky

# Profiles of sky_model Reinhart module
MF = 8
MFs = [16, 32]
for MF in MFs:
    profile_output = os.path.join('..', 'OUTPUTS', 'profiling', f'cprofile_output_sky_model_MF{MF}.prof')
    p = pstats.Stats(profile_output)
    p.strip_dirs().sort_stats('tottime').print_stats(10)

# Profile of example.py
profile_output = os.path.join('..', 'OUTPUTS', 'profiling', f'example.prof')
p = pstats.Stats(profile_output)
p.strip_dirs().sort_stats('tottime').print_stats(100)
