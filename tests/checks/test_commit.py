import unittest

from baloo.checks import CommitRules, conventional_commit

NOT_ONE_OF = "is not one of build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test"


class ConventionalCommit(unittest.TestCase):
    def test_accepts(self):
        for message in [
            "feat: add login",
            "fix(adr): correct a date",
            "feat!: drop node",
            "refactor(api/auth)!: split parse\n\nBody.",
            "feat: x\n\nBreaking change: a body line, not a footer.\n\nRefs: #1",
            "feat(multi word): a scope with spaces",
            "fix(ZrOpticsTab): a scope in any case",
            "docs: explain `README` and the API",
            "feat: 2 new checks",
            "feat: " + "x" * 94,
            "fix: x\n\n" + "y" * 100,
            "feat: é" + "x" * 93,
            "feat: x\n# ------------------------ >8 ------------------------\n" + "z" * 200,
            "# Please enter the commit message\n\ndocs: explain config",
            "Merge branch 'main' into feature",
            'Revert "feat: add login"',
            'Reapply "feat: add login"',
            "Merge pull request #7 from a/b",
            "Merge remote-tracking branch 'origin/main'",
            "fixup! feat: add login",
            "squash! feat: add login",
            "feat: x\n# a comment\n\nBody.",
            "feat: x\n# ------------------------ >8 ------------------------\ndiff --git a b",
            "feat: x\n\nBody.\n\nBREAKING CHANGE: drops node",
            "feat: x\n\nBREAKING-CHANGE: drops node\nRefs: #12",
            "feat: x\n\nBreaking change: not a token, so a body line",
            "feat: x\n\nRefs: #1\nbreaking change: part of the Refs value",
            "feat: x\n\nReviewed-by: Z\nCloses #42",
            "",
        ]:
            with self.subTest(message=message):
                self.assertEqual(conventional_commit(message, CommitRules()), "")

    # The examples in the Conventional Commits 1.0.0 specification, with LF and with CRLF.
    def test_accepts_the_specs_examples(self):
        for message in [
            "feat: allow provided config object to extend other configs\n\nBREAKING CHANGE: "
            "`extends` key in config file is now used for extending other config files",
            "feat!: send an email to the customer when a product is shipped",
            "feat(api)!: send an email to the customer when a product is shipped",
            "feat!: drop support for Node 6\n\nBREAKING CHANGE: use JavaScript features not "
            "available in Node 6.",
            "docs: correct spelling of CHANGELOG",
            "feat(lang): add Polish language",
            "fix: prevent racing of requests\n\nIntroduce a request id and a reference to latest "
            "request. Dismiss\nincoming responses other than from latest request.\n\nRemove "
            "timeouts which were used to mitigate the racing issue but are\nobsolete now.\n\n"
            "Reviewed-by: Z\nRefs: #123",
            "revert: let us never again speak of the noodle incident\n\nRefs: 676104e, a215868",
        ]:
            crlf = message.replace("\n", "\r\n") + "\r\n"
            for m in [message, crlf]:
                with self.subTest(message=m):
                    self.assertEqual(conventional_commit(m, CommitRules()), "")

    def test_rejects_a_subject_of_another_shape(self):
        for message in [
            "add login", "fix bug: x", "feat:add login", "feat:  x", "feat(): x", "feat( ): x",
            "feat (a): x", "feat: ", "Merge sort for the index",
        ]:
            with self.subTest(message=message):
                self.assertEqual(
                    conventional_commit(message, CommitRules()),
                    f'"{message}" is not `type(scope): description`',
                )

    # commitlint's config-conventional error rules.
    def test_rejects_what_commitlint_does(self):
        for message, want in [
            ("wip: any type", '"wip" ' + NOT_ONE_OF),
            ("i18n: digits in the type", '"i18n" ' + NOT_ONE_OF),
            ("Feat: any case", '"Feat" ' + NOT_ONE_OF),
            ("fix: Add Thing", '"Add Thing" starts with an uppercase letter'),
            ("fix: API timeout", '"API timeout" starts with an uppercase letter'),
            ("fix: add thing.", '"add thing." ends with a full stop'),
            ("fix: add thing ", '"fix: add thing " has trailing spaces'),
            ("feat: x\nBody.", 'leave a blank line between "feat: x" and the body'),
            ("feat: " + "x" * 95, '"feat: ' + "x" * 34 + '…" is 101 characters, over 100'),
            ("fix: x\n\n" + "y" * 101, '"' + "y" * 40 + '…" is 101 characters, over 100'),
            ("fix: x\n\nRefs: " + "1" * 100, '"Refs: ' + "1" * 34 + '…" is 106 characters, over 100'),
        ]:
            with self.subTest(message=message):
                self.assertEqual(conventional_commit(message, CommitRules()), want)

    def test_rejects_a_breaking_change_footer_of_another_shape(self):
        for footer in [
            "Breaking-Change: x", "breaking-change: x", "BREAKING CHANGE #12", "BREAKING-CHANGE #12",
        ]:
            with self.subTest(footer=footer):
                self.assertEqual(
                    conventional_commit("feat: x\n\nRefs: #1\n" + footer, CommitRules()),
                    f'"{footer}" is not `BREAKING CHANGE: description`',
                )
        # Footers are the trailing paragraphs that open with one, across blank lines.
        self.assertEqual(
            conventional_commit("feat: x\n\nBody.\n\nbreaking-change: y\n\nRefs: #1", CommitRules()),
            '"breaking-change: y" is not `BREAKING CHANGE: description`',
        )

    def test_takes_its_own_types_or_any(self):
        own = CommitRules(types=["wip", "feat"])
        for message, rules, want in [
            ("wip: x", own, ""),
            ("fix: x", own, '"fix" is not one of wip, feat'),
            ("wip: x", CommitRules(any_type=True), ""),
            ("add x", CommitRules(any_type=True), '"add x" is not `type(scope): description`'),
        ]:
            with self.subTest(message=message, rules=rules):
                self.assertEqual(conventional_commit(message, rules), want)

    def test_takes_its_own_line_length_or_none(self):
        for message, longest, want in [
            ("feat: " + "x" * 67, 72, '"feat: ' + "x" * 34 + '…" is 73 characters, over 72'),
            ("feat: x\n\n" + "y" * 73, 72, '"' + "y" * 40 + '…" is 73 characters, over 72'),
            ("feat: " + "x" * 500, 0, ""),
        ]:
            with self.subTest(message=message, longest=longest):
                self.assertEqual(conventional_commit(message, CommitRules(max_length=longest)), want)


if __name__ == "__main__":
    unittest.main()
