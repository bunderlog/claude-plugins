# bagheera and louie ship, and baloo keeps only its method

2026-11-09

## Symptom

Phase 5 of the move to three plugins (ADR plugin): bagheera and louie ship from this marketplace,
and baloo is left with its knowledge skills, Guidelines and one SessionStart Hook in `sh`. Now
only after `config-out-of-baloo` and `release-several-plugins`, which it needs.

## Evidence

- ADR plugin lists each plugin's parts; PRD harness lists what moves from baloo to each.
- About 4,000 lines of baloo's Python go to bagheera: the Checks in Hooks, the Status line and
  `doctor`, the Session review, Retro and the Transcripts' condenser.

## Acceptance criteria

- A PRD for each move exists and has no Status line: a simpler Session review; bagheera; stack
  Guidelines given on a file's first touch; delivery from an Issue to a pull request, `verify`
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
