# Keep what /bagheera:setup would fix in a project in one list, for doctor and attention alike

2026-11-22

## Symptom

What `/bagheera:setup` would fix in a project (an item of the list it lacks, a plugin turned on
with no install or one older than the Release, its Git hooks off in the clone) is put together by
hand in two places, `doctor` and the projects needing attention, and the two have drifted:
`doctor` never names Git hooks that are off, while the Status line's attention does, and each words
the same need its own way. Almost every commit that touched `setup.py`, `doctor.py`,
`attention.py` and `cli.py` together in the last months changed this one list or its wording.
The goal: one function in `setup.py` gives the list, each need in one wording, and `doctor`,
attention and the projects `/bagheera:setup` offers only show it (PRD setup).

## Evidence

- `plugins/bagheera/scripts/bagheera/attention.py:296-307` and `doctor.py:85-101` each assemble
  `setup.problems`, `setup.turned_on` with nothing installed and `setup.old_installs`;
  only attention adds `setup.hooks_off`.
- The same need, two wordings: `doctor.py:92-95` ("turns louie@bunderlog on, but Claude Code has no
  install of it for this project, so nothing of it loads here") and `attention.py:300-301`
  ("louie@bunderlog is turned on with no install of it for this project").
- `attention.SETUP_FIX`, a fix's text, serves as a tag: `attention.py:325` (`lacking`) and
  `cli.py:479` (`setup_others`) pick needs by comparing to it; `test_attention.py:76, 96` build
  needs with it.
- `test_setup.py:118, 162, 473-477` check setup through `doctor`'s output's wording.
- Commits that paid for it: e575645, 0e961ef, bba6095, b1da288, c08dfa4, ba73f82, e8740a0.
- Found by an architecture review on 2026-11-22; the user chose the interface below.

## Acceptance criteria

- `setup.needs(root)` returns, for a set-up repo holding every item of PRD project-setup's list,
  its plugins installed at the Release and its Git hooks on, an empty list; and one sentence for
  each of: an item it lacks, a plugin turned on with no install, an install older than the
  Release, Git hooks it tracks that the clone hasn't turned on. For a repo that isn't set up, it
  returns no item it lacks.
- The sentences are attention's present wording: "<plugin> is turned on with no install of it for
  this project", "<plugin> <version> is installed, older than the <release> this machine has",
  "its Git hooks are off in this clone", and each item's own as `setup.problems` gives it now.
- `doctor` names each sentence of `setup.needs` a problem, followed by
  `: /bagheera:setup fixes it`, and nothing else for these needs: PRD setup's criterion on Git
  hooks off holds (`doctor` names them and exits non-zero; with `core.hooksPath` set, it doesn't).
- `attention.needs` gives each sentence of `setup.needs` as a need with `/bagheera:setup there`
  as its fix, and `attention.lacking` and `bagheera setup-others` pick these needs by a field of
  the need, not by comparing its fix's text; PRD setup's criteria on the list the script gives the
  skill still pass.
- No test in `tests/bagheera/test_setup.py` checks `doctor`'s output to test setup's list; its
  checks of the list are on `setup.needs`.
- `setup.problems`, `setup.old_installs` and `setup.hooks_off` have no caller outside `setup.py`.
- Session start's one-time notice that a repo isn't set up still says so only of a repo lacking an
  item of the list, as now.
- `mise run check` passes.

## Comments

### 2026-11-22 · fix option

Agreed in the architecture review, over a `setup.state(root)` with raw fields (callers could word
needs their own way again) and typed findings (callers would know each kind):
`setup.needs(root) -> List[str]`, hiding the items, the install records, the hook layout and the
rule that an item counts only once the repo is set up. `Need` gains a `setup: bool`, and
`SETUP_FIX` stays only as the fix's text; `attention.json` is a cache rewritten every 30 s, so its
shape changing costs nothing. `turned_on` stays public, for `doctor`'s Plugin section; `missing`
and `started`, for session start and `cli`.

Steps, each leaving `mise run check` green: `setup.needs` with its tests; attention and
`setup-others` on it, with `Need.setup`; `doctor` on it, naming Git hooks off, its long wordings
gone and `test_setup`'s checks of `doctor`'s text moved to `setup.needs`; the three functions made
private.
