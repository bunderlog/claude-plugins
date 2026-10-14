import os
import unittest

from baloo import yaml

ROOT = os.path.dirname(os.path.dirname(__file__))


def value(text):
    node = yaml.parse(text)
    return None if node is None else node.value


class Parse(unittest.TestCase):
    # This repo's own Config is the subset's main use.
    def test_this_repos_config(self):
        with open(os.path.join(ROOT, ".claude", "baloo.yml")) as f:
            got = value(f.read())
        self.assertEqual(got["output-style"], "short-replies")
        self.assertEqual(got["status-line"]["bars"], ["context", "5h", "7d", "cache"])
        self.assertEqual(got["status-line"]["thresholds"]["cache"], {"yellow": 40, "red": 20})
        self.assertIs(got["guidelines"]["vue"], False)
        self.assertNotIn("format-on-edit", got)

    def test_nothing(self):
        for text in ["", "# only a comment\n", "\n\n", "---\n", "\N{BYTE ORDER MARK}"]:
            with self.subTest(text=text):
                self.assertIsNone(yaml.parse(text))

    def test_scalars(self):
        for text, want, tag in [
            ("a:", None, "null"),
            ("a: ~", None, "null"),
            ("a: null", None, "null"),
            ("a: true", True, "bool"),
            ("a: FALSE", False, "bool"),
            ("a: yes", "yes", "str"),
            ("a: 12", 12, "int"),
            ("a: -3", -3, "int"),
            ("a: 0x1f", 31, "int"),
            ("a: 1.5", 1.5, "float"),
            ("a: .inf", float("inf"), "float"),
            ("a: '12'", "12", "str"),
            ("a: 'it''s'", "it's", "str"),
            ('a: "tab\\there \\u00e9"', "tab\there \u00e9", "str"),
            ("a: npx prettier --write", "npx prettier --write", "str"),
            ("a: echo don't # stop", "echo don't", "str"),
            ("a: 'x # y'", "x # y", "str"),
            ("a: http://x.y/z#frag", "http://x.y/z#frag", "str"),
            ("a: 5h", "5h", "str"),
        ]:
            with self.subTest(text=text):
                node = yaml.parse(text).pairs[0][1]
                self.assertEqual((node.value, node.tag), (want, tag))

    def test_lists(self):
        for text in [
            "a: [x, y]",
            "a:\n  - x\n  - y",
            "a:\n- x\n- y",
            "a: [x,\n    y]",
            "a: [ 'x' , \"y\", ]",
        ]:
            with self.subTest(text=text):
                self.assertEqual(value(text), {"a": ["x", "y"]})

    def test_maps(self):
        want = {"a": {"b": {"c": 1, "d": 2}, "e": None}}
        for text in [
            "a:\n  b:\n    c: 1\n    d: 2\n  e:",
            "a: { b: { c: 1, d: 2 }, e: }",
            "a: {b: {c: 1, d: 2}, e}",
            "a: {\n  b: {c: 1,\n    d: 2},\n  e: ~ }",
            "a:\n   b: {c: 1, d: 2}\n   e: null",
        ]:
            with self.subTest(text=text):
                self.assertEqual(value(text), want)

    def test_top_level(self):
        self.assertEqual(value("- a\n- b\n"), ["a", "b"])
        self.assertEqual(value("true\n"), True)
        self.assertEqual(value("{}\n"), {})
        self.assertEqual(value("'a': 1\n\"b\": 2\n"), {"a": 1, "b": 2})

    def test_lines(self):
        top = yaml.parse("# head\n\na: 1\nb:\n  c: [x,\n    y]\n")
        (a, one), (b, inner) = top.pairs
        self.assertEqual((top.line, a.line, one.line, b.line, inner.line), (3, 3, 3, 4, 5))
        c, xy = inner.pairs[0]
        self.assertEqual([c.line, xy.line] + [i.line for i in xy.items], [5, 5, 5, 6])

    def test_documents(self):
        self.assertEqual(value("---\na: 1\n---\nb: 2\n"), {"a": 1})
        self.assertEqual(value("a: 1\n...\nb: 2\n"), {"a": 1})

    def test_line_endings(self):
        self.assertEqual(value("\N{BYTE ORDER MARK}a: 1\r\nb: [x]\r\n"), {"a": 1, "b": ["x"]})


class Errors(unittest.TestCase):
    def test_errors(self):
        for text, want in [
            ("a: [1\n", "line 1: did not find expected ',' or ']'"),
            ("a: {b: 1\n", "line 1: did not find expected ',' or '}'"),
            ("a: [1,\n  2\nb: 3\n", "line 3: did not find expected ',' or ']'"),
            ("a: [1] x\n", "line 1: unexpected text after ]"),
            ("a: 1\na: 2\n", 'line 2: mapping key "a" already defined at line 1'),
            ("a: {b: 1, b: 2}\n", 'line 1: mapping key "b" already defined at line 1'),
            ("a:\n\tb: 1\n", "line 2: found a tab character that violates indentation"),
            ("a: 1\n  b: 2\n", "line 2: unexpected indentation"),
            ("a:\n    b: 1\n  c: 2\n", "line 3: unexpected indentation"),
            ("a: 1\nb\n", "line 2: did not find expected key"),
            ("a: b: c\n", "line 1: mapping values are not allowed in this context"),
            ("a: &x 1\n", "line 1: an anchor is not supported"),
            ("a: *x\n", "line 1: an alias is not supported"),
            ("a: !!str 1\n", "line 1: a tag is not supported"),
            ("a: |\n  text\n", "line 1: a block scalar is not supported"),
            ("a: [&x 1]\n", "line 1: an anchor is not supported"),
            ("- a: 1\n", "line 1: a map inside a list is not supported"),
            ("a: [b: 1]\n", "line 1: a map inside a list is not supported"),
            ("a: 'open\n", "line 1: found unexpected end of line while parsing a quoted scalar"),
            ('a: "\\q"\n', "line 1: found unknown escape character while parsing a quoted scalar"),
            ("a: [,]\n", "line 1: did not find expected node content"),
            ("- a\nb: 1\n", "line 2: unexpected text"),
            ("%YAML 1.2\n", "line 1: a directive is not supported"),
        ]:
            with self.subTest(text=text):
                with self.assertRaises(yaml.Error) as caught:
                    yaml.parse(text)
                self.assertEqual(str(caught.exception), want)


if __name__ == "__main__":
    unittest.main()
