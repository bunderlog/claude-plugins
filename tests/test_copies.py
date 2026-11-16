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


class KnowledgeNames(unittest.TestCase):
    def test_louie_names_an_adr_at_the_files_the_assessment_counts(self):
        # louie's copy of the Assessment's rule for which file an ADR or a PRD names (ADR plugin),
        # so its Hook names one where the Assessment counts an edit (PRD index); the ADRs and files
        # of the Assessment's own tests.
        from bagheera import assess
        from louie import knowledge

        texts = [
            "# Orders\n\nOrders live in `src/orders/` and `src/orders/place.go`.\n",
            "# Docs\n\nPRDs live in `.about/prd/`, the code in `src/orders/`.\n",
        ]
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(knowledge.PATH.findall(text), assess._PATH.findall(text))
        files = [
            "src/orders/place.go", "src/orders/cancel.go", "README.md",
            ".claude/worktrees/pr-1/.about/prd/export.md",
            ".claude/worktrees/pr-1/src/orders/place.go",
        ]
        for path in ["src/orders", "src/orders/place.go", ".about/prd"]:
            for rel in files:
                with self.subTest(path=path, rel=rel):
                    self.assertEqual(knowledge.names(path, rel), assess._names(path, rel))


if __name__ == "__main__":
    unittest.main()
