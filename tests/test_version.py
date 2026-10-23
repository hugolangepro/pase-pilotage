"""The package exposes an importable, non-empty version string.

Fast and offline: it only imports ``pase`` and checks ``__version__``, so it
runs in every pipeline without touching the network.
"""

import pase


def test_version_is_a_nonempty_string():
    assert isinstance(pase.__version__, str)
    assert pase.__version__
