import os
from typing import Dict

from tests import testkit


def stage(dir: str, files: Dict[str, str]) -> None:
    """Writes each file of `files`, by its path from the repo `dir`, and stages it."""
    for path, text in files.items():
        full = os.path.join(dir, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", newline="") as f:
            f.write(text)
        testkit.git(dir, "add", path)
