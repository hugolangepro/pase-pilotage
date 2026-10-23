"""Resolution of data files shipped with the pase package."""

from pathlib import Path


def static_data_path(name: str) -> Path:
    """Return the path of a static data file shipped in ``pase/DATA``.

    Static data files (model lookup tables) move with the installed
    package, unlike user inputs which are resolved from the current
    working directory.
    """
    return Path(__file__).parent / 'DATA' / name
