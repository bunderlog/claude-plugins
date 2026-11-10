"""Each plugin of the marketplace works with the others gone (PRD harness): its folder alone,
copied out of this repo, runs every Hook it declares on a harmless call and lets it through."""

import json
import os
import re
import shutil
import subprocess
import unittest

from tests import testkit

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# A harmless input for each event a plugin's Hooks take.
CALLS = {
    "SessionStart": {"hook_event_name": "SessionStart", "source": "startup"},
    "SessionEnd": {"hook_event_name": "SessionEnd", "reason": "other"},
    "UserPromptSubmit": {"hook_event_name": "UserPromptSubmit", "prompt": "hello"},
    "PreToolUse": {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                   "tool_input": {"command": "ls"}},
    "PostToolUse": {"hook_event_name": "PostToolUse", "tool_name": "Read",
                    "tool_input": {"file_path": "README.md"}, "tool_response": {}},
    "PostToolUseFailure": {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                           "tool_input": {"command": "false"}, "error": "exit 1"},
    "SubagentStart": {"hook_event_name": "SubagentStart", "agent_type": "louie:verifier"},
    "Stop": {"hook_event_name": "Stop", "stop_hook_active": False},
    "Notification": {"hook_event_name": "Notification", "message": "Claude needs your permission",
                     "notification_type": "permission_prompt"},
}


class Alone(unittest.TestCase):
    def test_each_plugin_alone(self):
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
            plugins = [p["name"] for p in json.load(f)["plugins"]]
        self.assertEqual(sorted(plugins), ["bagheera", "baloo", "louie"])
        for name in plugins:
            with self.subTest(plugin=name):
                self.check(name)

    def check(self, name):
        repo = testkit.repo(self)
        testkit.git(repo, "commit", "-q", "--allow-empty", "-m", "chore: start")
        with open(os.path.join(repo, "README.md"), "w") as f:
            f.write("# x\n")
        root = os.path.join(testkit.tempdir(self), name)
        shutil.copytree(os.path.join(ROOT, "plugins", name), root,
                        ignore=shutil.ignore_patterns("__pycache__"))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("CLAUDE_", "BALOO_"))}
        env.update(CLAUDE_PROJECT_DIR=repo, CLAUDE_PLUGIN_ROOT=root,
                   CLAUDE_PLUGIN_DATA=testkit.tempdir(self), CLAUDE_CONFIG_DIR=testkit.tempdir(self))
        with open(os.path.join(root, "hooks", "hooks.json"), encoding="utf-8") as f:
            hooks = json.load(f)["hooks"]
        for event, groups in hooks.items():
            call = dict(CALLS[event], session_id="s1", cwd=repo, transcript_path="")
            for group in groups:
                for h in group["hooks"]:
                    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", root) for a in h.get("args", [])]
                    p = subprocess.run([h["command"], *args], input=json.dumps(call), cwd=repo,
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, timeout=60)
                    what = f"{name} {event} {' '.join(args[1:])}"
                    self.assertEqual(p.returncode, 0, f"{what}: {p.stderr}")
                    self.assertNotIn('"deny"', p.stdout, what)
                    self.assertNotIn('"block"', p.stdout, what)
        self.check_skills(name, root)
        if name == "louie":
            dest = os.path.join(testkit.tempdir(self), "demo")
            p = subprocess.run(["python3", "-E", "-s", os.path.join(root, "scripts", "run.py"),
                                "new", dest, "demo", "owner"], env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, f"louie new: {p.stderr}")
            self.assertTrue(os.path.isfile(os.path.join(dest, "CLAUDE.md")), p.stdout)

    def check_skills(self, name, root):
        """Each skill of the plugin copied to `root` has its name and a description, and every
        file of the plugin it runs is in the copy."""
        skills = os.path.join(root, "skills")
        for skill in sorted(os.listdir(skills)) if os.path.isdir(skills) else []:
            with open(os.path.join(skills, skill, "SKILL.md"), encoding="utf-8") as f:
                text = f.read()
            what = f"{name} skill {skill}"
            match = re.match(r"---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(match, f"{what}: no frontmatter")
            fields = dict(line.split(": ", 1) for line in match.group(1).splitlines()
                          if ": " in line and not line.startswith(" "))
            self.assertEqual(fields.get("name"), skill, what)
            self.assertTrue(fields.get("description"), what)
            for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^'\"\s`]+)", text):
                self.assertTrue(os.path.exists(os.path.join(root, rel)), f"{what}: {rel}")


if __name__ == "__main__":
    unittest.main()
