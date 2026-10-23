"""PASE - Python Agrivoltaic Simulation Environment."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Distribution name (pip), not the import name: the package imports as
    # `pase` but is distributed as `pase-agrivoltaics`.
    __version__ = version("pase-agrivoltaics")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"
