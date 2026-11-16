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


class GuidelineKinds(unittest.TestCase):
    def test_the_assessment_tells_a_guidelines_files_as_louie_does(self):
        # bagheera's copy of louie's file kinds (ADR plugin), so the Assessment counts a Guideline
        # before the first edit of the files louie's Hook gives it for.
        from bagheera import assess
        from louie import guidelines

        paths = [
            "a.ts", "a.tsx", "a.mts", "a.cts", "a.vue", "a.js", "a.go", "a.md", "SKILL.md",
            "x/CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude/agents/a.md",
            ".claude/commands/a.md", "x/.claude/skills/a/b.md", ".claude/hooks/a.md",
            ".claude/agents/a.json", "skills/a.md",
        ]
        for name, louie in guidelines.BY_PATH.items():
            for path in paths:
                with self.subTest(guideline=name, path=path):
                    self.assertEqual(assess._BY_KIND[name](path), louie(path))


if __name__ == "__main__":
    unittest.main()
