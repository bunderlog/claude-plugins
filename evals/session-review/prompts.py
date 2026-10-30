"""Writes each case's prompt.md from the Session review's own prompt and the case's
conversation.md, so a case asks what a review is asked. Run it after the prompt changes:
python3 evals/session-review/prompts.py"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "plugins", "baloo", "scripts"))

from baloo import names, review  # noqa: E402

ID = "20261030T120000Z-0e7a1c35"

for case in sorted(os.listdir(HERE)):
    conversation = os.path.join(HERE, case, "conversation.md")
    if not os.path.isfile(conversation):
        continue
    with open(os.path.join(HERE, case, "description.txt"), encoding="utf-8") as f:
        description = f.read().strip()
    with open(conversation, encoding="utf-8") as f:
        text = f.read().strip()
    prompt = review._prompt(ID, "./" + names.PROPOSALS + ID + ".md", [], False)
    with open(os.path.join(HERE, case, "prompt.md"), "w", encoding="utf-8") as f:
        f.write(
            "---\n"
            f"description: {description}\n"
            'plugins: ["../../../plugins/baloo"]\n'
            "max_turns: 30\n"
            "allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]\n"
            "---\n\n"
            f"{prompt}\n\nThe conversation, as stdin holds it:\n\n{text}\n"
        )
