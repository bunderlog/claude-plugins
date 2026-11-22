import unittest

from bagheera.checks import no_hidden_characters


def write(content):
    return {"tool_name": "Write", "tool_input": {"file_path": "a.py", "content": content}}


def edit(old, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": "a.py", "old_string": old,
                                                "new_string": new}}


def multi_edit(old, new):
    return {"tool_name": "MultiEdit", "tool_input": {"file_path": "a.py", "edits": [
        {"old_string": "x", "new_string": "y"}, {"old_string": old, "new_string": new}]}}


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# Written with escapes, so this file holds none of the characters it tests (PRD hidden-characters).
class NoHiddenCharacters(unittest.TestCase):
    def test_names_the_character_and_where(self):
        self.assertEqual(
            no_hidden_characters(write("ok = 1\nif admin\u202e:\n")),
            "the Write holds U+202E RIGHT-TO-LEFT OVERRIDE at line 2, column 9, which a person "
            "can't see in a terminal or a diff. If it's meant, write it as an escape, such as "
            "\\u202e.",
        )

    def test_denies_each_kind_in_each_tool(self):
        for c, escape in [("\u2066", "\\u2066"), ("\U000e0041", "\\U000e0041"),
                          ("\u200b", "\\u200b"), ("\u2060", "\\u2060"), ("\ufeff", "\\ufeff")]:
            for call in [write("a" + c), edit("a", "a" + c), multi_edit("a", "a" + c),
                         bash("echo a" + c)]:
                with self.subTest(c=escape, tool=call["tool_name"]):
                    self.assertIn("such as " + escape + ".", no_hidden_characters(call))

    def test_lets_through(self):
        for name, call in {
            "a leading byte order mark": write("\ufeffok = 1\n"),
            "an edit that removes one": edit("a\u200bb", "ab"),
            "an edit that keeps one": edit("a\u200bb", "a\u200bbc"),
            "an emoji sequence": write("\U0001f468\u200d\U0001f469\u200d\U0001f467"),
            "ZWNJ, LRM and RLM": write("\u200c\u200e\u200f"),
            "an escape": bash("printf '\\u200b'"),
            "a Read": {"tool_name": "Read", "tool_input": {"file_path": "a\u202e"}},
            "no input": {"tool_name": "Write"},
            "a content not text": {"tool_name": "Write", "tool_input": {"content": 1}},
        }.items():
            with self.subTest(name):
                self.assertEqual(no_hidden_characters(call), "")

    def test_a_flag_emoji_but_not_what_follows_it(self):
        england = chr(0x1F3F4) + "".join(chr(0xE0000 + ord(c)) for c in "gbeng") + chr(0xE007F)
        self.assertEqual(no_hidden_characters(write(england)), "")
        self.assertIn("U+200B", no_hidden_characters(write(england + chr(0x200B))))
        self.assertIn("U+E0041", no_hidden_characters(write("a" + chr(0xE0041))))

    def test_a_second_byte_order_mark(self):
        self.assertIn("U+FEFF", no_hidden_characters(write("\ufeffa\ufeff")))


if __name__ == "__main__":
    unittest.main()
