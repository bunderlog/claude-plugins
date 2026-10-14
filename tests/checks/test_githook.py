import io
import os
import unittest

from baloo import checks
from baloo.checks import CommitRules, Input
from tests import testkit
from tests.checks import stage


def every(_: str) -> bool:
    """Turns every Check on."""
    return True


class Run(unittest.TestCase):
    def message(self, text: str) -> str:
        """A commit message file holding `text`."""
        path = os.path.join(testkit.tempdir(self), "COMMIT_EDITMSG")
        with open(path, "w") as f:
            f.write(text)
        return path

    def run_check(self, name, args, in_):
        """run's exit code and what it printed."""
        stderr = io.StringIO()
        code = checks.run(name, args, in_, every, stderr)
        self.assertIsNotNone(code, f"run({name}, {args}) not ok")
        return code, stderr.getvalue()

    # A commit-msg Check fails with what is wrong, for git to stop the commit and show it.
    def test_commit_message(self):
        for name, message, want in [
            ("no-ai-coauthor", "feat: x\n\nCo-authored-by: Jane Doe <jane@example.com>\n", (0, "")),
            (
                "no-ai-coauthor",
                "feat: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n",
                (
                    1,
                    "baloo:no-ai-coauthor: remove the AI co-author or credit:\n"
                    "Co-Authored-By: Claude <noreply@anthropic.com>\n",
                ),
            ),
            ("conventional-commits", "feat: x\n", (0, "")),
            (
                "conventional-commits",
                "Add x\n",
                (1, 'baloo:conventional-commits: "Add x" is not `type(scope): description`\n'),
            ),
        ]:
            with self.subTest(name=name, message=message):
                self.assertEqual(self.run_check(name, [self.message(message)], Input()), want)
        missing = os.path.join(testkit.tempdir(self), "nope")
        for name in ["no-ai-coauthor", "conventional-commits"]:
            with self.subTest(name=name, message="missing"):
                code, errs = self.run_check(name, [missing], Input())
                self.assertEqual(code, 2)
                self.assertEqual(
                    errs, f"baloo:{name}: open {missing}: no such file or directory\n"
                )

    # conventional-commits takes its settings from the Input.
    def test_commit_rules(self):
        path = self.message("wip: x\n")
        for rules, want in [
            (CommitRules(), 1),
            (CommitRules(types=["wip"]), 0),
            (CommitRules(any_type=True), 0),
        ]:
            with self.subTest(rules=rules):
                code, _ = self.run_check("conventional-commits", [path], Input(rules=rules))
                self.assertEqual(code, want)

    # The pre-commit Check no-secrets-in-commits fails with where each Secret is, but not the
    # Secret.
    def test_no_secrets_in_commits(self):
        dir = testkit.repo(self)
        self.assertEqual(self.run_check("no-secrets-in-commits", [], Input(dir=dir)), (0, ""))
        secret = "AKIA" + "IOSFODNN7EXAMPLE"  # cspell:disable-line
        stage(dir, {"a.go": secret})
        self.assertEqual(
            self.run_check("no-secrets-in-commits", [], Input(dir=dir)),
            (
                1,
                "baloo:no-secrets-in-commits: remove each secret, or mark a false alarm with "
                "baloo:allow-secret:\na.go:1: an AWS access key\n",
            ),
        )

    # The pre-commit Check no-stale-adr-date fails with each ADR changed without today's Date.
    def test_no_stale_adr_date(self):
        dir = testkit.repo(self)

        def write(date, decision):
            stage(dir, {".about/adr/billing.md": f"# Billing\n\nDate: {date}\n\n{decision}\n"})

        write("2020-01-01", "Invoices are monthly.")
        testkit.git(dir, "commit", "-q", "-m", "docs: adr")
        write("2020-01-01", "Invoices are weekly.")
        in_ = Input(dir=dir, today="2026-10-01")
        self.assertEqual(
            self.run_check("no-stale-adr-date", [], in_),
            (
                1,
                "baloo:no-stale-adr-date: an ADR's Date is when it last changed:\n"
                ".about/adr/billing.md: changed, but its Date is 2020-01-01; set it to "
                "2026-10-01\n",
            ),
        )
        write("2026-10-01", "Invoices are weekly.")
        self.assertEqual(self.run_check("no-stale-adr-date", [], in_), (0, ""))

    # The pre-commit Check no-conflict-markers fails with where each marker is.
    def test_no_conflict_markers(self):
        dir = testkit.repo(self)
        stage(dir, {"a.go": "<" * 7 + " HEAD\n"})
        self.assertEqual(
            self.run_check("no-conflict-markers", [], Input(dir=dir)),
            (
                1,
                "baloo:no-conflict-markers: resolve each conflict, or give a file that holds "
                "markers on purpose a longer conflict-marker-size in .gitattributes; conflict "
                "markers:\na.go:1\n",
            ),
        )

    # The pre-commit Check no-large-files fails with each file over the limit the Input gives.
    def test_no_large_files(self):
        dir = testkit.repo(self)
        stage(dir, {"app": "x" * 2048})
        self.assertEqual(
            self.run_check("no-large-files", [], Input(dir=dir, max_file_kb=1)),
            (
                1,
                "baloo:no-large-files: keep each out of git, or raise no-large-files' max-size "
                "in .claude/baloo.yml:\napp: 2 KB, over 1 KB\n",
            ),
        )
        self.assertEqual(self.run_check("no-large-files", [], Input(dir=dir)), (0, ""))

    # The pre-push Check linear-history fails with the merge commits the push sends, as git gives
    # them on stdin.
    def test_linear_history(self):
        dir = testkit.repo(self)
        testkit.git(dir, "commit", "-q", "--allow-empty", "-m", "feat: base")
        testkit.git(dir, "checkout", "-q", "-b", "side")
        testkit.git(dir, "commit", "-q", "--allow-empty", "-m", "feat: side")
        testkit.git(dir, "checkout", "-q", "main")
        base = testkit.git(dir, "rev-parse", "HEAD").strip()
        testkit.git(dir, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
        merge = testkit.git(dir, "rev-parse", "HEAD").strip()
        for local, remote, want_code, want in [
            (base, "0" * 40, 0, ""),
            (
                merge,
                base,
                1,
                "baloo:linear-history: rebase instead of merging, then push the rebased branch "
                "with --force-with-lease; git config pull.rebase true makes git pull rebase; "
                f"merge commits:\nrefs/heads/main {merge[:12]}\n",
            ),
            ("2" * 40, base, 2, "baloo:linear-history: git rev-list: "),
        ]:
            pushed = f"refs/heads/main {local} refs/heads/main {remote}\n"
            with self.subTest(pushed=pushed):
                code, errs = self.run_check(
                    "linear-history", [], Input(dir=dir, stdin=io.StringIO(pushed))
                )
                self.assertEqual(code, want_code)
                if want_code == 2:  # after why git failed
                    self.assertTrue(errs.startswith(want), errs)
                else:
                    self.assertEqual(errs, want)

    # A Check the Config turns off passes everything; an unknown Check, or one given arguments it
    # doesn't take, is not ok.
    def test_off_and_unknown(self):
        path = self.message("Add x\n")
        stderr = io.StringIO()
        self.assertEqual(
            checks.run("conventional-commits", [path], Input(), lambda _: False, stderr), 0
        )
        self.assertEqual(stderr.getvalue(), "")
        for name, args in {
            "nope": [],
            "conventional-commits": [],
            "no-ai-coauthor": [path, path],
            "no-secrets-in-commits": [path],
        }.items():
            with self.subTest(name=name, args=args):
                self.assertIsNone(checks.run(name, args, Input(), every, stderr))


class RunHook(unittest.TestCase):
    # A Git hook runs each of its Checks, all of them, and fails with the worst; it takes from
    # git's arguments only the message file of commit-msg.
    def test_runs_each_check_of_the_git_hook(self):
        path = os.path.join(testkit.tempdir(self), "COMMIT_EDITMSG")
        with open(path, "w") as f:
            f.write("Add x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
        stderr = io.StringIO()
        self.assertEqual(checks.run_hook("commit-msg", [path, "extra"], Input(), every, stderr), 1)
        self.assertIn("baloo:no-ai-coauthor: ", stderr.getvalue())
        self.assertIn("baloo:conventional-commits: ", stderr.getvalue())
        self.assertIsNone(checks.run_hook("commit-msg", [], Input(), every, stderr))
        # The plugin writes no post-merge Git hook.
        self.assertIsNone(checks.run_hook("post-merge", [], Input(), every, stderr))
        dir = testkit.repo(self)
        stderr = io.StringIO()
        in_ = Input(dir=dir, stdin=io.StringIO(""))
        self.assertEqual(checks.run_hook("pre-push", ["origin", "url"], in_, every, stderr), 0)
        self.assertEqual(stderr.getvalue(), "")


class Registry(unittest.TestCase):
    # usage names each Check with what it takes.
    def test_usage(self):
        got = "\n".join(checks.usage()) + "\n"
        for want in [
            "check no-ai-coauthor <message file>",
            "check no-secrets-in-commits\n",
            "check linear-history < <pushed refs>",
        ]:
            self.assertIn(want, got)

    # Each Check a Git hook runs has a name of its own and a Git hook git calls.
    def test_git_hook_checks(self):
        gits = [
            "applypatch-msg", "pre-applypatch", "post-applypatch", "pre-commit",
            "pre-merge-commit", "prepare-commit-msg", "commit-msg", "post-commit", "pre-rebase",
            "post-checkout", "post-merge", "pre-push", "pre-auto-gc", "post-rewrite",
        ]
        self.assertEqual(len(checks.GIT_HOOK_CHECKS), len(set(checks.GIT_HOOK_CHECKS)))
        for hook in checks.GIT_HOOKS:
            self.assertIn(hook, gits)


if __name__ == "__main__":
    unittest.main()
