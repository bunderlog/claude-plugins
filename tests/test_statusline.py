import json
import os
import re
import time
import unittest
from unittest import mock

from baloo import binlink, names, statusline
from baloo.statusline import Input, Layout, Thresholds, default
from tests import testkit

PLUGIN_ID = names.PLUGIN_ID
ON = '{"enabledPlugins": {"' + PLUGIN_ID + '": true}}'
THEIRS = '{"statusLine": {"type": "command", "command": "their-line"}}'
# The plugin's folder in this repo, where the code under test runs from.
PLUGIN = os.path.realpath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "baloo")
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


def want_command(data):
    return "python3 -E -s '" + os.path.join(data, "baloo") + "/scripts/run.py' status-line # managed by baloo"


class Sandbox(unittest.TestCase):
    """A temporary repo with the user's and the managed settings of its own, none of them there
    yet, and a plugin data folder."""

    def setUp(self):
        self.root = testkit.tempdir(self)
        self.own = testkit.tempdir(self)
        self.data = testkit.tempdir(self)
        os.mkdir(os.path.join(self.root, ".git"))
        patcher = mock.patch.dict(
            os.environ,
            {
                "CLAUDE_CONFIG_DIR": self.own,
                "BALOO_MANAGED_SETTINGS": os.path.join(self.own, "managed-settings.json"),
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.local = os.path.join(self.root, names.LOCAL_SETTINGS)

    def set(self, on=True, data=None):
        return statusline.set_line(self.root, self.root, self.data if data is None else data, on)


class Set(Sandbox):
    def test_set(self):
        enabled_with_line = (
            '{"statusLine": {"type": "command", "command": "x"}, "enabledPlugins": {"'
            + PLUGIN_ID
            + '": true}}'
        )
        for name, local, project, user, manage, shown in [
            ("enabled in the project", "", ON, "", "", True),
            ("enabled here", ON, "", "", "", True),
            ("enabled for the user, who has a status line", "", "", enabled_with_line, "", True),
            ("not enabled anywhere", "", "", "", "", False),
            ("enabled only by managed settings", "", "", "", ON, False),
            ("a status line here", enabled_with_line, "", "", "", False),
            ("a status line in the project", "", enabled_with_line, "", "", False),
            ("a status line in managed settings", "", ON, "", THEIRS, False),
        ]:
            with self.subTest(name):
                self.setUp()
                for path, text in [
                    (self.local, local),
                    (os.path.join(self.root, names.PROJECT_SETTINGS), project),
                    (os.path.join(self.own, "settings.json"), user),
                    (os.path.join(self.own, "managed-settings.json"), manage),
                ]:
                    if text:
                        write(path, text)
                before = contents(self.local)
                self.assertEqual(self.set(), (shown, None))
                if shown:
                    self.assertEqual(status_line(self.local), want_command(self.data))
                else:
                    self.assertEqual(contents(self.local), before)

    # The command runs the plugin through a link in the data folder, and a second session start
    # changes nothing.
    def test_links(self):
        write(os.path.join(self.own, "settings.json"), ON)
        self.assertEqual(self.set(), (True, None))
        self.assertEqual(os.readlink(os.path.join(self.data, "baloo")), PLUGIN)
        before = contents(self.local)
        self.assertEqual(self.set(), (False, None))
        self.assertEqual(contents(self.local), before)
        self.assertEqual(
            contents(os.path.join(self.root, ".git", "info", "exclude")),
            "/" + names.LOCAL_SETTINGS + "\n",
        )
        self.assertEqual(os.listdir(self.data), ["baloo"])

    # The plugin's own status line, from another data folder or the Go binary, is set again in
    # place, and turned off it is taken out, the rest of the file kept; another's is left alone.
    def test_own(self):
        old = (
            '{\n  "enabledPlugins": {"' + PLUGIN_ID + '": true},\n'
            '  "statusLine": {"type": "command", "command": "\'/old/baloo\' status-line # managed '
            'by baloo", "padding": 0}\n}\n'
        )
        write(self.local, old)
        self.assertEqual(self.set(), (False, None))
        self.assertEqual(status_line(self.local), want_command(self.data))
        self.assertEqual(json.loads(contents(self.local))["statusLine"]["refreshInterval"], 60)
        self.assertEqual(self.set(on=False), (False, None))
        self.assertEqual(
            contents(self.local), '{\n  "enabledPlugins": {"' + PLUGIN_ID + '": true}\n}\n'
        )
        write(self.local, THEIRS)
        self.assertEqual(self.set(on=False), (False, None))
        self.assertEqual(contents(self.local), THEIRS)

    # The plugin's own status line gives way to one the project or managed settings set later.
    def test_own_gives_way(self):
        for scope in ["project", "managed"]:
            with self.subTest(scope):
                self.setUp()
                write(self.local, ON)
                self.assertEqual(self.set(), (True, None))
                path = os.path.join(self.root, names.PROJECT_SETTINGS)
                if scope == "managed":
                    path = os.path.join(self.own, "managed-settings.json")
                write(path, THEIRS)
                self.assertEqual(self.set(), (False, None))
                self.assertEqual(status_line(self.local), "")

    # Without the data folder the status line can't be set, which is an error only where it would
    # be.
    def test_no_data(self):
        self.assertEqual(self.set(data=""), (False, None))
        write(os.path.join(self.own, "settings.json"), ON)
        shown, err = self.set(data="")
        self.assertFalse(shown)
        self.assertEqual(str(err), "CLAUDE_PLUGIN_DATA is not set")

    def test_broken_settings(self):
        write(self.local, "{")
        shown, err = self.set()
        self.assertFalse(shown)
        self.assertTrue(str(err).startswith(self.local + ": "), err)


class Link(unittest.TestCase):
    # The link points at the plugin's folder of the version running, and replaces one to another
    # version, or to the Go binary, in place.
    def test_point(self):
        data = testkit.tempdir(self)
        path = os.path.join(data, "baloo")
        os.symlink("/old/baloo_0.25.1_linux_amd64", path)
        self.assertEqual(binlink.point(data), path)
        self.assertEqual(os.readlink(path), PLUGIN)
        self.assertEqual(binlink.point(data), path)
        self.assertEqual(os.listdir(data), ["baloo"])
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
    """An Input with every Usage bar, and `extra` fields."""
    return parse(
        '{"context_window": {"used_percentage": 12}, "rate_limits": {'
        f'"five_hour": {{"used_percentage": 55, "resets_at": {at(24, 14, 0)}}},'
        f'"seven_day": {{"used_percentage": 81}}}}{extra}}}'
    )


MODEL = ', "model": {"display_name": "Opus 5.5"}, "effort": {"level": "high"}'


class Render(unittest.TestCase):
    def test_bar(self):
        th = Thresholds(50, 80)
        for percent, width, want in [
            (34.6, 10, "███░░░░░░░ 35%"),
            (150, 5, "█████ 100%"),
            (-3, 5, "░░░░░ 0%"),
            (12.5, 10, "█░░░░░░░░░ 13%"),  # half rounds away from zero, as Go's
        ]:
            self.assertEqual(plain(statusline._bar(percent, width, th)), want)
        for percent, color in [(49, "\x1b[2;32m"), (50, "\x1b[2;33m"), (80, "\x1b[2;31m")]:
            self.assertTrue(statusline._bar(percent, 10, th).startswith(color), percent)

    # The context bar is yellow from 15% and red from 20%.
    def test_context_colors(self):
        for used, color in [
            ("14.4", "\x1b[2;32m"),
            ("15", "\x1b[2;33m"),
            ("19.4", "\x1b[2;33m"),
            ("20", "\x1b[2;31m"),
        ]:
            got = default().render(parse('{"context_window": {"used_percentage": ' + used + "}}"), "", 120)
            self.assertIn(color, got, used)

    # The 7-day bar shows the weekday it resets on, and drops it with the 5-hour reset time when
    # narrow.
    def test_reset_day(self):
        in_ = parse(
            '{"rate_limits": {"five_hour": {"used_percentage": 55, "resets_at": %d},'
            '"seven_day": {"used_percentage": 81, "resets_at": %d}}}'
            % (at(24, 14, 0), at(28, 9, 30))
        )
        got = plain(default().render(in_, "", 120))
        self.assertTrue(got.endswith("7d ████████░░ 81% (Mon)"), got)
        in_.model = "Opus 5.5"
        self.assertNotIn("(", plain(default().render(in_, "", 44)))

    # The reset time shows alone, even past midnight.
    def test_reset_time(self):
        self.assertEqual(statusline._reset_time(float(at(24, 14, 5))), "14:05")
        self.assertEqual(statusline._reset_time(float(at(25, 1, 0))), "01:00")

    def test_layout(self):
        line = plain(default().render(usage(), "main", 200))
        self.assertTrue(line.startswith("main "), line)
        self.assertIn("Ctx █░░░░░░░░░ 12% 5h █████░░░░░ 55% (", line)
        self.assertTrue(line.endswith("7d ████████░░ 81%"), line)
        mid = len(line) - line.index("Ctx")
        self.assertEqual(line.index("Ctx"), (196 - mid) // 2, "centered")

        colored = default().render(usage(MODEL), "main", 200)
        line = plain(colored)
        self.assertRegex(line, r"81% {2,}Opus 5\.5 \(high\)$")
        self.assertEqual(len(line), 196)
        # The effort shares the model's color.
        self.assertTrue(colored.endswith("\x1b[2;37mOpus 5.5 (high)\x1b[00m"), colored)
        got = plain(default().render(parse('{"model": {"display_name": "Opus 5.5"}}'), "", 120))
        self.assertTrue(got.endswith(" Opus 5.5"), got)

    # When narrow, the line shrinks the bars, then drops the reset time, then the model.
    def test_narrow(self):
        in_ = usage(MODEL)
        for columns, want, suffix in [
            (87, "Ctx █░░░░░░░░░ 12%", False),
            (86, "Ctx ░░░░░ 12% 5h ██░░░ 55% (", False),
            (72, "55% (", False),
            (71, "55% 7d ████░ 81% Opus 5.5 (high)", False),
            (64, "Opus 5.5 (high)", True),
            (63, "7d ████░ 81%", True),
        ]:
            line = plain(default().render(in_, "main", columns))
            if suffix:
                self.assertTrue(line.endswith(want), (columns, line))
            else:
                self.assertIn(want, line, columns)

    # The bars never overlap the branch, and the line shows nothing it isn't given.
    def test_bounds(self):
        got = plain(default().render(usage(), "a-very-long-branch-name-that-fills-the-line", 20))
        self.assertIn("line Ctx", got)
        self.assertEqual(default().render(Input(), "", 120).strip(), "")
        self.assertLessEqual(statusline._visible(default().render(usage(), "", 120)), 116)

    # Before the first reply the context bar shows empty.
    def test_empty_context(self):
        for window in [
            "{}",
            '{"used_percentage": null}',
            '{"used_percentage": 0, "total_input_tokens": 0}',
        ]:
            got = plain(default().render(parse('{"context_window": ' + window + "}"), "", 120))
            self.assertEqual(got.strip(), "Ctx ░░░░░░░░░░ 0%", window)

    # The context's tokens follow its percentage, rounded to thousands.
    def test_tokens(self):
        for tokens, want in [
            ("120400", "60% (120K)"),
            ("199600", "60% (200K)"),
            ("400", "60% (0K)"),
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
        self.assertEqual(got.strip(), "Ctx ░░░░░░░░░░ 0% 5h █████░░░░░ 55%")
        self.assertEqual(default().render(Input.parse([1, 2]), "", 120).strip(), "")


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

    # The Cache bar, after the 7-day bar, fills with the share of the cache's lifetime left, dim
    # green, then yellow below 40% and red below 20%, and shows the minutes until the cache goes
    # cold, rounded up.
    def test_cache(self):
        warm = '"warm": true, "ttl": "5m", "expires_at": ' + str(self.START + 221)
        for fields, want in [
            (warm, "Ctx █░░░░░░░░░ 12% 5h █████░░░░░ 55% Cache ███████░░░ 4m"),
            (warm + ', "recache_tokens_if_cold": 45000', "Cache ███████░░░ 4m"),
            (
                '"warm": true, "ttl": "1h", "expires_at": ' + str(self.START + 3600),
                "Cache ██████████ 60m",
            ),
            (
                '"warm": true, "ttl": "2h", "expires_at": ' + str(self.START + 30),
                "Cache ██████████ 1m",
            ),
        ]:
            got = plain(default().render(self.cached(fields), "", 120))
            self.assertIn(want, got, fields)
            self.assertNotIn("45K", got)
        for left, color in [
            (120, "\x1b[2;32m"),
            (118, "\x1b[2;33m"),
            (61, "\x1b[2;33m"),
            (58, "\x1b[2;31m"),
        ]:
            got = default().render(
                self.cached('"warm": true, "ttl": "5m", "expires_at": ' + str(self.START + left)),
                "",
                120,
            )
            self.assertIn("\x1b[2;37mCache\x1b[00m " + color, got, left)

    # A cold cache shows empty and says so in dim red; with caching off there is no Cache bar.
    def test_cold(self):
        for fields in [
            '"warm": false, "expires_at": null, "recache_tokens_if_cold": 151200',
            '"warm": true, "expires_at": ' + str(self.START),
        ]:
            got = default().render(self.cached(fields), "", 120)
            self.assertIn("Cache ░░░░░░░░░░ cold", plain(got), fields)
            self.assertIn(statusline._paint("2;31", "cold"), got, fields)
        off = parse('{"prompt_cache": {"caching_observed": false, "warm": false}}')
        self.assertEqual(default().render(off, "", 120).strip(), "")

    # Without the context bar, the Cache bar shows the cache's size, the context's tokens, after
    # its minutes or cold.
    def test_size(self):
        no_context = Layout(["cache", "5h"], default().thresholds)
        for fields, want in [
            (
                '"warm": true, "ttl": "5m", "expires_at": '
                + str(self.START + 221)
                + ', "recache_tokens_if_cold": 45000',
                "Cache ███████░░░ 4m (45K) 5h",
            ),
            ('"warm": false, "recache_tokens_if_cold": 151200', "Cache ░░░░░░░░░░ cold (151K) 5h"),
            ('"warm": false, "recache_tokens_if_cold": null', "Cache ░░░░░░░░░░ cold 5h"),
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
