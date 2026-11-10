"""Tests of bagheera's code (PRD bagheera), beside bagheera's in tests/; each imports only its own
plugin's package."""

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins", "bagheera", "scripts"
    ),
)
