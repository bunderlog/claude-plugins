import fnmatch
import json
import os
import unittest

from bagheera import deny
from tests.bagheera.commands import in_repo, outside_repo, run, start, write

OFFER = "offer the user, once, to add these deny rules"


class Deny(unittest.TestCase):
    def setUp(self):
        self.dir = in_repo(self)
        self.user = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json")
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"

    # With none of the rules in the person's own settings, session start offers all of them, once
    # per machine, and writes nothing there; a headless session doesn't use the offer up, and one
    # outside a repo offers as in one.
    def test_offer(self):
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertNotIn(OFFER, start(self)[1])
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        out = start(self)[1]
        self.assertIn(OFFER + " to the permissions.deny of " + self.user, out)
        for rule in ["Read(//**/.env)", "Read(~/.aws/credentials)", "Read(~/.config/gh/hosts.yml)"]:
            self.assertIn(rule, out)
        self.assertFalse(os.path.exists(self.user))
        self.assertNotIn(OFFER, start(self)[1])
        os.environ["CLAUDE_PROJECT_DIR"] = in_repo_again(self)
        self.assertNotIn(OFFER, start(self)[1])

    def test_offer_outside_repo(self):
        os.environ["CLAUDE_PROJECT_DIR"] = outside_repo(self)
        self.assertIn(OFFER, start(self)[1])

    # With some of the rules there, the offer names only the missing ones; with all, none; a file
    # that isn't JSON gets no offer.
    def test_offer_missing_only(self):
        write(self.user, json.dumps({"permissions": {"deny": deny.RULES[1:]}}))
        out = start(self)[1]
        self.assertIn(OFFER, out)
        self.assertIn('["Read(//**/.env)"]', out)

        for text in [json.dumps({"permissions": {"deny": deny.RULES}}), "{not json",
                     '{"permissions": {"deny": "Read(.env)"}}']:
            with self.subTest(text=text):
                in_repo(self)
                os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
                write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), text)
                self.assertNotIn(OFFER, start(self)[1])

    # The managed settings count as the person's too.
    def test_counts_managed_rules(self):
        write(os.environ["BALOO_MANAGED_SETTINGS"],
              json.dumps({"permissions": {"deny": deny.RULES}}))
        self.assertNotIn(OFFER, start(self)[1])

    # doctor names the file and the missing rules, and fails; with all there, it names none.
    def test_doctor_names_missing_rules(self):
        write(self.user, json.dumps({"permissions": {"deny": deny.RULES[2:]}}))
        code, out, _ = run("doctor")
        self.assertEqual(code, 1, out)
        self.assertIn(f"- {self.user} lacks 2 of bagheera's deny rules: add to its "
                      'permissions.deny ["Read(//**/.env)", "Read(//**/.env.local)"]', out)
        write(self.user, json.dumps({"permissions": {"deny": deny.RULES}}))
        self.assertNotIn("deny rules", run("doctor")[1])
        write(self.user, "{not json")
        self.assertIn(f"- {self.user}: ", run("doctor")[1])

    # No rule denies an Env file's template.
    def test_templates_readable(self):
        for rule in deny.RULES:
            last = rule[len("Read("):-1].split("/")[-1]
            for name in (".env.example", ".env.sample"):
                self.assertFalse(fnmatch.fnmatch(name, last), (rule, name))


def in_repo_again(test):
    """A new repo for the rest of the test, keeping the plugin's data folder and the person's own
    settings, so an offer once per machine stays made."""
    data, own = os.environ["CLAUDE_PLUGIN_DATA"], os.environ["CLAUDE_CONFIG_DIR"]
    managed = os.environ["BALOO_MANAGED_SETTINGS"]
    dir = in_repo(test)
    os.environ.update({"CLAUDE_PLUGIN_DATA": data, "CLAUDE_CONFIG_DIR": own,
                       "BALOO_MANAGED_SETTINGS": managed, "CLAUDE_CODE_ENTRYPOINT": "cli"})
    return dir


if __name__ == "__main__":
    unittest.main()
