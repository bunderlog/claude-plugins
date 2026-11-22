# bagheera keeps characters a person can't see out of what Claude writes

## Problem

Text Claude copies from a web page, an issue or a file it read can hold characters a terminal, an
editor and a pull request's diff don't show. Bidi controls make code read one way and run
another (Trojan Source, CVE-2021-42574). Tag characters and zero-width spaces carry words that
Claude reads but a person doesn't. Once Claude writes them into a repo, every later session
reads them and every reviewer misses them. Nothing in bunderlog stops that today.

## Users

- Each person with bagheera installed, in every session, the same as the other Checks (ADR
  checks).
- Not for: a project that wants to scan the files it already has, or to scan in CI. That is a
  linter's job, or `hathi`'s.

## Success signal

In the 30 days after the Release, `/bagheera:assess` counts `no-hidden-characters`' denials, and
none of them is labeled false. One false denial is a reason to narrow the Check.

## Scope

- A Check, `no-hidden-characters`, always on like the others (ADR checks). It denies a tool call
  that would write one of these characters:
  - the bidi embeddings, overrides and isolates, U+202A–U+202E and U+2066–U+2069;
  - the tag characters, U+E0000–U+E007F;
  - U+200B ZERO WIDTH SPACE, U+2060 WORD JOINER and U+FEFF ZERO WIDTH NO-BREAK SPACE. A Write
    whose content starts with U+FEFF is still allowed, since that is a file's byte order mark.
  A run of tag characters right after U+1F3F4 WAVING BLACK FLAG is allowed: that is the flag of
  England, Scotland or Wales.
- What counts as written: a Write's content, an Edit's `new_string`, each MultiEdit edit's
  `new_string`, and a Bash command's text as it stands. An Edit, and each MultiEdit edit on its
  own, counts a character only when its `new_string` holds more of that code point than its
  `old_string`, so an edit can remove a character or keep one that is already there.
- The denial's reason names the first such character (its code point and Unicode name) and its
  line and column in that text, each counted in characters from 1. It tells Claude that, if the
  character is meant, it can write it as an escape: `\u200b`, or `\U000e0041` above U+FFFF.

## Non-goals

- Characters that real text uses: U+200C ZWNJ and U+200D ZWJ (emoji sequences, Persian), U+200E
  LRM and U+200F RLM (Hebrew and Arabic text), ESC and NUL.
- What Claude reads: a Read, a Grep's or a command's output, a web page. The Check only stops what
  goes into the repo.
- Files the repo already holds, and commits that aren't Claude's.
- NotebookEdit, which no Check's Hook matches.
- Keeping a character a file already holds when Claude rewrites the whole file with a Write, or
  removing one with a Bash command that names it as it is, such as `sed`: both are denied, and
  Claude uses an Edit, or writes the character as an escape.

## Anti-goals

- An emoji sequence joined with U+200D, or a Hebrew or Arabic string with LRM or RLM, is denied.
- An edit that removes a hidden character is denied.
- A Check that guarded a session stops guarding it (PRD bagheera).

## Acceptance criteria

- A Write whose content holds U+202E at line 2 is denied. The reason names
  `bagheera:no-hidden-characters`, `U+202E RIGHT-TO-LEFT OVERRIDE`, line 2 and its column, and the
  escape to write instead.
  → test: tests/bagheera/test_cli.py "test_pre_tool_use", tests/bagheera/checks/test_hidden.py "test_names_the_character_and_where"
- A Write, an Edit, a MultiEdit and a Bash command that each hold one of U+2066, U+E0041, U+200B,
  U+2060 or a mid-text U+FEFF are denied.
  → test: tests/bagheera/checks/test_hidden.py "test_denies_each_kind_in_each_tool", "test_a_second_byte_order_mark"
- A Write whose content starts with U+FEFF and holds no other listed character runs.
  → test: tests/bagheera/checks/test_hidden.py "test_lets_through"
- An Edit whose `old_string` holds U+200B and whose `new_string` doesn't runs. So does one whose
  `old_string` and `new_string` hold it once each.
  → test: tests/bagheera/checks/test_hidden.py "test_lets_through"
- A Write holding an emoji sequence joined with U+200D, U+200C, U+200E or U+200F runs.
  → test: tests/bagheera/checks/test_hidden.py "test_lets_through"
- A Bash command `printf '\u200b'`, written with the escape, runs.
  → test: tests/bagheera/checks/test_hidden.py "test_lets_through"
- A Write holding the flag of England (U+1F3F4 and its tag characters) runs; the same with U+200B
  after it is denied; U+E0041 after a letter is denied.
  → test: tests/bagheera/checks/test_hidden.py "test_a_flag_emoji_but_not_what_follows_it"
- `doctor` lists `no-hidden-characters` as on with the other Checks.
  → test: tests/bagheera/test_doctor.py "test_doctor"
- A `no-hidden-characters` that raises lets the call through, and `doctor` names it, as for the
  other Checks.
  → test: tests/bagheera/test_doctor.py "test_hidden_characters_failed"
