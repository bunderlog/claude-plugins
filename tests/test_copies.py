"""The helpers copied into bagheera and louie (ADR plugin), which share no code: each copy is the
other with the plugin's name changed, so a fix to one reaches both."""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The modules each plugin's package holds the same copy of.
COPIED = ["checks/shell.py", "once.py", "repo.py", "version.py"]


def _read(plugin: str, module: str) -> str:
    path = os.path.join(ROOT, "plugins", plugin, "scripts", plugin, module)
    with open(path, encoding="utf-8") as f:
        return f.read().replace(plugin, "<plugin>")


class Copies(unittest.TestCase):
    def test_copies_match(self):
        for module in COPIED:
            with self.subTest(module=module):
                self.assertEqual(_read("bagheera", module), _read("louie", module))


if __name__ == "__main__":
    unittest.main()
