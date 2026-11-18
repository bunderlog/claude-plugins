import os
import re
import unittest

# louie's Workflows, the scripts Claude Code runs (PRD implement).
WORKFLOWS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
    "plugins", "louie", "workflows",
)


class Workflows(unittest.TestCase):
    # Each Workflow's meta is the script's first statement, a plain literal with its name,
    # description and the phases its phase() calls and its agents' phase use, and no script calls what Claude Code makes
    # throw or refuses (PRD implement).
    def test_meta_and_body(self):
        names = sorted(f for f in os.listdir(WORKFLOWS) if f.endswith(".js"))
        self.assertIn("verify.js", names)
        for name in names:
            with self.subTest(name=name):
                with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
                    text = f.read()
                meta = re.match(r"export const meta = \{\n(.*?)\n\}\n", text, re.S)
                self.assertIsNotNone(meta, "meta isn't the first statement")
                body = meta.group(1)
                self.assertIn(f"  name: '{name[:-3]}',", body)
                self.assertRegex(body, r"\n  description: '")
                # A plain literal: no variable, call or spread, which drops the command.
                self.assertNotRegex(re.sub(r"'(?:[^'\\]|\\.)*'", "''", body), r"\.\.\.|\w\(|\$\{")
                listed = re.findall(r"\{ title: '([^']+)' \}", body)
                called = set(re.findall(r"\bphase(?:\(|: )'([^']+)'", text[meta.end():]))
                # A nested Workflow's agents show in a group of its own, `▸ <name>`, which a
                # title of that name in meta places among the phases.
                nested = {f"▸ {n}" for n in re.findall(r"\bworkflow\('([^']+)'", text[meta.end():])}
                self.assertEqual(set(listed) - nested, called)
                for banned in ("Date.now(", "Math.random(", "import(", "new Date()"):
                    self.assertNotIn(banned, text)


    # implement's progress lists its stages in the order they run, the plan's and the
    # Verification's own groups among them, and no phase that holds no agent.
    def test_implement_lists_its_stages_in_order(self):
        with open(os.path.join(WORKFLOWS, "implement.js"), encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(
            re.findall(r"\{ title: '([^']+)' \}", text),
            ["Prepare", "▸ louie:plan", "Implement", "▸ louie:verify", "Pull request"],
        )


if __name__ == "__main__":
    unittest.main()
