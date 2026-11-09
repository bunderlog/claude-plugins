# baloo works without a Config, one Release per step

2026-11-09

## Symptom

Phase 3 of the move to three plugins (ADR plugin): baloo stops reading and writing a Config and
stops writing Claude Code's settings into a project, while it is still one plugin. Now, because
splitting baloo is cheaper once nothing in it needs a switch: about 1,300 lines exist only to read
the Config and write settings.

## Evidence

- `plugins/baloo/scripts/baloo/config.py` (559 lines), `yaml.py` (440), `settings.py` (320).
- ADR config, ADR checks, ADR guidelines, ADR output-styles and ADR status-line describe the
  switches and the settings session start writes today.
- Guidelines waiting to be read were read 5 times in 79; given by a Hook on the task's signal,
  before the first edit 15 times in 22 (ADR measurement).

## Acceptance criteria

- PRD no-config's criteria hold, each from the Release it names. Done: PRD no-config.

## Comments

### 2026-11-09 · order

One Release per criterion after the PRD, in the order above; each leaves baloo working.

### 2026-11-09 · plan changed

The Guidelines stay given by their task's signal instead of becoming skills: a skill waits to be
called as a Guideline waited to be read, 5 times in 79, against 15 in 22 by a Hook (ADR
measurement). Only their switch goes. The four Releases are PRD no-config's.
