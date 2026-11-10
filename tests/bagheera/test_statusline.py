import json
import os
import re
import time
import unittest
from unittest import mock

from bagheera import binlink, names, statusline
from bagheera.statusline import Input, Layout, Thresholds, default
from tests import testkit

PLUGIN_ID = names.PLUGIN_ID
ON = '{"enabledPlugins": {"' + PLUGIN_ID + '": true}}'
THEIRS = '{"statusLine": {"type": "command", "command": "their-line"}}'
# The plugin's folder in this repo, where the code under test runs from.
PLUGIN = os.path.realpath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins", "bagheera")
)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def contents(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def status_line(path):
    """The command of the statusLine in the settings file at `path`, or "" for none."""
    text = contents(path)
    if not text:
        return ""
    line = json.loads(text).get("statusLine")
    return line["command"] if line else ""


class Ours(unittest.TestCase):
    # The command the person sets runs the plugin through the link, marked as the plugin's, and a
    # statusLine with that mark is told from the person's own.
    def test_command_and_ours(self):
        cmd = statusline.command("/data/bagheera")
        self.assertEqual(cmd, "python3 -E -s '/data/bagheera/scripts/run.py' status-line " + names.MARKER)
        self.assertTrue(statusline.ours({"type": "command", "command": cmd}))
        self.assertFalse(statusline.ours({"type": "command", "command": "my-line"}))
        self.assertFalse(statusline.ours("nope"))


class Link(unittest.TestCase):
    # The link points at the plugin's folder of the version running, and replaces one to another
    # version, or to the Go binary, in place.
    def test_point(self):
        data = testkit.tempdir(self)
        path = os.path.join(data, "bagheera")
        os.symlink("/old/baloo_0.25.1_linux_amd64", path)
        self.assertEqual(binlink.point(data), path)
        self.assertEqual(os.readlink(path), PLUGIN)
        self.assertEqual(binlink.point(data), path)
        self.assertEqual(os.listdir(data), ["bagheera"])
        self.assertTrue(os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json")))

    def test_no_data(self):
        with self.assertRaises(OSError) as caught:
            binlink.point("")
        self.assertEqual(str(caught.exception), "CLAUDE_PLUGIN_DATA is not set")


_COLORS = re.compile(r"\x1b\[[0-9;]*m")


def plain(s):
    """`s` without its colors."""
    return _COLORS.sub("", s)


def parse(text):
    return Input.parse(json.loads(text))


def at(day, hour, minute):
    """The epoch seconds of a local time on 2026-09-24, or the day after for a `day` of 25."""
    return int(time.mktime((2026, 9, day, hour, minute, 0, 0, 0, -1)))


def usage(extra=""):
    """An Input with every Usage figure, and `extra` fields."""
    return parse(
        '{"context_window": {"used_percentage": 12}, "rate_limits": {'
        f'"five_hour": {{"used_percentage": 55, "resets_at": {at(24, 14, 0)}}},'
        f'"seven_day": {{"used_percentage": 81}}}}{extra}}}'
    )


MODEL = ', "model": {"display_name": "Opus 5.5"}, "effort": {"level": "high"}'


GREY, YELLOW, RED = "\x1b[90m", "\x1b[33m", "\x1b[31m"


class Render(unittest.TestCase):
    # Each part is its icon and its number, grey, then yellow and red from its thresholds, the
    # icon and the number together.
    def test_used(self):
        th = Thresholds(50, 80)
        for percent, want in [(34.6, "▤ 35%"), (150, "▤ 100%"), (-3, "▤ 0%"), (12.5, "▤ 13%")]:
            self.assertEqual(plain(statusline._used("context", percent, th)), want)
        for percent, color in [(49, GREY), (50, YELLOW), (80, RED)]:
            self.assertTrue(statusline._used("context", percent, th).startswith(color), percent)

    # The context is yellow from 15% and red from 20%, its tokens grey.
    def test_context_colors(self):
        for used, color in [("14.4", GREY), ("15", YELLOW), ("19.4", YELLOW), ("20", RED)]:
            got = default().render(parse('{"context_window": {"used_percentage": ' + used + "}}"), "", 120)
            self.assertIn(color + "▤ ", got, used)
        got = default().render(
            parse('{"context_window": {"used_percentage": 22, "total_input_tokens": 120000}}'), "", 120
        )
        self.assertIn(RED + "▤ 22%\x1b[00m " + GREY + "120K", got)

    # The 7-day limit shows the weekday it resets on, and drops it with the 5-hour reset time when
    # narrow.
    def test_reset_day(self):
        in_ = parse(
            '{"rate_limits": {"five_hour": {"used_percentage": 55, "resets_at": %d},'
            '"seven_day": {"used_percentage": 81, "resets_at": %d}}}'
            % (at(24, 14, 0), at(28, 9, 30))
        )
        got = plain(default().render(in_, "", 120))
        self.assertTrue(got.endswith("◷ 55% 14:00 · ◷ 81% Mon"), got)
        in_.model = "Opus 5.5"
        self.assertNotIn("Mon", plain(default().render(in_, "feature-branch-x", 44)))

    # The reset time shows alone, even past midnight.
    def test_reset_time(self):
        self.assertEqual(statusline._reset_time(float(at(24, 14, 5))), "14:05")
        self.assertEqual(statusline._reset_time(float(at(25, 1, 0))), "01:00")

    # The parts are centered, three spaces apart, and the model and its effort are flush right,
    # all grey while nothing is past a threshold.
    def test_layout(self):
        line = plain(default().render(usage(), "main", 200))
        self.assertTrue(line.startswith("main   "), line)
        self.assertIn("▤ 12% · ◷ 55% 14:00 · ◷ 81%", line)
        self.assertTrue(line.endswith("◷ 81%"), line)
        mid = len(line) - line.index("▤")
        self.assertEqual(line.index("▤"), (196 - mid) // 2, "centered")

        colored = default().render(usage(MODEL), "main", 200)
        line = plain(colored)
        self.assertRegex(line, r"81% {3,}Opus 5\.5 high$")
        self.assertEqual(len(line), 196)
        self.assertTrue(colored.endswith(GREY + "Opus 5.5 high\x1b[00m"), colored)
        got = plain(default().render(parse('{"model": {"display_name": "Opus 5.5"}}'), "", 120))
        self.assertTrue(got.endswith("   Opus 5.5"), got)

    # The project's folder comes before the branch, so it's clear which project a terminal shows:
    # the one Claude Code runs in, not the folder a command moved to; both grey.
    def test_folder(self):
        in_ = parse('{"workspace": {"current_dir": "/w/shop/apps/web", "project_dir": "/w/shop"}}')
        colored = default().render(in_, "main", 120)
        self.assertTrue(plain(colored).startswith("shop main"), plain(colored))
        self.assertIn(GREY + "shop main", colored)
        in_ = parse('{"workspace": {"current_dir": "/w/notes"}}')
        self.assertEqual(plain(default().render(in_, "", 120)).strip(), "notes")

    # When narrow, the line drops the details, then the model; no bar shows at any width.
    def test_narrow(self):
        in_ = usage(MODEL)
        for columns, want, suffix in [
            (54, "▤ 12% · ◷ 55% 14:00", False),
            (53, "◷ 55% · ◷ 81%   Opus 5.5 high", True),
            (48, "◷ 55% · ◷ 81%   Opus 5.5 high", True),
            (47, "◷ 55% · ◷ 81%", True),
        ]:
            line = plain(default().render(in_, "main", columns))
            if suffix:
                self.assertTrue(line.endswith(want), (columns, line))
            else:
                self.assertIn(want, line, columns)
            self.assertNotRegex(line, "[█░]")

    # The parts never overlap the branch, and the line shows nothing it isn't given.
    def test_bounds(self):
        got = plain(default().render(usage(), "a-very-long-branch-name-that-fills-the-line", 20))
        self.assertIn("line   ▤", got)
        self.assertEqual(default().render(Input(), "", 120).strip(), "")
        self.assertLessEqual(statusline._visible(default().render(usage(), "", 120)), 116)

    # Before the first reply the context shows 0%.
    def test_empty_context(self):
        for window in [
            "{}",
            '{"used_percentage": null}',
            '{"used_percentage": 0, "total_input_tokens": 0}',
        ]:
            got = plain(default().render(parse('{"context_window": ' + window + "}"), "", 120))
            self.assertEqual(got.strip(), "▤ 0%", window)

    # The context's tokens follow its percentage, rounded to thousands.
    def test_tokens(self):
        for tokens, want in [
            ("120400", "60% 120K"),
            ("199600", "60% 200K"),
            ("400", "60% 0K"),
        ]:
            got = plain(
                default().render(
                    parse(
                        '{"context_window": {"used_percentage": 60, "total_input_tokens": '
                        + tokens
                        + "}}"
                    ),
                    "",
                    120,
                )
            )
            self.assertTrue(got.endswith(want), got)

    # A field of the wrong type is left out, as Go's decoder left it, and the rest still shows.
    def test_wrong_types(self):
        got = plain(
            default().render(
                parse(
                    '{"context_window": {"used_percentage": "12"}, "model": {"display_name": 5},'
                    '"rate_limits": {"five_hour": {"used_percentage": 55, "resets_at": true}}}'
                ),
                "",
                120,
            )
        )
        self.assertEqual(got.strip(), "▤ 0% · ◷ 55%")
        self.assertEqual(default().render(Input.parse([1, 2]), "", 120).strip(), "")


class Marks(unittest.TestCase):
    # How many sessions wait and how many projects need attention show in yellow before the model,
    # each only when it isn't 0, naming no project; they stay when the model goes (PRD visibility).
    def test_marks(self):
        in_ = usage(MODEL)
        colored = default().render(in_, "main", 120, 3, 2)
        self.assertTrue(plain(colored).endswith("⧗ 3 · ⚑ 2 · Opus 5.5 high"), plain(colored))
        self.assertIn(YELLOW + "⧗ 3", colored)
        self.assertIn(YELLOW + "⚑ 2", colored)
        self.assertTrue(plain(default().render(in_, "main", 120, 0, 2)).endswith("   ⚑ 2 · Opus 5.5 high"))
        line = plain(default().render(in_, "main", 120))
        self.assertNotIn("⧗", line)
        self.assertNotIn("⚑", line)
        narrow = plain(default().render(in_, "main", 52, 3, 2))
        self.assertTrue(narrow.endswith("⧗ 3 · ⚑ 2"), narrow)
        self.assertNotIn("Opus", narrow)

    # With nothing past a threshold and nothing waiting, every part of the line is grey.
    def test_all_grey(self):
        in_ = parse('{"context_window": {"used_percentage": 12}, "rate_limits": {'
                    '"five_hour": {"used_percentage": 30}, "seven_day": {"used_percentage": 40}}'
                    + MODEL + "}")
        colored = default().render(in_, "main", 120)
        self.assertNotIn(YELLOW, colored)
        self.assertNotIn(RED, colored)


class Cache(unittest.TestCase):
    START = at(24, 14, 0)

    def cached(self, fields):
        """The Input with a prompt cache of `fields`, the clock stopped at START."""
        patcher = mock.patch.object(statusline, "now", lambda: float(self.START))
        patcher.start()
        self.addCleanup(patcher.stop)
        return parse(
            '{"context_window": {"used_percentage": 12}, "prompt_cache": {"caching_observed": true, '
            + fields
            + '}, "rate_limits": {"five_hour": {"used_percentage": 55}}}'
        )

    # The cache's part, after the 7-day limit, shows the minutes until the cache goes cold,
    # rounded up: grey, then yellow below 40% of its lifetime left and red below 20%.
    def test_cache(self):
        warm = '"warm": true, "ttl": "5m", "expires_at": ' + str(self.START + 221)
        for fields, want in [
            (warm, "▤ 12% · ◷ 55% · ↻ 4m"),
            (warm + ', "recache_tokens_if_cold": 45000', "↻ 4m"),
            ('"warm": true, "ttl": "1h", "expires_at": ' + str(self.START + 3600), "↻ 60m"),
            ('"warm": true, "ttl": "2h", "expires_at": ' + str(self.START + 30), "↻ 1m"),
        ]:
            got = plain(default().render(self.cached(fields), "", 120))
            self.assertIn(want, got, fields)
            self.assertNotIn("45K", got)
        for left, color in [(120, GREY), (118, YELLOW), (61, YELLOW), (58, RED)]:
            got = default().render(
                self.cached('"warm": true, "ttl": "5m", "expires_at": ' + str(self.START + left)),
                "",
                120,
            )
            self.assertIn(color + "↻ ", got, left)

    # A cold cache says so in red; with caching off there is no cache part.
    def test_cold(self):
        for fields in [
            '"warm": false, "expires_at": null, "recache_tokens_if_cold": 151200',
            '"warm": true, "expires_at": ' + str(self.START),
        ]:
            got = default().render(self.cached(fields), "", 120)
            self.assertIn(RED + "↻ cold", got, fields)
        off = parse('{"prompt_cache": {"caching_observed": false, "warm": false}}')
        self.assertEqual(default().render(off, "", 120).strip(), "")

    # Without the context, the cache's part shows its size, the context's tokens, after its
    # minutes or cold.
    def test_size(self):
        no_context = Layout(["cache", "5h"], default().thresholds)
        for fields, want in [
            (
                '"warm": true, "ttl": "5m", "expires_at": '
                + str(self.START + 221)
                + ', "recache_tokens_if_cold": 45000',
                "↻ 4m 45K · ◷ 55%",
            ),
            ('"warm": false, "recache_tokens_if_cold": 151200', "↻ cold 151K · ◷ 55%"),
            ('"warm": false, "recache_tokens_if_cold": null', "↻ cold · ◷ 55%"),
        ]:
            got = plain(no_context.render(self.cached(fields), "", 120)).strip()
            self.assertTrue(got.startswith(want), (fields, got))


class Defaults(unittest.TestCase):
    def test_default(self):
        layout = default()
        self.assertEqual(layout.bars, ["context", "5h", "7d", "cache"])
        self.assertEqual(layout.thresholds["cache"], Thresholds(40, 20))
        layout.bars.append("x")
        layout.thresholds["cache"].red = 1
        self.assertEqual(default().bars, ["context", "5h", "7d", "cache"])
        self.assertEqual(default().thresholds["cache"], Thresholds(40, 20))

    def test_ordered(self):
        self.assertTrue(statusline.ordered("context", Thresholds(15, 20)))
        self.assertFalse(statusline.ordered("context", Thresholds(20, 15)))
        self.assertTrue(statusline.ordered("cache", Thresholds(40, 20)))
        self.assertFalse(statusline.ordered("cache", Thresholds(20, 40)))


class Branch(unittest.TestCase):
    def test_branch(self):
        folder = testkit.tempdir(self)
        with mock.patch.dict(
            os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        ):
            if statusline.branch(folder):
                self.skipTest("the temporary folder is inside a repo")
            testkit.git(folder, "init", "-q", "-b", "work")
            self.assertEqual(statusline.branch(folder), "work")
            testkit.git(
                folder, "-c", "user.name=t", "-c", "user.email=t@example.com",
                "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "x",
            )
            testkit.git(folder, "checkout", "-q", "--detach")
            commit = testkit.git(folder, "rev-parse", "--short", "HEAD").strip()
            self.assertEqual(statusline.branch(folder), commit)
        self.assertEqual(statusline.branch(""), "")


if __name__ == "__main__":
    unittest.main()
