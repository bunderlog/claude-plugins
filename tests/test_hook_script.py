import os
import shutil
import subprocess
import tempfile
import unittest

HOOK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins", "baloo", "scripts", "hook",
)  # fmt: skip


class HookScript(unittest.TestCase):
    """The sh the Hooks run, with a stand-in python3 that logs its arguments and stdin, or none."""

    def setUp(self):
        self.bin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bin)
        self.log = os.path.join(self.bin, "log")
        for tool in ("dirname", "cat"):
            os.symlink(shutil.which(tool), os.path.join(self.bin, tool))

    def python3(self, code=0):
        path = os.path.join(self.bin, "python3")
        with open(path, "w") as f:
            f.write(
                f'#!{shutil.which("sh")}\n'
                f'echo "$*" >> "{self.log}"\n'
                f'cat >> "{self.log}"\n'
                f"echo failed >&2\n"
                f"exit {code}\n"
            )
        os.chmod(path, 0o755)

    def hook(self, *args, stdin=""):
        return subprocess.run(
            [shutil.which("sh"), HOOK, *args],
            input=stdin,
            capture_output=True,
            text=True,
            env={"PATH": self.bin},
        )

    def logged(self):
        if not os.path.exists(self.log):
            return ""
        with open(self.log) as f:
            return f.read()

    def test_session_start_without_python3_says_why(self):
        got = self.hook("session-start")
        self.assertEqual(got.returncode, 2)
        self.assertEqual(
            got.stderr,
            "baloo: python3 is missing, so no Check runs this session: install Python 3.9 or later\n",
        )

    def test_other_hooks_without_python3_say_nothing(self):
        got = self.hook("pre-tool-use", stdin="{}")
        self.assertEqual((got.returncode, got.stdout, got.stderr), (0, "", ""))

    def test_session_start_runs_run_py_and_shows_its_failure(self):
        self.python3(code=2)
        got = self.hook("session-start", stdin="{}")
        self.assertEqual((got.returncode, got.stderr), (2, "failed\n"))
        run = os.path.join(os.path.dirname(HOOK), "run.py")
        self.assertEqual(self.logged(), f"-E -s {run} session-start\n{{}}")

    def test_a_failing_hook_says_nothing_and_passes(self):
        self.python3(code=1)
        got = self.hook("post-tool-use", stdin='{"x": 1}')
        self.assertEqual((got.returncode, got.stderr), (0, ""))
        self.assertTrue(self.logged().endswith('post-tool-use\n{"x": 1}'))

    def test_reading_another_file_never_starts_python(self):
        self.python3()
        got = self.hook("allow-guideline", stdin='{"file_path": "/repo/main.go"}')
        self.assertEqual((got.returncode, got.stdout), (0, ""))
        self.assertEqual(self.logged(), "")

    def test_reading_a_guideline_passes_the_call_on(self):
        self.python3()
        call = '{"file_path": "/plugin/guidelines/go.md"}'
        self.hook("allow-guideline", stdin=call)
        self.assertTrue(self.logged().endswith("allow-guideline\n" + call + "\n"))


if __name__ == "__main__":
    unittest.main()
