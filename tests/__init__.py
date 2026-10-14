"""Tests of the plugin's code, kept outside the plugin so a Release doesn't ship them. Run from the
repo's root: python3 -m unittest discover -s tests -t ."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "baloo", "scripts")
)
