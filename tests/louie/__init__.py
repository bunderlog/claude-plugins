"""Tests of louie's code (PRD louie), beside bagheera's in tests/bagheera/; each imports only its
own plugin's package."""

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins", "louie", "scripts"
    ),
)
