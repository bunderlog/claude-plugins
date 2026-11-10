# bagheera and louie ship, and baloo keeps only its method

2026-11-09

## Symptom

Phase 5 of the move to three plugins (ADR plugin): bagheera and louie ship from this marketplace,
and baloo is left with its knowledge skills and one SessionStart Hook in `sh`. Now
only after `config-out-of-baloo` and `release-several-plugins`, which it needs.

## Evidence

- ADR plugin lists each plugin's parts; PRD harness lists what moves from baloo to each.
- About 4,000 lines of baloo's Python go to bagheera: the Checks in Hooks, the Status line and
  `doctor`, the Session review, Retro and the Transcripts' condenser.

## Acceptance criteria

- A PRD for each move exists and has no Status line: a simpler Session review; bagheera; louie,
  which takes the Guidelines and the verifier; delivery from an Issue to a pull request, `verify`
  included; templates.
- PRD harness: "With every other plugin of the marketplace off, each plugin's skills load …" holds
  for all three.
- PRD harness: the install criteria hold on a clean machine (bagheera by two commands; baloo and
  louie from a set-up project's settings once the folder is trusted).
- baloo's `plugins/baloo/` holds no Python.
- The Release that moves `short-replies` says once, to whoever set `baloo:short-replies`, to set
  `bagheera:short-replies`.

## Comments

### 2026-11-09 · order

bagheera first, after the Session review is made simpler; then louie, its PRDs in the order above;
baloo loses its Python with the last of bagheera's moves. One feature at a time (PRD harness).

### 2026-11-10 · progress

The simpler Session review and bagheera shipped with 0.41.0, louie with 0.42.0, and
`plugins/baloo/` holds no Python. Left: the install criteria on a clean machine, and the test
that each plugin works with the others gone.

### 2026-11-10 · progress

PRD delivery and PRD templates are agreed; 0.44.1 tells once, to whoever still picks
`baloo:short-replies`, to pick `bagheera:short-replies`. The clean machine is a new macOS account,
with python3 from the Command Line Tools.

### 2026-11-10 · clean machine

Tried on the clean machine by the user: baloo and louie came on from the set-up project's settings
once the folder was trusted, so PRD harness's second install criterion holds. The user chose not to
install bagheera at user scope and added it to the project's settings by hand, where it all worked,
so the first criterion, the two commands as the whole install for any folder, is still unchecked;
the Status line was set by hand, as ADR status-line has it (Inbox, "The Status line set by hand on a
clean machine"); bagheera at local scope is supported from then on (ADR plugin).
